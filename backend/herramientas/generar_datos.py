"""Genera los archivos de `datos/` que necesita el backend para correr.

Son datos de referencia provisorios: la infraestructura y las organizaciones son
información pública, la base y sus dispositivos son ficticios. Si Producto entrega
sus propios archivos, alcanza con reemplazarlos; el backend los valida al arrancar.

Uso: python backend/herramientas/generar_datos.py
"""

from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "datos"

# (id, tipo, nombre, organizacion, asn, ciudad, pais, lat, lon, capa)
INFRA: list[tuple] = [
    ("router-01", "router", "Router perimetral El Chañar", "Base Aérea El Chañar", 0,
     "Neuquén", "AR", -38.95, -68.06, "dispositivos"),
    # ISPs argentinos
    ("isp-telecom", "isp", "Telecom Argentina", "Telecom Argentina", 7303,
     "Buenos Aires", "AR", -34.60, -58.38, "isp"),
    ("isp-telefonica", "isp", "Telefónica de Argentina", "Telefónica", 22927,
     "Buenos Aires", "AR", -34.61, -58.42, "isp"),
    ("isp-claro", "isp", "Claro Argentina", "AMX Argentina", 11664,
     "Buenos Aires", "AR", -34.58, -58.40, "isp"),
    # IXPs
    ("ixp-bue", "ixp", "IXP Buenos Aires", "CABASE", 52376, "Buenos Aires", "AR", -34.60, -58.38, "ixp"),
    ("ixp-nqn", "ixp", "IXP Neuquén", "CABASE", 52376, "Neuquén", "AR", -38.95, -68.06, "ixp"),
    ("ixp-sao", "ixp", "IX.br São Paulo", "NIC.br", 26162, "San Pablo", "BR", -23.55, -46.63, "ixp"),
    ("ixp-mia", "ixp", "NAP of the Americas", "Equinix", 24115, "Miami", "US", 25.77, -80.19, "ixp"),
    ("ixp-mad", "ixp", "ESpanix Madrid", "ESpanix", 6895, "Madrid", "ES", 40.42, -3.70, "ixp"),
    ("ixp-ams", "ixp", "AMS-IX Amsterdam", "AMS-IX", 1200, "Ámsterdam", "NL", 52.37, 4.90, "ixp"),
    ("ixp-lon", "ixp", "LINX Londres", "LINX", 5459, "Londres", "GB", 51.51, -0.13, "ixp"),
    ("ixp-fra", "ixp", "DE-CIX Frankfurt", "DE-CIX", 6695, "Fráncfort", "DE", 50.11, 8.68, "ixp"),
    ("ixp-scl", "ixp", "PIT Chile", "NIC Chile", 27678, "Santiago", "CL", -33.45, -70.67, "ixp"),
    ("ixp-sin", "ixp", "SGIX Singapur", "SGIX", 24482, "Singapur", "SG", 1.35, 103.82, "ixp"),
    ("ixp-nrt", "ixp", "JPIX Tokio", "JPIX", 7527, "Tokio", "JP", 35.68, 139.69, "ixp"),
    ("ixp-lax", "ixp", "Any2 Los Ángeles", "CoreSite", 19626, "Los Ángeles", "US", 34.05, -118.24, "ixp"),
    ("ixp-dub", "ixp", "INEX Dublín", "INEX", 2128, "Dublín", "IE", 53.35, -6.26, "ixp"),
    # Backbone
    ("bb-lumen-bue", "backbone", "Backbone Lumen Buenos Aires", "Lumen", 3356, "Buenos Aires", "AR", -34.62, -58.45, "backbone"),
    ("bb-lumen-sp", "backbone", "Backbone Lumen San Pablo", "Lumen", 3356, "San Pablo", "BR", -23.53, -46.62, "backbone"),
    ("bb-telxius-mia", "backbone", "Backbone Telxius Miami", "Telxius", 12956, "Miami", "US", 25.79, -80.22, "backbone"),
    ("bb-gtt-nyc", "backbone", "Backbone GTT Nueva York", "GTT", 3257, "Nueva York", "US", 40.71, -74.01, "backbone"),
    ("bb-tata-lon", "backbone", "Backbone Tata Londres", "Tata Communications", 6453, "Londres", "GB", 51.50, -0.12, "backbone"),
    ("bb-ntt-tok", "backbone", "Backbone NTT Tokio", "NTT", 2914, "Tokio", "JP", 35.69, 139.70, "backbone"),
    # Cables submarinos (punto de amarre representativo)
    ("cable-sam1", "cable", "Cable SAM-1 (Las Toninas ↔ Miami)", "Telxius", 12956, "Las Toninas", "AR", -36.32, -56.70, "cables"),
    ("cable-atlantis2", "cable", "Cable Atlantis-2 (Las Toninas ↔ Lisboa)", "Consorcio Atlantis-2", 0, "Las Toninas", "AR", -36.33, -56.71, "cables"),
    ("cable-unisur", "cable", "Cable Unisur (Las Toninas ↔ Valparaíso)", "Telxius", 12956, "Las Toninas", "AR", -36.34, -56.69, "cables"),
    ("cable-bicentenario", "cable", "Cable Bicentenario (Las Toninas ↔ Río)", "Telecom Argentina", 7303, "Las Toninas", "AR", -36.31, -56.72, "cables"),
    ("cable-tannat", "cable", "Cable Tannat (Maldonado ↔ Santos)", "Google/Antel", 0, "Maldonado", "UY", -34.90, -54.95, "cables"),
    ("cable-monet", "cable", "Cable Monet (Santos ↔ Boca Ratón)", "Google", 15169, "Santos", "BR", -23.96, -46.33, "cables"),
    ("cable-marea", "cable", "Cable Marea (Virginia ↔ Bilbao)", "Telxius", 12956, "Bilbao", "ES", 43.26, -2.93, "cables"),
    ("cable-curie", "cable", "Cable Curie (Valparaíso ↔ Los Ángeles)", "Google", 15169, "Valparaíso", "CL", -33.05, -71.62, "cables"),
    # Satélites LEO
    ("sat-leo-01", "satelite", "Satélite LEO 01", "Constelación LEO", 0, "Órbita sur", "XX", -40.00, -65.00, "satelites"),
    ("sat-leo-02", "satelite", "Satélite LEO 02", "Constelación LEO", 0, "Órbita atlántica", "XX", -20.00, -40.00, "satelites"),
    # Data centers
    ("dc-mia", "datacenter", "Data center Miami", "Equinix", 24115, "Miami", "US", 25.78, -80.20, "datacenters"),
    ("dc-iad", "datacenter", "Data center Virginia", "Amazon Web Services", 16509, "Ashburn", "US", 39.04, -77.49, "datacenters"),
    ("dc-gru", "datacenter", "Data center San Pablo", "Ascenty", 0, "San Pablo", "BR", -23.56, -46.64, "datacenters"),
    ("dc-scl", "datacenter", "Data center Santiago", "Google", 15169, "Santiago", "CL", -33.46, -70.65, "datacenters"),
    ("dc-ams", "datacenter", "Data center Ámsterdam", "Equinix", 24115, "Ámsterdam", "NL", 52.36, 4.88, "datacenters"),
    ("dc-lon", "datacenter", "Data center Londres", "Digital Realty", 0, "Londres", "GB", 51.52, -0.10, "datacenters"),
    ("dc-fra", "datacenter", "Data center Fráncfort", "Interxion", 0, "Fráncfort", "DE", 50.12, 8.66, "datacenters"),
    ("dc-dub", "datacenter", "Data center Dublín", "Microsoft", 8075, "Dublín", "IE", 53.34, -6.24, "datacenters"),
    ("dc-sin", "datacenter", "Data center Singapur", "Equinix", 24115, "Singapur", "SG", 1.34, 103.84, "datacenters"),
    ("dc-nrt", "datacenter", "Data center Tokio", "NTT", 2914, "Tokio", "JP", 35.67, 139.72, "datacenters"),
    ("dc-lax", "datacenter", "Data center Los Ángeles", "CoreSite", 19626, "Los Ángeles", "US", 34.04, -118.25, "datacenters"),
    ("dc-bue", "datacenter", "Data center Buenos Aires", "Telecom Argentina", 7303, "Buenos Aires", "AR", -34.59, -58.37, "datacenters"),
    ("dc-mad", "datacenter", "Data center Madrid", "Telefónica", 22927, "Madrid", "ES", 40.44, -3.68, "datacenters"),
    # Destino desconocido del escenario de exfiltración (ficticio)
    ("dc-desconocido-nl", "datacenter", "Hosting sin identificar (Países Bajos)", "AS desconocido", 47583,
     "Ámsterdam", "NL", 52.38, 4.92, "datacenters"),
]

