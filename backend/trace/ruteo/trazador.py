"""Arma la ruta de un flujo como lista de hops sobre la topología de `datos/`.

No hacemos traceroute: los hops se infieren de la topología pública (IXPs, cables,
data centers). Por eso cada hop lleva `observado` y el flujo una `confianza_ruta`.
"""

from __future__ import annotations

import math
from random import Random

from ..datos import Catalogo
from ..esquemas import Hop, Nodo

# Continente aproximado por país, para elegir por dónde cruza el tráfico.
REGION_POR_PAIS = {
    "AR": "sudamerica", "BR": "sudamerica", "CL": "sudamerica", "UY": "sudamerica",
    "US": "norteamerica", "CA": "norteamerica", "MX": "norteamerica",
    "ES": "europa", "NL": "europa", "GB": "europa", "DE": "europa", "IE": "europa",
    "FR": "europa", "PT": "europa",
    "JP": "asia", "SG": "asia", "IN": "asia", "CN": "asia",
}

CABLE_POR_REGION = {
    "norteamerica": "cable-sam1",
    "europa": "cable-atlantis2",
    "asia": "cable-curie",
}

IXP_ENTRADA_POR_REGION = {
    "norteamerica": "ixp-mia",
    "europa": "ixp-mad",
    "asia": "ixp-sin",
}


def region(pais: str) -> str:
    return REGION_POR_PAIS.get(pais, "europa")


def distancia_km(a: Nodo, b: Nodo) -> float:
    r = 6371.0
    dlat = math.radians(b.lat - a.lat)
    dlon = math.radians(b.lon - a.lon)
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(a.lat)) * math.cos(math.radians(b.lat)) * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(h))


def latencia_entre(a: Nodo, b: Nodo) -> int:
    """Latencia del tramo: la luz en fibra va a ~200.000 km/s, más overhead de equipos."""
    return max(1, round(distancia_km(a, b) / 200.0) + 1)


class Trazador:
    def __init__(self, catalogo: Catalogo) -> None:
        self.catalogo = catalogo

    def trazar(self, dispositivo_id: str, destino_id: str, azar: Random,
               via: str | None = None) -> tuple[list[Hop], float]:
        cat = self.catalogo
        destino = cat.nodo_por_id[destino_id]
        cadena_ids: list[str] = [dispositivo_id, "router-01"]

        isp = azar.choice(["isp-telecom", "isp-telefonica", "isp-claro"])
        cadena_ids += [isp, "ixp-nqn", "ixp-bue"]

        destino_region = region(destino.pais)
        if via:
            cadena_ids.append(via)
            if destino.id != via:
                cadena_ids.append(destino.id)
        elif destino_region == "sudamerica" and destino.pais == "AR":
            cadena_ids.append(destino.id)
        elif destino_region == "sudamerica":
            cadena_ids += ["bb-lumen-sp", "ixp-sao", destino.id]
        else:
            cadena_ids += [
                "bb-lumen-bue",
                CABLE_POR_REGION[destino_region],
                IXP_ENTRADA_POR_REGION[destino_region],
                destino.id,
            ]
            if destino_region == "europa" and destino.pais != "ES":
                cadena_ids.insert(-1, "ixp-ams" if destino.pais == "NL" else "ixp-lon")

        # Sin duplicados consecutivos y sólo nodos que existan.
        cadena: list[Nodo] = []
        for nodo_id in cadena_ids:
            nodo = cat.nodo_por_id.get(nodo_id)
            if nodo is None or (cadena and cadena[-1].id == nodo.id):
                continue
            cadena.append(nodo)

        hops: list[Hop] = []
        acumulada = 0
        for indice, nodo in enumerate(cadena):
            if indice > 0:
                acumulada += latencia_entre(cadena[indice - 1], nodo)
            # Los tramos internos y los IXP se ven; backbone y cables se infieren.
            observado = nodo.tipo not in {"backbone", "cable", "satelite"}
            hops.append(Hop(nodo_id=nodo.id, latencia_ms=acumulada, observado=observado))

        inferidos = sum(1 for h in hops if not h.observado)
        confianza = round(max(0.4, 1.0 - 0.12 * inferidos), 2)
        return hops, confianza
