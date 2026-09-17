"""Motor de detección: seis reglas explicables más la correlación de la secuencia de ataque.

Toda alerta dice qué regla se disparó, con qué valores y contra qué línea de base.
La `explicacion` que sale de acá es la plantilla; el asistente puede reemplazarla.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

from ..datos import Catalogo
from ..esquemas import Alerta, Dispositivo, Flujo
from .linea_base import LineaBase

VENTANA_VOLUMEN_S = 60.0
VENTANA_CORRELACION_S = 180.0
# La correlación espera a que las tres señales se sostengan antes de gritar "exfiltración".
CONFIRMACION_CORRELACION_S = 7.0
MAX_DESTINO_NUEVO_POR_DISPOSITIVO = 3


@dataclass
class Senal:
    """Una alerta que puede formar parte de una secuencia de ataque."""

    alerta_id: str
    regla: str
    dispositivo_id: str
    t: float


@dataclass
class EstadoDispositivo:
    asn_vistos: set[int] = field(default_factory=set)
    paises_por_destino: dict[str, str] = field(default_factory=dict)
    destinos_nuevos: int = 0
    ventana_subida: deque = field(default_factory=deque)  # (t, bytes)
    bytes_por_flujo: dict[str, int] = field(default_factory=dict)


class Detector:
    def __init__(self, catalogo: Catalogo) -> None:
        self.catalogo = catalogo
        self.linea_base = LineaBase(catalogo)
        self.estados: dict[str, EstadoDispositivo] = defaultdict(EstadoDispositivo)
        self.emitidas: set[tuple] = set()
        self.senales: list[Senal] = []
        self.correlacion_emitida = False
        self._contador = 0
        self._t = 0.0

    # ------------------------------------------------------------------ utilidades

    def reiniciar(self) -> None:
        self.estados.clear()
        self.emitidas.clear()
        self.senales.clear()
        self.correlacion_emitida = False
        self._contador = 0
        self._t = 0.0

    def _nuevo_id(self) -> str:
        self._contador += 1
        return f"al-{self._contador:04d}"

    def _nombre(self, dispositivo_id: str) -> str:
        dispositivo = self.catalogo.dispositivo_por_id.get(dispositivo_id)
        return dispositivo.nombre if dispositivo else dispositivo_id

    def _ya_emitida(self, clave: tuple) -> bool:
        if clave in self.emitidas:
            return True
        self.emitidas.add(clave)
        return False

    def _alerta(self, ts: str, severidad: str, regla: str, titulo: str, dispositivo_id: str,
                flujo_id: str | None, evidencia: dict, explicacion: str,
                accion: str) -> Alerta:
        alerta = Alerta(
            id=self._nuevo_id(),
            ts=ts,
            severidad=severidad,
            regla=regla,
            titulo=titulo,
            dispositivo_id=dispositivo_id,
            flujo_id=flujo_id,
            evidencia=evidencia,
            explicacion=explicacion,
            accion_sugerida=accion,
            fuente_explicacion="plantilla",
        )
        self.senales.append(Senal(alerta.id, regla, dispositivo_id, self._t))
        return alerta

    # ------------------------------------------------------------------ reglas

    def dispositivo_nuevo(self, dispositivo: Dispositivo, ts: str, t: float) -> list[Alerta]:
        self._t = t
        if dispositivo.mac.upper() in self.catalogo.mac_conocidas:
            return []
        if self._ya_emitida(("dispositivo_nuevo", dispositivo.id)):
            return []
        return [self._alerta(
            ts, "info", "dispositivo_nuevo", "Dispositivo nuevo en la red", dispositivo.id, None,
            {"mac": dispositivo.mac, "ip": dispositivo.ip, "nombre": dispositivo.nombre},
            f"Se conectó un dispositivo nuevo: {dispositivo.nombre} ({dispositivo.mac}). "
            f"Nadie lo dio de alta.",
            "Identificá el equipo y dalo de alta, o sacalo de la red.",
        )]

    def evaluar_flujo(self, flujo: Flujo, ts: str, t: float, bytes_ventana: int) -> list[Alerta]:
        self._t = t
        estado = self.estados[flujo.dispositivo_id]
        base = self.linea_base.de(flujo.dispositivo_id)
        dispositivo = self.catalogo.dispositivo_por_id.get(flujo.dispositivo_id)
        critico = bool(dispositivo and dispositivo.critico)
        asn = flujo.destino.asn
        alertas: list[Alerta] = []

        destino_es_nuevo = asn not in base.asn_habituales
        conocido_en_esta_corrida = asn in estado.asn_vistos
        estado.asn_vistos.add(asn)

        # 1 · destino_nuevo
        if destino_es_nuevo and estado.destinos_nuevos < MAX_DESTINO_NUEVO_POR_DISPOSITIVO and \
                not self._ya_emitida(("destino_nuevo", flujo.dispositivo_id, asn)):
            estado.destinos_nuevos += 1
            alertas.append(self._alerta(
                ts, "alta" if critico else "media", "destino_nuevo", "Destino nuevo",
                flujo.dispositivo_id, flujo.id,
                {"destino": flujo.destino.ip, "asn": asn, "pais": flujo.destino.pais,
                 "organizacion": flujo.destino.organizacion, "primera_vez": ts},
                f"{self._nombre(flujo.dispositivo_id)} nunca había hablado con "
                f"{flujo.destino.organizacion} ({flujo.destino.pais}). "
                f"Primer contacto: {ts[11:19]}.",
                "Revisá si ese destino corresponde a una tarea del equipo.",
            ))

        # 2 · asn_desconocido
        if asn not in self.catalogo.organizacion_por_asn and \
                not self._ya_emitida(("asn_desconocido", asn)):
            alertas.append(self._alerta(
                ts, "media", "asn_desconocido", "AS desconocido", flujo.dispositivo_id, flujo.id,
                {"destino": flujo.destino.ip, "asn": asn, "pais": flujo.destino.pais},
                f"El destino {flujo.destino.ip} pertenece a un AS ({asn}) que no está en la "
                f"lista de organizaciones conocidas.",
                "Verificá a quién pertenece ese AS antes de dejar pasar más tráfico.",
            ))
        elif self.catalogo.organizacion_por_asn.get(asn) and \
                self.catalogo.organizacion_por_asn[asn].nombre == "AS desconocido" and \
                not self._ya_emitida(("asn_desconocido", asn)):
            alertas.append(self._alerta(
                ts, "media", "asn_desconocido", "AS desconocido", flujo.dispositivo_id, flujo.id,
                {"destino": flujo.destino.ip, "asn": asn, "pais": flujo.destino.pais},
                f"El destino {flujo.destino.ip} pertenece a un AS ({asn}) sin organización "
                f"identificada.",
                "Verificá a quién pertenece ese AS antes de dejar pasar más tráfico.",
            ))

        # 3 · volumen_inusual
        if bytes_ventana > base.umbral_volumen_por_minuto and \
                not self._ya_emitida(("volumen_inusual", flujo.dispositivo_id)):
            severidad = "alta"
            minutos = max(1, round(VENTANA_VOLUMEN_S / 60))
            alertas.append(self._alerta(
                ts, severidad, "volumen_inusual", "Volumen inusual", flujo.dispositivo_id, flujo.id,
                {"bytes": bytes_ventana, "ventana_s": VENTANA_VOLUMEN_S,
                 "linea_base_bytes_hora": base.bytes_salida_por_hora,
                 "destino": flujo.destino.ip, "asn": asn, "pais": flujo.destino.pais},
                f"{self._nombre(flujo.dispositivo_id)} mandó "
                f"{self.linea_base.formatear_bytes(bytes_ventana)} en {minutos} min. Su promedio "
                f"es {self.linea_base.formatear_bytes(base.bytes_salida_por_hora)} por hora.",
                "Aislá el dispositivo de la red y revisá su firmware.",
            ))

        # 4 · cambio_ruta
        paises_ruta = [
            self.catalogo.nodo_por_id[h.nodo_id].pais
            for h in flujo.ruta if h.nodo_id in self.catalogo.nodo_por_id
        ]
        pais_transito = next((p for p in paises_ruta[2:-1] if p not in {"AR", "XX"}), None)
        if conocido_en_esta_corrida and pais_transito:
            anterior = estado.paises_por_destino.get(flujo.destino.nodo_id)
            if anterior and anterior != pais_transito and \
                    not self._ya_emitida(("cambio_ruta", flujo.dispositivo_id, asn)):
                alertas.append(self._alerta(
                    ts, "media", "cambio_ruta", "Cambio de ruta", flujo.dispositivo_id, flujo.id,
                    {"organizacion": flujo.destino.organizacion, "pais_nuevo": pais_transito,
                     "pais_anterior": anterior, "asn": asn},
                    f"El tráfico de {self._nombre(flujo.dispositivo_id)} hacia "
                    f"{flujo.destino.organizacion} ahora pasa por {pais_transito}. "
                    f"Antes iba por {anterior}.",
                    "Confirmá con el proveedor si hubo un cambio de ruteo legítimo.",
                ))
        if pais_transito:
            estado.paises_por_destino.setdefault(flujo.destino.nodo_id, pais_transito)

        # 5 · sin_cifrar
        if flujo.protocolo.cifrado is None and flujo.destino.pais != "AR" and \
                not self._ya_emitida(("sin_cifrar", flujo.dispositivo_id, asn)):
            alertas.append(self._alerta(
                ts, "media", "sin_cifrar", "Tráfico sin cifrar", flujo.dispositivo_id, flujo.id,
                {"destino": flujo.destino.ip, "organizacion": flujo.destino.organizacion,
                 "pais": flujo.destino.pais},
                f"{self._nombre(flujo.dispositivo_id)} está mandando datos sin cifrar a "
                f"{flujo.destino.organizacion}. Cualquiera en el camino puede leerlos.",
                "Forzá TLS en ese servicio o bloqueá el destino.",
            ))

        return alertas

    # ------------------------------------------------------------------ correlación

    def correlacionar(self, ts: str, t: float) -> list[Alerta]:
        """Secuencia de exfiltración: dispositivo nuevo + destino nuevo + volumen inusual.

        Se emite con 4 s de confirmación desde la última señal, para no encadenar
        coincidencias sueltas.
        """
        self._t = t
        if self.correlacion_emitida:
            return []

        recientes = [s for s in self.senales if t - s.t <= VENTANA_CORRELACION_S]
        requeridas = ("dispositivo_nuevo", "destino_nuevo", "volumen_inusual")
        encontradas = {regla: next((s for s in recientes if s.regla == regla), None)
                       for regla in requeridas}
        if any(s is None for s in encontradas.values()):
            return []

        ultima = max(s.t for s in encontradas.values())
        if t - ultima < CONFIRMACION_CORRELACION_S:
            return []

        self.correlacion_emitida = True
        senal_volumen = encontradas["volumen_inusual"]
        linea_tiempo = [
            {"regla": s.regla, "alerta_id": s.alerta_id, "t": round(s.t, 1),
             "dispositivo_id": s.dispositivo_id}
            for s in sorted(encontradas.values(), key=lambda s: s.t)
        ]
        alerta = self._alerta(
            ts, "critica", "secuencia_exfiltracion", "Secuencia de exfiltración",
            senal_volumen.dispositivo_id, None,
            {"linea_tiempo": linea_tiempo},
            "En menos de tres minutos apareció un dispositivo no declarado, un equipo habló con "
            "un destino nuevo y el volumen saliente se disparó. Los tres eventos, juntos, son el "
            "patrón de una exfiltración en curso.",
            "Aislá los dispositivos involucrados, cortá la salida hacia ese destino y preservá "
            "los registros.",
        )
        alerta.alertas_relacionadas = [s.alerta_id for s in sorted(encontradas.values(),
                                                                   key=lambda s: s.t)]
        return [alerta]