# Nubes / CDN: (id, nombre, org, asn, ciudad, pais, lat, lon)
NUBES = [
    ("nube-cloudflare-mia", "Cloudflare Miami", "Cloudflare", 13335, "Miami", "US", 25.76, -80.18),
    ("nube-cloudflare-gru", "Cloudflare San Pablo", "Cloudflare", 13335, "San Pablo", "BR", -23.54, -46.65),
    ("nube-google-iad", "Google Virginia", "Google", 15169, "Ashburn", "US", 39.03, -77.48),
    ("nube-google-scl", "Google Santiago", "Google", 15169, "Santiago", "CL", -33.44, -70.66),
    ("nube-meta-iad", "Meta Virginia", "Meta", 32934, "Ashburn", "US", 39.05, -77.50),
    ("nube-amazon-iad", "Amazon Virginia", "Amazon Web Services", 16509, "Ashburn", "US", 39.02, -77.47),
    ("nube-microsoft-dub", "Microsoft Dublín", "Microsoft", 8075, "Dublín", "IE", 53.36, -6.27),
    ("nube-akamai-mad", "Akamai Madrid", "Akamai", 20940, "Madrid", "ES", 40.41, -3.71),
    ("nube-apple-lax", "Apple Los Ángeles", "Apple", 714, "Los Ángeles", "US", 34.06, -118.23),
    ("nube-telegram-ams", "Telegram Ámsterdam", "Telegram", 62041, "Ámsterdam", "NL", 52.35, 4.91),
    ("nube-whatsapp-gru", "WhatsApp San Pablo", "Meta", 32934, "San Pablo", "BR", -23.57, -46.66),
    ("nube-netflix-mia", "Netflix Miami", "Netflix", 2906, "Miami", "US", 25.75, -80.21),
]

