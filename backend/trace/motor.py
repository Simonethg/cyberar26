"""Motor: corre el simulador, aplica la detección y publica todo por WebSocket."""

from __future__ import annotations

import asyncio
import contextlib
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from .almacen import Almacen
from .asistente.ollama import Asistente
from .datos import Catalogo
from .datos import catalogo as cargar_catalogo
from .deteccion.reglas import VENTANA_VOLUMEN_S, Detector
from .esquemas import (
    Alerta,
    DestinoTop,
    Dispositivo,
    EstadoSistema,
    EvaluacionEjercicio,
    Flujo,
    MetricasGlobal,
    Paquete,
)
from .simulador.generador import DT, Simulador

VENTANA_METRICAS_S = 5.0
VENTANA_DESTINOS_S = 300.0
MAX_PAQUETES = 200
MAX_FLUJOS_RECORDADOS = 400
SEVERIDAD_MINIMA_IA = {"media", "alta", "critica"}


class Motor:
    def __init__(self, catalogo: Catalogo | None = None, almacen: Almacen | None = None) -> None:
        self.catalogo = catalogo or cargar_catalogo()
        self.almacen = almacen or Almacen()
        self.asistente = Asistente()
        self.detector = Detector(self.catalogo)
        self.simulador: Simulador | None = None
        self.tarea: asyncio.Task | None = None
        self.suscriptores: set[asyncio.Queue] = set()

        self.flujos: dict[str, Flujo] = {}
        self.paquetes: deque[Paquete] = deque(maxlen=MAX_PAQUETES)
        self.dispositivos_extra: dict[str, Dispositivo] = {}
        self.ventana_bytes: deque = deque()          # (t, subida, bajada, cifrado)
        self.ventana_destinos: deque = deque()       # (t, asn, organizacion, bytes, paquetes)
        self._bytes_por_flujo: dict[str, tuple[int, int]] = {}
        self._ventana_por_dispositivo: dict[str, deque] = defaultdict(deque)
        self._alertas_generadas = 0
        self._ts_ultima_critica: str | None = None
        self._proxima_metrica = 0.0

    # ------------------------------------------------------------------ publicación

    def suscribir(self) -> asyncio.Queue:
        cola: asyncio.Queue = asyncio.Queue(maxsize=500)
        self.suscriptores.add(cola)
        return cola

    def desuscribir(self, cola: asyncio.Queue) -> None:
        self.suscriptores.discard(cola)

    def publicar(self, tipo: str, datos) -> None:
        cuerpo = datos.model_dump() if hasattr(datos, "model_dump") else datos
        mensaje = {"tipo": tipo, "datos": cuerpo}
        for cola in list(self.suscriptores):
            try:
                cola.put_nowait(mensaje)
            except asyncio.QueueFull:
                # Un cliente lento no puede frenar la simulación.
                self.desuscribir(cola)

    # ------------------------------------------------------------------ control del guion

    def preparar(self, guion_id: str) -> None:
        if guion_id not in self.catalogo.guiones:
            raise KeyError(guion_id)
        self.reiniciar_estado()
        self.simulador = Simulador(self.catalogo, self.catalogo.guiones[guion_id])

    async def lanzar(self, guion_id: str) -> None:
        if guion_id not in self.catalogo.guiones:
            raise KeyError(guion_id)
        await self.detener()
        self.preparar(guion_id)
        self.tarea = asyncio.create_task(self._correr())

    async def detener(self) -> None:
        if self.tarea:
            self.tarea.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.tarea
            self.tarea = None
        self.simulador = None

    def reiniciar_estado(self) -> None:
        self.flujos.clear()
        self.paquetes.clear()
        self.dispositivos_extra.clear()
        self.ventana_bytes.clear()
        self.ventana_destinos.clear()
        self._bytes_por_flujo.clear()
        self._ventana_por_dispositivo.clear()
        self._alertas_generadas = 0
        self._ts_ultima_critica = None
        self._proxima_metrica = 0.0
        self.detector.reiniciar()
        self.almacen.vaciar()

    # ------------------------------------------------------------------ bucle principal

    def paso(self) -> tuple[float, list[Alerta], bool]:
        """Un tick de simulación: emite flujos, corre la detección y publica todo."""
        assert self.simulador is not None
        resultado = self.simulador.tick()
        t = resultado.t
        alertas: list[Alerta] = []

        for dispositivo in resultado.dispositivos_nuevos:
            self.dispositivos_extra[dispositivo.id] = dispositivo
            self.publicar("dispositivo", dispositivo)
            alertas += self.detector.dispositivo_nuevo(dispositivo, self._ts(t), t)

        for flujo in resultado.flujos:
            self._absorber_flujo(flujo, t)
            self.publicar("flujo", flujo)
            bytes_ventana = self._bytes_ventana_dispositivo(flujo.dispositivo_id, t)
            alertas += self.detector.evaluar_flujo(flujo, self._ts(t), t, bytes_ventana)

        alertas += self.detector.correlacionar(self._ts(t), t)
        for alerta in alertas:
            self._registrar_alerta(alerta)

        for paquete in resultado.paquetes:
            self.paquetes.append(paquete)
            self.publicar("paquete", paquete)

        if t >= self._proxima_metrica:
            self._proxima_metrica = t + 1.0
            self.publicar("metricas", self.metricas(t))
            self.publicar("guion", self._estado_guion(t, resultado.terminado))

        if resultado.terminado:
            self.publicar("guion", self._estado_guion(t, True))
        return t, alertas, resultado.terminado

    def _estado_guion(self, t: float, terminado: bool) -> dict:
        assert self.simulador is not None
        return {
            "id": self.simulador.guion.id,
            "t": round(t, 1),
            "duracion_s": self.simulador.guion.duracion_s,
            "terminado": terminado,
        }

    async def _correr(self) -> None:
        while True:
            _t, _alertas, terminado = self.paso()
            if terminado:
                return
            await asyncio.sleep(DT)

    def _ts(self, t: float) -> str:
        if self.simulador is None:
            return (datetime.now(timezone.utc).isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z"))
        return self.simulador._ts(t)

    # ------------------------------------------------------------------ estado en memoria

    def _absorber_flujo(self, flujo: Flujo, t: float) -> None:
        previo_subida, previo_bajada = self._bytes_por_flujo.get(flujo.id, (0, 0))
        delta_subida = flujo.bytes_subida - previo_subida
        delta_bajada = flujo.bytes_bajada - previo_bajada
        self._bytes_por_flujo[flujo.id] = (flujo.bytes_subida, flujo.bytes_bajada)
        self.flujos[flujo.id] = flujo

        self.ventana_bytes.append((t, delta_subida, delta_bajada, bool(flujo.protocolo.cifrado)))
        self.ventana_destinos.append((t, flujo.destino.asn, flujo.destino.organizacion,
                                      delta_subida + delta_bajada,
                                      max(1, (delta_subida + delta_bajada) // 1400)))
        self._ventana_por_dispositivo[flujo.dispositivo_id].append((t, delta_subida))

        self._podar(t)
        if len(self.flujos) > MAX_FLUJOS_RECORDADOS:
            cerrados = [f for f in self.flujos.values() if f.estado == "cerrado"]
            for viejo in cerrados[: len(self.flujos) - MAX_FLUJOS_RECORDADOS]:
                self.flujos.pop(viejo.id, None)
                self._bytes_por_flujo.pop(viejo.id, None)

    def _podar(self, t: float) -> None:
        while self.ventana_bytes and t - self.ventana_bytes[0][0] > VENTANA_METRICAS_S:
            self.ventana_bytes.popleft()
        while self.ventana_destinos and t - self.ventana_destinos[0][0] > VENTANA_DESTINOS_S:
            self.ventana_destinos.popleft()
        for ventana in self._ventana_por_dispositivo.values():
            while ventana and t - ventana[0][0] > VENTANA_VOLUMEN_S:
                ventana.popleft()

    def _bytes_ventana_dispositivo(self, dispositivo_id: str, t: float) -> int:
        return sum(b for _t, b in self._ventana_por_dispositivo[dispositivo_id])

    # ------------------------------------------------------------------ alertas

    def _registrar_alerta(self, alerta: Alerta) -> None:
        self._alertas_generadas += 1
        if alerta.severidad == "critica":
            self._ts_ultima_critica = alerta.ts
        self.almacen.guardar(alerta)
        self._marcar_flujo(alerta, True)
        self.publicar("alerta", alerta)
        if alerta.severidad in SEVERIDAD_MINIMA_IA and self.asistente.conectado:
            with contextlib.suppress(RuntimeError):  # sin loop corriendo: sólo plantilla
                asyncio.create_task(self._explicar(alerta))

    async def _explicar(self, alerta: Alerta) -> None:
        explicada = await self.asistente.explicar(alerta.model_copy(deep=True))
        if explicada.fuente_explicacion != "ollama":
            return
        actual = self.almacen.obtener(alerta.id)
        if actual and actual.estado != "abierta":
            explicada.estado = actual.estado
        self.almacen.guardar(explicada)
        self.publicar("alerta", explicada)

    def _marcar_flujo(self, alerta: Alerta, con_alerta: bool) -> None:
        if not alerta.flujo_id:
            return
        flujo = self.flujos.get(alerta.flujo_id)
        if not flujo:
            return
        if con_alerta and "alerta" not in flujo.etiquetas:
            flujo.etiquetas.append("alerta")
            self.publicar("flujo", flujo)
        elif not con_alerta and "alerta" in flujo.etiquetas:
            flujo.etiquetas.remove("alerta")
            self.publicar("flujo", flujo)

    def cambiar_estado_alerta(self, alerta_id: str, estado: str) -> Alerta | None:
        alerta = self.almacen.cambiar_estado(
            alerta_id, estado, datetime.now(timezone.utc).isoformat(timespec="seconds")
        )
        if alerta:
            if estado in {"reconocida", "cerrada"}:
                self._marcar_flujo(alerta, False)
            self.publicar("alerta", alerta)
        return alerta

    # ------------------------------------------------------------------ métricas

    def metricas(self, t: float | None = None) -> MetricasGlobal:
        t = t if t is not None else (self.simulador.t if self.simulador else 0.0)
        self._podar(t)
        subida = sum(m[1] for m in self.ventana_bytes)
        bajada = sum(m[2] for m in self.ventana_bytes)
        bytes_cifrados = sum(m[1] + m[2] for m in self.ventana_bytes if m[3])
        bytes_total = sum(m[1] + m[2] for m in self.ventana_bytes)
        activos = [f for f in self.flujos.values() if f.estado == "activo"]
        return MetricasGlobal(
            mbps_bajada=round(bajada * 8 / VENTANA_METRICAS_S / 1e6, 2),
            mbps_subida=round(subida * 8 / VENTANA_METRICAS_S / 1e6, 2),
            flujos_activos=len(activos),
            destinos=len({d[1] for d in self.ventana_destinos}),
            porcentaje_cifrado=round(100 * bytes_cifrados / bytes_total, 1) if bytes_total else 0.0,
            alertas_abiertas=len(self.almacen.listar("abierta")),
        )

    def destinos_top(self, por: str = "bytes", limite: int = 7) -> list[DestinoTop]:
        acumulado: dict[tuple[int, str], int] = defaultdict(int)
        for _t, asn, organizacion, bytes_, paquetes in self.ventana_destinos:
            valor = bytes_ if por == "bytes" else (paquetes if por == "paquetes" else 1)
            acumulado[(asn, organizacion)] += valor
        total = sum(acumulado.values()) or 1
        ordenado = sorted(acumulado.items(), key=lambda kv: kv[1], reverse=True)
        top = [
            DestinoTop(organizacion=org, asn=asn, valor=valor,
                       porcentaje=round(100 * valor / total, 1))
            for (asn, org), valor in ordenado[:limite]
        ]
        resto = sum(valor for _clave, valor in ordenado[limite:])
        if resto:
            top.append(DestinoTop(organizacion="Otros", asn=0, valor=resto,
                                  porcentaje=round(100 * resto / total, 1)))
        return top

    def dispositivos(self) -> list[Dispositivo]:
        return list(self.catalogo.dispositivos) + list(self.dispositivos_extra.values())

    def estado(self) -> EstadoSistema:
        return EstadoSistema(
            en_vivo=self.tarea is not None and not self.tarea.done(),
            guion_activo=self.simulador.guion.id if self.simulador else None,
            t=round(self.simulador.t, 1) if self.simulador else 0.0,
            duracion_s=self.simulador.guion.duracion_s if self.simulador else 0.0,
            ia_conectada=self.asistente.conectado,
            modelo=self.asistente.modelo,
        )

    def evaluacion(self) -> EvaluacionEjercicio:
        reconocidas = self.almacen.tiempos_de_reconocimiento()
        demora = None
        if self._ts_ultima_critica:
            for _id, ts, ts_reconocida in reconocidas:
                if ts == self._ts_ultima_critica:
                    demora = (
                        datetime.fromisoformat(ts_reconocida.replace("Z", "+00:00"))
                        - datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    ).total_seconds()
                    break
        guion_id = self.simulador.guion.id if self.simulador else "—"
        texto = (
            f"Detectaste la alerta crítica a los {demora:.0f} s de generada. "
            if demora is not None else "No reconociste la alerta crítica. "
        ) + f"Reconociste {len(reconocidas)} de {self._alertas_generadas} alertas."
        return EvaluacionEjercicio(
            guion_id=guion_id,
            alertas_generadas=self._alertas_generadas,
            alertas_reconocidas=len(reconocidas),
            segundos_hasta_reconocer_critica=demora,
            texto=texto,
        )


def instante_iso(segundos: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=segundos)).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")
