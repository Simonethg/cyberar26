"""Simulador determinístico de tráfico.

Lee un guion de `datos/guiones/`, genera flujos de fondo a la tasa indicada y ejecuta
los eventos del guion en sus tiempos `t`. Mismo guion + misma semilla = misma secuencia.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from random import Random

from ..datos import Catalogo
from ..esquemas import Destino, Dispositivo, Flujo, Guion, Nodo, Paquete, Protocolo
from ..ruteo.trazador import Trazador
from .paquetes import SintetizadorPaquetes

DT = 0.25  # segundos de reloj virtual por tick
PERIODO_EMISION_S = 1.0  # cada cuánto se reemite un flujo activo

CIFRADOS = ["TLS 1.3", "TLS 1.3", "TLS 1.2"]
PROBABILIDAD_SIN_CIFRAR = 0.004
PROBABILIDAD_DESTINO_FUERA_DE_BASE = 0.0015


@dataclass
class FlujoVivo:
    flujo: Flujo
    bytes_subida_por_s: float
    bytes_bajada_por_s: float
    t_inicio: float
    t_fin: float
    forzado: bool = False
    ultima_emision: float = -99.0
    handshake_emitido: bool = False
    historial_subida: list[tuple[float, int]] = field(default_factory=list)


@dataclass
class ResultadoTick:
    t: float
    flujos: list[Flujo]
    paquetes: list[Paquete]
    cerrados: list[Flujo]
    dispositivos_nuevos: list[Dispositivo]
    terminado: bool


class Simulador:
    def __init__(self, catalogo: Catalogo, guion: Guion) -> None:
        self.catalogo = catalogo
        self.guion = guion
        self.azar = Random(guion.semilla)
        self.trazador = Trazador(catalogo)
        self.paquetes = SintetizadorPaquetes(catalogo, Random(guion.semilla + 1))
        self.t = 0.0
        self.vivos: dict[str, FlujoVivo] = {}
        self.eventos_pendientes = sorted(guion.eventos, key=lambda e: e.t)
        self.rutas_forzadas: dict[str, str] = {}
        self.dispositivos_extra: dict[str, Dispositivo] = {}
        self._acumulador_flujos = 0.0
        self._contador_id = 0
        self._inicio_real = datetime.now(timezone.utc)
        self._habituales_por_dispositivo = self._indexar_habituales()

    def _indexar_habituales(self) -> dict[str, dict[str, list[str]]]:
        """Nodos de cada categoría que caen dentro de la línea de base del dispositivo."""
        indice: dict[str, dict[str, list[str]]] = {}
        for dispositivo in self.catalogo.dispositivos:
            habituales = set(self.catalogo.linea_base_de(dispositivo.id)["asn_habituales"])
            por_categoria = {
                categoria: [
                    nodo_id for nodo_id in nodos
                    if self.catalogo.nodo_por_id[nodo_id].asn in habituales
                ]
                for categoria, nodos in self.catalogo.mezcla_destinos.items()
            }
            indice[dispositivo.id] = {c: n for c, n in por_categoria.items() if n}
        return indice

    # ------------------------------------------------------------------ utilidades

    def _nuevo_id(self) -> str:
        self._contador_id += 1
        return f"{self.guion.semilla:02X}{self._contador_id:04X}"

    def _ts(self, t: float | None = None) -> str:
        instante = self._inicio_real + timedelta(seconds=self.t if t is None else t)
        return instante.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def dispositivos(self) -> list[Dispositivo]:
        return list(self.catalogo.dispositivos) + list(self.dispositivos_extra.values())

    def _elegir_dispositivo(self) -> Dispositivo:
        candidatos = self.dispositivos()
        pesos = [4 if d.tipo in {"servidor", "notebook"} else 1 for d in candidatos]
        return self.azar.choices(candidatos, weights=pesos, k=1)[0]

    def _elegir_destino(self, dispositivo: Dispositivo) -> tuple[str, str]:
        """El tráfico de fondo se queda dentro de la línea de base del dispositivo.

        Salirse de ella es justo lo que detectan las reglas, así que sólo pasa de forma
        excepcional: si no, la operación normal viviría en alerta permanente.
        """
        mezcla = self.guion.fondo.mezcla or {"cdn": 1.0}
        habituales = self._habituales_por_dispositivo.get(dispositivo.id, {})
        dentro_de_base = habituales and self.azar.random() > PROBABILIDAD_DESTINO_FUERA_DE_BASE
        catalogo_categorias = habituales if dentro_de_base else self.catalogo.mezcla_destinos
        categorias = [c for c in mezcla if c in catalogo_categorias] or list(catalogo_categorias)
        categoria = self.azar.choices(categorias,
                                      weights=[mezcla.get(c, 0.1) for c in categorias], k=1)[0]
        return categoria, self.azar.choice(catalogo_categorias[categoria])

    def _destino_desde_nodo(self, nodo: Nodo, categoria: str) -> Destino:
        org = self.catalogo.organizacion_por_asn.get(nodo.asn)
        return Destino(
            ip=self._ip_de(nodo),
            asn=nodo.asn,
            organizacion=org.nombre if org else nodo.organizacion,
            servicio=org.tipo_servicio if org else categoria.upper(),
            ciudad=nodo.ciudad,
            pais=nodo.pais,
            lat=nodo.lat,
            lon=nodo.lon,
            nodo_id=nodo.id,
        )

    def _ip_de(self, nodo: Nodo) -> str:
        semilla = abs(hash((nodo.id, self.guion.semilla))) % (256 * 256)
        base = 104 if nodo.tipo == "nube" else 185
        return f"{base}.{(nodo.asn % 200) + 1}.{semilla // 256}.{semilla % 256}"

    # ------------------------------------------------------------------ creación de flujos

    def _crear_flujo(self, dispositivo: Dispositivo, nodo_destino: Nodo, categoria: str,
                     bytes_subida_por_s: float, bytes_bajada_por_s: float, duracion: float,
                     cifrado: str | None, forzado: bool = False) -> FlujoVivo:
        via = self.rutas_forzadas.get(dispositivo.id)
        # La ruta hacia un mismo destino es estable: cambiarla es una anomalía, no ruido.
        azar_ruta = Random(f"{dispositivo.id}|{nodo_destino.id}|{via}|{self.guion.semilla}")
        hops, confianza = self.trazador.trazar(dispositivo.id, nodo_destino.id, azar_ruta, via=via)
        flujo = Flujo(
            id=self._nuevo_id(),
            ts_inicio=self._ts(),
            dispositivo_id=dispositivo.id,
            destino=self._destino_desde_nodo(nodo_destino, categoria),
            protocolo=Protocolo(
                transporte="TCP",
                cifrado=cifrado,
                aplicacion="HTTPS" if cifrado else "HTTP",
            ),
            rtt_ms=hops[-1].latencia_ms * 2 if hops else 0,
            ruta=hops,
            confianza_ruta=confianza,
        )
        vivo = FlujoVivo(
            flujo=flujo,
            bytes_subida_por_s=bytes_subida_por_s,
            bytes_bajada_por_s=bytes_bajada_por_s,
            t_inicio=self.t,
            t_fin=self.t + duracion,
            forzado=forzado,
        )
        self.vivos[flujo.id] = vivo
        return vivo

    def _crear_flujo_de_fondo(self) -> FlujoVivo:
        dispositivo = self._elegir_dispositivo()
        categoria, destino_id = self._elegir_destino(dispositivo)
        nodo = self.catalogo.nodo_por_id[destino_id]
        subida = self.azar.uniform(400, 6_000)
        bajada = subida * self.azar.uniform(4, 30)
        duracion = self.azar.uniform(4, 40)
        sin_cifrar = self.azar.random() < PROBABILIDAD_SIN_CIFRAR
        cifrado = None if sin_cifrar else self.azar.choice(CIFRADOS)
        return self._crear_flujo(dispositivo, nodo, categoria, subida, bajada, duracion, cifrado)

    # ------------------------------------------------------------------ eventos del guion

    def _aplicar_evento(self, evento) -> Dispositivo | None:
        if evento.tipo == "dispositivo_nuevo":
            dispositivo = Dispositivo(
                id=evento.dispositivo_id,
                nombre=evento.nombre or "Dispositivo sin declarar",
                tipo="desconocido",
                ip=evento.ip or "192.168.0.99",
                mac=evento.mac or "AA:BB:CC:FF:EE:FF",
                sector="Sin asignar",
                critico=False,
                primera_vez_visto=self._ts(),
            )
            self.dispositivos_extra[dispositivo.id] = dispositivo
            return dispositivo

        if evento.tipo == "flujo_forzado":
            dispositivo = self.catalogo.dispositivo_por_id.get(evento.dispositivo_id) \
                or self.dispositivos_extra[evento.dispositivo_id]
            nodo = self.catalogo.nodo_por_id[evento.destino_id]
            self._crear_flujo(
                dispositivo,
                nodo,
                "otros",
                bytes_subida_por_s=float(evento.bytes_por_s or 50_000),
                bytes_bajada_por_s=float(evento.bytes_por_s or 50_000) * 0.02,
                duracion=float(evento.duracion_s or 60),
                cifrado=evento.cifrado,
                forzado=True,
            )
        elif evento.tipo == "cambio_ruta":
            self.rutas_forzadas[evento.dispositivo_id] = evento.via or "ixp-mad"
        return None

    # ------------------------------------------------------------------ tick

    def tick(self) -> ResultadoTick:
        self.t = round(self.t + DT, 3)
        dispositivos_nuevos: list[Dispositivo] = []

        while self.eventos_pendientes and self.eventos_pendientes[0].t <= self.t:
            nuevo = self._aplicar_evento(self.eventos_pendientes.pop(0))
            if nuevo:
                dispositivos_nuevos.append(nuevo)

        self._acumulador_flujos += self.guion.fondo.flujos_por_segundo * DT
        while self._acumulador_flujos >= 1:
            self._acumulador_flujos -= 1
            self._crear_flujo_de_fondo()

        emitidos: list[Flujo] = []
        cerrados: list[Flujo] = []
        paquetes: list[Paquete] = []

        for vivo in list(self.vivos.values()):
            flujo = vivo.flujo
            subida = int(vivo.bytes_subida_por_s * DT)
            bajada = int(vivo.bytes_bajada_por_s * DT)
            flujo.bytes_subida += subida
            flujo.bytes_bajada += bajada
            flujo.paquetes_subida += max(1, subida // 1400)
            flujo.paquetes_bajada += max(1, bajada // 1400)
            vivo.historial_subida.append((self.t, flujo.bytes_subida))

            if not vivo.handshake_emitido:
                paquetes += self.paquetes.handshake(flujo, self._ts())
                vivo.handshake_emitido = True
            elif self.azar.random() < 0.25:
                paquetes += self.paquetes.datos(flujo, self._ts())

            if self.t >= vivo.t_fin:
                flujo.estado = "cerrado"
                cerrados.append(flujo)
                emitidos.append(flujo)
                del self.vivos[flujo.id]
            elif self.t - vivo.ultima_emision >= PERIODO_EMISION_S:
                vivo.ultima_emision = self.t
                emitidos.append(flujo)

        terminado = self.t >= self.guion.duracion_s
        return ResultadoTick(
            t=self.t,
            flujos=emitidos,
            paquetes=paquetes[:25],
            cerrados=cerrados,
            dispositivos_nuevos=dispositivos_nuevos,
            terminado=terminado,
        )

    def bytes_subida_en_ventana(self, flujo_id: str, ventana_s: float) -> int:
        """Bytes salientes de un flujo en los últimos `ventana_s` segundos."""
        vivo = self.vivos.get(flujo_id)
        if not vivo:
            return 0
        actual = vivo.flujo.bytes_subida
        corte = self.t - ventana_s
        previos = 0
        for t, acumulado in vivo.historial_subida:
            if t <= corte:
                previos = acumulado
            else:
                break
        return actual - previos