# (id, nombre, tipo, ip_final, sector, critico)
DISPOSITIVOS = [
    ("dev-01", "Servidor de archivos", "servidor", 10, "Sistemas", True),
    ("dev-02", "Servidor de correo", "servidor", 11, "Sistemas", True),
    ("dev-03", "Notebook Comando", "notebook", 12, "Comando", True),
    ("dev-04", "Notebook Logística", "notebook", 13, "Logística", False),
    ("dev-05", "Notebook Operaciones 1", "notebook", 14, "Operaciones", False),
    ("dev-06", "Tablet Guardia", "tablet", 15, "Guardia", False),
    ("dev-07", "Notebook Operaciones 2", "notebook", 16, "Operaciones", True),
    ("dev-08", "Celular Jefe de turno", "celular", 17, "Comando", False),
    ("dev-09", "Cámara perimetral norte", "camara", 18, "Seguridad", False),
    ("dev-10", "Cámara perimetral sur", "camara", 19, "Seguridad", False),
    ("dev-11", "Sensor de acceso 3", "sensor", 20, "Seguridad", True),
    ("dev-12", "Impresora Estado Mayor", "impresora", 21, "Comando", False),
]

# (asn, nombre, pais, tipo_servicio, jurisdiccion, contexto)
ORGANIZACIONES = [
    (13335, "Cloudflare", "US", "CDN", "Estados Unidos",
     "Cloudflare es un CDN: tu tráfico pasa por él aunque el sitio final esté en otro país."),
    (15169, "Google", "US", "Nube y servicios", "Estados Unidos",
     "Google mueve buscador, video y nube; casi siempre te atiende desde el borde más cercano."),
    (32934, "Meta", "US", "Redes sociales", "Estados Unidos",
     "Meta atiende Facebook, Instagram y WhatsApp desde su propia red global."),
    (16509, "Amazon Web Services", "US", "Nube", "Estados Unidos",
     "AWS hospeda una parte enorme de los servicios que usás sin saberlo."),
    (8075, "Microsoft", "US", "Nube y ofimática", "Estados Unidos",
     "Microsoft concentra Office, Teams y Azure; Dublín es su nodo europeo típico."),
    (20940, "Akamai", "US", "CDN", "Estados Unidos",
     "Akamai es el CDN más viejo: entrega actualizaciones y video desde miles de puntos."),
    (714, "Apple", "US", "Servicios y nube", "Estados Unidos",
     "Apple maneja iCloud y actualizaciones desde su red propia."),
    (62041, "Telegram", "GB", "Mensajería", "Emiratos Árabes Unidos",
     "Telegram tiene registro en Reino Unido y operación en Dubái: la jurisdicción no es obvia."),
    (2906, "Netflix", "US", "Video", "Estados Unidos",
     "Netflix pone cachés dentro de los ISP: el video suele venir del país, el control no."),
    (7303, "Telecom Argentina", "AR", "ISP", "Argentina",
     "Telecom es uno de los tres accesos fijos grandes del país."),
    (22927, "Telefónica", "AR", "ISP", "Argentina",
     "Telefónica de Argentina opera acceso fijo y móvil."),
    (11664, "AMX Argentina", "AR", "ISP", "Argentina",
     "Claro Argentina, parte de América Móvil."),
    (52376, "CABASE", "AR", "IXP", "Argentina",
     "CABASE opera los puntos de intercambio locales: si el tráfico pasa por acá, no sale del país."),
    (26162, "NIC.br", "BR", "IXP", "Brasil",
     "IX.br de San Pablo es el punto de intercambio más grande de la región."),
    (24115, "Equinix", "US", "Data center e IXP", "Estados Unidos",
     "Equinix opera data centers neutrales y el NAP of the Americas en Miami."),
    (6695, "DE-CIX", "DE", "IXP", "Alemania",
     "DE-CIX Frankfurt es uno de los IXP con más tráfico del mundo."),
    (1200, "AMS-IX", "NL", "IXP", "Países Bajos",
     "AMS-IX concentra buena parte del intercambio europeo."),
    (5459, "LINX", "GB", "IXP", "Reino Unido",
     "LINX es el punto de intercambio de Londres."),
    (6895, "ESpanix", "ES", "IXP", "España",
     "ESpanix es el intercambio de Madrid, puerta natural de Sudamérica a Europa."),
    (2128, "INEX", "IE", "IXP", "Irlanda",
     "INEX conecta a los operadores irlandeses, donde varias nubes tienen región."),
    (24482, "SGIX", "SG", "IXP", "Singapur",
     "SGIX es el intercambio de Singapur, nodo de todo el sudeste asiático."),
    (7527, "JPIX", "JP", "IXP", "Japón",
     "JPIX es uno de los intercambios de Tokio."),
    (19626, "CoreSite", "US", "Data center", "Estados Unidos",
     "CoreSite opera data centers neutrales en Estados Unidos."),
    (27678, "NIC Chile", "CL", "IXP", "Chile",
     "NIC Chile opera el PIT, el intercambio chileno."),
    (3356, "Lumen", "US", "Backbone", "Estados Unidos",
     "Lumen (ex CenturyLink/Level3) es una de las troncales globales."),
    (12956, "Telxius", "ES", "Backbone y cables", "España",
     "Telxius opera cables submarinos que amarran en Las Toninas."),
    (3257, "GTT", "US", "Backbone", "Estados Unidos",
     "GTT transporta tráfico entre continentes."),
    (6453, "Tata Communications", "IN", "Backbone", "India",
     "Tata es una de las troncales con más presencia global."),
    (2914, "NTT", "JP", "Backbone", "Japón",
     "NTT opera una de las redes troncales más grandes de Asia."),
    (47583, "AS desconocido", "NL", "Hosting", "Países Bajos",
     "Hosting sin identificar: no está en la lista de organizaciones conocidas."),
]

