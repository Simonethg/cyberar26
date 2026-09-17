"""Exporta 40 flujos de muestra usando el contrato y el trazador del backend."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from random import Random
from trace.datos import DATOS, Catalogo
from trace.esquemas import Destino, Flujo, Protocolo
from trace.ruteo.trazador import Trazador

SALIDA = DATOS / "ejemplo_flujos.json"
SEMILLA = 42
INICIO = datetime(2026, 9, 18, 9, 0, tzinfo=timezone.utc)


def generar(catalogo: Catalogo) -> list[Flujo]:
    azar = Random(SEMILLA)
    trazador = Trazador(catalogo)
    destinos = [
        nodo for nodo in catalogo.nodos
        if nodo.tipo in {"nube", "datacenter"}
        and nodo.asn in catalogo.organizacion_por_asn
        and catalogo.organizacion_por_asn[nodo.asn].nombre != "AS desconocido"
    ]
    flujos = []
    for indice in range(40):
        dispositivo = catalogo.dispositivos[indice % len(catalogo.dispositivos)]
        nodo = destinos[indice % len(destinos)]
        org = catalogo.organizacion_por_asn[nodo.asn]
        ruta, confianza = trazador.trazar(dispositivo.id, nodo.id, azar)
        bajada = azar.randint(40_000, 6_000_000)
        subida = azar.randint(2_000, 120_000)
        instante = INICIO + timedelta(seconds=indice * 3)
        flujos.append(Flujo(
            id=f"{SEMILLA:02X}{indice + 1:04X}",
            ts_inicio=instante.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            dispositivo_id=dispositivo.id,
            destino=Destino(
                ip=f"198.51.100.{indice + 1}",
                asn=nodo.asn,
                organizacion=org.nombre,
                servicio=org.tipo_servicio,
                ciudad=nodo.ciudad,
                pais=nodo.pais,
                lat=nodo.lat,
                lon=nodo.lon,
                nodo_id=nodo.id,
            ),
            protocolo=Protocolo(
                transporte="TCP",
                cifrado=None if indice % 10 == 0 else "TLS 1.3",
                aplicacion="HTTP" if indice % 10 == 0 else "HTTPS",
            ),
            bytes_subida=subida,
            bytes_bajada=bajada,
            paquetes_subida=max(1, subida // 1400),
            paquetes_bajada=max(1, bajada // 1400),
            rtt_ms=ruta[-1].latencia_ms * 2,
            estado="cerrado" if indice % 4 == 0 else "activo",
            ruta=ruta,
            confianza_ruta=confianza,
            etiquetas=["ejemplo"],
        ))
    return flujos


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verificar", action="store_true", help="No escribe archivos.")
    args = parser.parse_args()
    flujos = generar(Catalogo())
    contenido = json.dumps(
        [flujo.model_dump() for flujo in flujos], ensure_ascii=False, indent=2
    ) + "\n"
    if args.verificar:
        if not SALIDA.exists() or SALIDA.read_text(encoding="utf-8") != contenido:
            raise SystemExit("La muestra falta o está desactualizada. Regenerala sin --verificar.")
        print("Muestra reproducible: 40 flujos, sin cambios.")
    else:
        SALIDA.write_text(contenido, encoding="utf-8")
        print("Listo: 40 flujos en datos/ejemplo_flujos.json.")


if __name__ == "__main__":
    main()
