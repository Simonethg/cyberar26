"""Valida el catálogo, las referencias y la muestra sin levantar servicios."""

from __future__ import annotations

import math
from ipaddress import ip_address
from trace.datos import DATOS, Catalogo
from trace.esquemas import Flujo, Guion

from pydantic import BaseModel, Field, TypeAdapter


class Amarre(BaseModel):
    ciudad: str
    pais: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    nodo_id: str | None = None


class Cable(BaseModel):
    id: str
    nombre: str
    organizacion: str
    amarre: Amarre
    amarres: list[Amarre] = Field(default_factory=list)


class BaseDispositivo(BaseModel):
    bytes_salida_por_hora: int = Field(ge=0)
    asn_habituales: list[int]
    paises_habituales: list[str]


class LineaBase(BaseModel):
    generada_con: str
    dispositivos: dict[str, BaseDispositivo]


def exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise ValueError(mensaje)


def main() -> None:
    catalogo = Catalogo()
    nodos = catalogo.nodo_por_id
    dispositivos = catalogo.dispositivo_por_id
    organizaciones = catalogo.organizacion_por_asn
    exigir(len(nodos) == len(catalogo.nodos), "IDs de nodos duplicados")
    exigir(len(dispositivos) == len(catalogo.dispositivos), "IDs de dispositivos duplicados")
    exigir(len(organizaciones) == len(catalogo.organizaciones), "ASNs duplicados")
    exigir(len(catalogo.mac_conocidas) == len(dispositivos), "MACs duplicadas")
    for nodo in nodos.values():
        exigir(-90 <= nodo.lat <= 90 and -180 <= nodo.lon <= 180, f"Coordenadas: {nodo.id}")
        exigir(nodo.asn == 0 or nodo.asn in organizaciones, f"ASN del nodo: {nodo.id}")
    for dispositivo in dispositivos.values():
        exigir(dispositivo.id in nodos, f"Falta nodo de {dispositivo.id}")
        exigir(nodos[dispositivo.id].nombre == dispositivo.nombre, f"Nombre: {dispositivo.id}")
        exigir(ip_address(dispositivo.ip).is_private, f"IP de la base: {dispositivo.id}")

    base = LineaBase.model_validate_json((DATOS / "linea_base.json").read_text())
    exigir(set(base.dispositivos) == set(dispositivos), "La línea base no cubre los dispositivos")
    for dispositivo_id, valores in base.dispositivos.items():
        exigir(
            set(valores.asn_habituales) <= set(organizaciones),
            f"ASN habitual: {dispositivo_id}",
        )
    cables = TypeAdapter(list[Cable]).validate_json((DATOS / "cables.json").read_text())
    exigir(len({c.id for c in cables}) == len(cables), "IDs de cables duplicados")
    for cable in cables:
        exigir(cable.id in nodos and nodos[cable.id].tipo == "cable", f"Cable: {cable.id}")
        for amarre in cable.amarres:
            exigir(amarre.nodo_id in nodos, f"Amarre inexistente: {amarre.nodo_id}")
            if amarre.nodo_id is not None:
                nodo = nodos[amarre.nodo_id]
                exigir(
                    (nodo.ciudad, nodo.pais, nodo.lat, nodo.lon)
                    == (amarre.ciudad, amarre.pais, amarre.lat, amarre.lon),
                    f"Coordenadas del amarre: {amarre.nodo_id}",
                )

    rutas_guiones = sorted((DATOS / "guiones").glob("*.json"))
    guiones = [
        Guion.model_validate_json(ruta.read_text())
        for ruta in rutas_guiones
    ]
    exigir(len(guiones) == len(catalogo.guiones), "IDs de guiones duplicados")
    for ruta, guion in zip(rutas_guiones, guiones, strict=True):
        exigir(ruta.stem == guion.id, f"ID distinto del nombre del archivo: {ruta.name}")
        exigir(guion.duracion_s > 0, f"Duración del guion: {guion.id}")
        exigir(math.isclose(sum(guion.fondo.mezcla.values()), 1), f"Mezcla: {guion.id}")
        exigir(all(p >= 0 for p in guion.fondo.mezcla.values()), f"Pesos: {guion.id}")
        exigir(
            set(guion.fondo.mezcla) <= set(catalogo.mezcla_destinos),
            f"Categoría desconocida: {guion.id}",
        )
        ids = set(dispositivos)
        macs = set(catalogo.mac_conocidas)
        for evento in sorted(guion.eventos, key=lambda e: e.t):
            exigir(0 <= evento.t <= guion.duracion_s, f"Tiempo del evento: {guion.id}")
            if evento.tipo == "dispositivo_nuevo":
                exigir(evento.dispositivo_id not in ids, "Dispositivo nuevo ya registrado")
                exigir(evento.mac is not None and evento.mac.upper() not in macs, "MAC ya conocida")
                ids.add(evento.dispositivo_id)
                if evento.mac:
                    macs.add(evento.mac.upper())
            else:
                exigir(evento.dispositivo_id in ids, f"Dispositivo inexistente: {guion.id}")
                if evento.tipo == "flujo_forzado":
                    exigir(evento.destino_id is not None, "Falta destino del flujo")
                    exigir(
                        evento.bytes_por_s is not None and evento.bytes_por_s > 0
                        and evento.duracion_s is not None and evento.duracion_s > 0,
                        "Flujo sin volumen o duración",
                    )
                elif evento.tipo == "cambio_ruta":
                    exigir(evento.via is not None, "Falta vía del cambio de ruta")

    flujos = TypeAdapter(list[Flujo]).validate_json((DATOS / "ejemplo_flujos.json").read_text())
    exigir(len(flujos) == 40 and len({f.id for f in flujos}) == 40, "Se esperan 40 flujos únicos")
    for flujo in flujos:
        exigir(flujo.dispositivo_id in dispositivos, f"Origen: {flujo.id}")
        exigir(flujo.destino.nodo_id in nodos, f"Destino: {flujo.id}")
        exigir(flujo.destino.asn in organizaciones, f"ASN: {flujo.id}")
        exigir(
            flujo.destino.organizacion == organizaciones[flujo.destino.asn].nombre,
            f"Organización del destino: {flujo.id}",
        )
        exigir(all(h.nodo_id in nodos for h in flujo.ruta), f"Hop inexistente: {flujo.id}")
        exigir(
            bool(flujo.ruta)
            and flujo.ruta[0].nodo_id == flujo.dispositivo_id
            and flujo.ruta[-1].nodo_id == flujo.destino.nodo_id,
            f"Extremos de ruta: {flujo.id}",
        )
        latencias = [h.latencia_ms for h in flujo.ruta]
        exigir(latencias == sorted(latencias), f"Latencias acumuladas: {flujo.id}")
    print(f"Válido: {len(nodos)} nodos, {len(dispositivos)} dispositivos, "
          f"{len(organizaciones)} organizaciones, {len(cables)} cables y 40 flujos.")


if __name__ == "__main__":
    main()