MEZCLA_POR_CATEGORIA = {
    "cdn": ["nube-cloudflare-mia", "nube-cloudflare-gru", "nube-akamai-mad", "nube-netflix-mia"],
    "mensajeria": ["nube-telegram-ams", "nube-whatsapp-gru", "nube-meta-iad"],
    "nube": ["nube-google-iad", "nube-amazon-iad", "nube-microsoft-dub", "nube-apple-lax"],
    "otros": ["dc-bue", "dc-gru", "dc-mad", "dc-scl", "dc-nrt", "dc-sin", "dc-lon"],
}


def nodos() -> list[dict]:
    salida: list[dict] = []
    for id_, nombre, _tipo, ip_final, _sector, _critico in DISPOSITIVOS:
        salida.append({
            "id": id_, "tipo": "dispositivo", "nombre": nombre, "organizacion": "Base Aérea El Chañar",
            "asn": 0, "ciudad": "Neuquén", "pais": "AR",
            "lat": -38.95 + (ip_final - 10) * 0.002, "lon": -68.06 + (ip_final - 10) * 0.002,
            "capa": "dispositivos",
        })
    for id_, tipo, nombre, org, asn, ciudad, pais, lat, lon, capa in INFRA:
        salida.append({
            "id": id_, "tipo": tipo, "nombre": nombre, "organizacion": org, "asn": asn,
            "ciudad": ciudad, "pais": pais, "lat": lat, "lon": lon, "capa": capa,
        })
    for id_, nombre, org, asn, ciudad, pais, lat, lon in NUBES:
        salida.append({
            "id": id_, "tipo": "nube", "nombre": nombre, "organizacion": org, "asn": asn,
            "ciudad": ciudad, "pais": pais, "lat": lat, "lon": lon, "capa": "nubes",
        })
    return salida


