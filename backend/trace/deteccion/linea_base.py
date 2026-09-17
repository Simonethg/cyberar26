"""Línea de base por dispositivo: cuánto manda y con quién habla habitualmente.

Se precalcula a partir del guion `normal` y vive en `datos/linea_base.json`. No se
recalcula en vivo: la demo tiene que ser determinística.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..datos import Catalogo


@dataclass
class BaseDispositivo:
    bytes_salida_por_hora: int
    asn_habituales: set[int]
    paises_habituales: set[str]

    @property
    def umbral_volumen_por_minuto(self) -> int:
        """La regla dispara cuando en un minuto sale más de 10 veces el promedio horario."""
        return self.bytes_salida_por_hora * 10


class LineaBase:
    def __init__(self, catalogo: Catalogo) -> None:
        self.catalogo = catalogo
        self._por_dispositivo: dict[str, BaseDispositivo] = {}
        for dispositivo_id, datos in catalogo.linea_base.get("dispositivos", {}).items():
            self._por_dispositivo[dispositivo_id] = BaseDispositivo(
                bytes_salida_por_hora=int(datos.get("bytes_salida_por_hora", 1_000_000)),
                asn_habituales=set(datos.get("asn_habituales", [])),
                paises_habituales=set(datos.get("paises_habituales", [])),
            )

    def de(self, dispositivo_id: str) -> BaseDispositivo:
        if dispositivo_id not in self._por_dispositivo:
            # Un dispositivo que no está en la línea de base es nuevo: todo le resulta inusual.
            self._por_dispositivo[dispositivo_id] = BaseDispositivo(120_000, set(), set())
        return self._por_dispositivo[dispositivo_id]

    def formatear_bytes(self, cantidad: float) -> str:
        for unidad, divisor in (("GB", 1e9), ("MB", 1e6), ("KB", 1e3)):
            if cantidad >= divisor:
                return f"{cantidad / divisor:.1f} {unidad}".replace(".", ",")
        return f"{int(cantidad)} B"
