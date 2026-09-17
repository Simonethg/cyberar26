"""Sintetiza paquetes legibles a partir de cada flujo (no son capturas reales)."""

from __future__ import annotations

from random import Random

from ..datos import Catalogo
from ..esquemas import Flujo, Paquete

INFOS_DATOS = [
    "Datos cifrados",
    "Datos cifrados",
    "Datos cifrados",
    "Segmento de aplicación",
    "ACK",
]


class SintetizadorPaquetes:
    def __init__(self, catalogo: Catalogo, azar: Random) -> None:
        self.catalogo = catalogo
        self.azar = azar

    def _ip_origen(self, flujo: Flujo) -> str:
        dispositivo = self.catalogo.dispositivo_por_id.get(flujo.dispositivo_id)
        return dispositivo.ip if dispositivo else "192.168.0.99"

    def _paquete(self, flujo: Flujo, ts: str, direccion: str, tamano: int, info: str) -> Paquete:
        origen = self._ip_origen(flujo)
        destino = flujo.destino.ip
        return Paquete(
            ts=ts,
            flujo_id=flujo.id,
            dispositivo_id=flujo.dispositivo_id,
            direccion=direccion,
            origen=origen if direccion == "SAL" else destino,
            destino=destino if direccion == "SAL" else origen,
            protocolo=flujo.protocolo.aplicacion if info != "Consulta DNS" else "DNS",
            tamano=tamano,
            info=info,
        )

    def handshake(self, flujo: Flujo, ts: str) -> list[Paquete]:
        paquetes = [
            self._paquete(flujo, ts, "SAL", 74,
                          f"Consulta DNS {flujo.destino.organizacion.lower()}"),
            self._paquete(flujo, ts, "SAL", 74, "SYN"),
            self._paquete(flujo, ts, "ENT", 74, "SYN, ACK"),
        ]
        if flujo.protocolo.cifrado:
            paquetes += [
                self._paquete(flujo, ts, "SAL", 517, "Client Hello (TLS)"),
                self._paquete(flujo, ts, "ENT", 1414, "Server Hello (TLS)"),
            ]
        else:
            paquetes.append(self._paquete(flujo, ts, "SAL", 312, "Datos sin cifrar"))
        return paquetes

    def datos(self, flujo: Flujo, ts: str) -> list[Paquete]:
        direccion = "SAL" if self.azar.random() < 0.4 else "ENT"
        info = "Datos sin cifrar" if not flujo.protocolo.cifrado else self.azar.choice(INFOS_DATOS)
        return [self._paquete(flujo, ts, direccion, self.azar.randint(120, 1460), info)]