def dispositivos() -> list[dict]:
    return [
        {
            "id": id_,
            "nombre": nombre,
            "tipo": tipo,
            "ip": f"192.168.0.{ip_final}",
            "mac": f"AA:BB:CC:00:00:{int(id_.split('-')[1]):02X}",
            "sector": sector,
            "critico": critico,
            "primera_vez_visto": "2026-09-10T08:00:00Z",
        }
        for id_, nombre, tipo, ip_final, sector, critico in DISPOSITIVOS
    ]


def organizaciones() -> list[dict]:
    return [
        {
            "asn": asn, "nombre": nombre, "pais": pais, "tipo_servicio": tipo,
            "jurisdiccion": jurisdiccion, "contexto": contexto,
        }
        for asn, nombre, pais, tipo, jurisdiccion, contexto in ORGANIZACIONES
    ]


def cables() -> list[dict]:
    return [
        {
            "id": id_, "nombre": nombre, "organizacion": org,
            "amarre": {"ciudad": ciudad, "pais": pais, "lat": lat, "lon": lon},
        }
        for id_, tipo, nombre, org, asn, ciudad, pais, lat, lon, capa in INFRA
        if tipo == "cable"
    ]


# Línea de base por dispositivo: bytes salientes por hora y ASN habituales.
LINEA_BASE = {
    "dev-01": (4_500_000, [16509, 8075, 13335]),
    "dev-02": (2_800_000, [8075, 13335, 15169]),
    "dev-03": (3_200_000, [15169, 13335, 32934, 8075]),
    "dev-04": (1_900_000, [15169, 13335, 16509]),
    "dev-05": (2_400_000, [15169, 32934, 13335]),
    "dev-06": (900_000, [32934, 62041, 13335]),
    "dev-07": (3_600_000, [13335, 15169, 16509, 2906]),
    "dev-08": (1_400_000, [32934, 62041, 714]),
    "dev-09": (1_100_000, [16509, 13335]),
    "dev-10": (1_050_000, [16509, 13335]),
    "dev-11": (240_000, [16509]),
    "dev-12": (180_000, [8075]),
}

# Ruta habitual por dispositivo: países por los que suele pasar (para `cambio_ruta`).
PAIS_HABITUAL = {asn: pais for asn, _n, pais, *_r in ORGANIZACIONES}


def linea_base() -> dict:
    return {
        "generada_con": "guion normal, semilla 42",
        "dispositivos": {
            dev: {
                "bytes_salida_por_hora": bytes_hora,
                "asn_habituales": asns,
                "paises_habituales": sorted({PAIS_HABITUAL.get(a, "US") for a in asns}),
            }
            for dev, (bytes_hora, asns) in LINEA_BASE.items()
        },
    }


def guion_normal() -> dict:
    return {
        "id": "normal",
        "nombre": "Operación normal",
        "descripcion": "Tráfico de fondo de la base, sin incidentes. Es el guion de arranque de la demo.",
        "duracion_s": 600,
        "semilla": 42,
        "fondo": {
            "flujos_por_segundo": 6,
            "mezcla": {"cdn": 0.4, "mensajeria": 0.2, "nube": 0.25, "otros": 0.15},
        },
        "eventos": [],
    }


def guion_exfiltracion() -> dict:
    return {
        "id": "exfiltracion-iot",
        "nombre": "Exfiltración desde un sensor IoT",
        "descripcion": (
            "Un dispositivo no declarado se conecta, el sensor de acceso 3 empieza a mandar datos "
            "a un AS desconocido en Países Bajos y el volumen se dispara. A los 65 s el sistema "
            "correlaciona los tres eventos."
        ),
        "duracion_s": 180,
        "semilla": 42,
        "fondo": {
            "flujos_por_segundo": 6,
            "mezcla": {"cdn": 0.4, "mensajeria": 0.2, "nube": 0.25, "otros": 0.15},
        },
        "eventos": [
            {"t": 20, "tipo": "dispositivo_nuevo", "dispositivo_id": "dev-13",
             "nombre": "Equipo no declarado", "mac": "AA:BB:CC:FF:EE:13", "ip": "192.168.0.99"},
            {"t": 45, "tipo": "flujo_forzado", "dispositivo_id": "dev-11",
             "destino_id": "dc-desconocido-nl", "bytes_por_s": 150000, "duracion_s": 120,
             "cifrado": None},
            {"t": 90, "tipo": "cambio_ruta", "dispositivo_id": "dev-03", "via": "ixp-mad"},
        ],
    }


def guion_desvio() -> dict:
    return {
        "id": "desvio-de-ruta",
        "nombre": "Desvío de ruta por un tercer país",
        "descripcion": (
            "El tráfico del servidor de correo deja de salir por Miami y empieza a pasar por "
            "Madrid y Ámsterdam. Sirve para entrenar la lectura del mapa."
        ),
        "duracion_s": 180,
        "semilla": 7,
        "fondo": {
            "flujos_por_segundo": 5,
            "mezcla": {"cdn": 0.35, "mensajeria": 0.2, "nube": 0.3, "otros": 0.15},
        },
        "eventos": [
            {"t": 30, "tipo": "cambio_ruta", "dispositivo_id": "dev-02", "via": "ixp-mad"},
            {"t": 75, "tipo": "cambio_ruta", "dispositivo_id": "dev-01", "via": "ixp-ams"},
            {"t": 120, "tipo": "flujo_forzado", "dispositivo_id": "dev-09",
             "destino_id": "dc-ams", "bytes_por_s": 40000, "duracion_s": 45, "cifrado": None},
        ],
    }


def main() -> None:
    DATOS.mkdir(parents=True, exist_ok=True)
    (DATOS / "guiones").mkdir(exist_ok=True)
    escribir(DATOS / "infraestructura.json", nodos())
    escribir(DATOS / "dispositivos.json", dispositivos())
    escribir(DATOS / "organizaciones.json", organizaciones())
    escribir(DATOS / "cables.json", cables())
    escribir(DATOS / "linea_base.json", linea_base())
    escribir(DATOS / "mezcla_destinos.json", MEZCLA_POR_CATEGORIA)
    escribir(DATOS / "guiones" / "normal.json", guion_normal())
    escribir(DATOS / "guiones" / "exfiltracion-iot.json", guion_exfiltracion())
    escribir(DATOS / "guiones" / "desvio-de-ruta.json", guion_desvio())
    print(f"Listo: {len(nodos())} nodos en datos/infraestructura.json")


def escribir(ruta: Path, contenido) -> None:
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
