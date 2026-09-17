"""Carga y validación de los archivos de `datos/`.

Si un archivo falta o un campo no cumple el contrato, el backend no arranca y dice
exactamente qué está mal (CU-12).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from .esquemas import Dispositivo, Guion, Nodo, Organizacion

RAIZ = Path(os.environ.get("TRACE_RAIZ", Path(__file__).resolve().parents[2]))
DATOS = Path(os.environ.get("TRACE_DATOS", RAIZ / "datos"))


class DatosInvalidos(RuntimeError):
    pass


def _leer_json(ruta: Path):
    if not ruta.exists():
        raise DatosInvalidos(
            f"Falta el archivo {ruta}. Generalo con "
            f"`python backend/herramientas/generar_datos.py` o pedíselo a Producto."
        )
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatosInvalidos(f"{ruta} no es JSON válido: {exc}") from exc


def _validar(modelo, crudo, ruta: Path):
    try:
        return [modelo.model_validate(item) for item in crudo]
    except ValidationError as exc:
        raise DatosInvalidos(f"{ruta} no cumple el contrato:\n{exc}") from exc


class Catalogo:
    """Todo lo estático que el simulador y la API necesitan en memoria."""

    def __init__(self) -> None:
        self.nodos: list[Nodo] = _validar(Nodo, _leer_json(DATOS / "infraestructura.json"),
                                          DATOS / "infraestructura.json")
        self.dispositivos: list[Dispositivo] = _validar(
            Dispositivo, _leer_json(DATOS / "dispositivos.json"), DATOS / "dispositivos.json"
        )
        self.organizaciones: list[Organizacion] = _validar(
            Organizacion, _leer_json(DATOS / "organizaciones.json"), DATOS / "organizaciones.json"
        )
        self.cables = _leer_json(DATOS / "cables.json")
        self.linea_base = _leer_json(DATOS / "linea_base.json")
        self.mezcla_destinos: dict[str, list[str]] = _leer_json(DATOS / "mezcla_destinos.json")

        self.nodo_por_id = {n.id: n for n in self.nodos}
        self.dispositivo_por_id = {d.id: d for d in self.dispositivos}
        self.organizacion_por_asn = {o.asn: o for o in self.organizaciones}
        self.mac_conocidas = {d.mac.upper() for d in self.dispositivos}

        self.guiones: dict[str, Guion] = {}
        for ruta in sorted((DATOS / "guiones").glob("*.json")):
            crudo = _leer_json(ruta)
            try:
                guion = Guion.model_validate(crudo)
            except ValidationError as exc:
                raise DatosInvalidos(f"El guion {ruta.name} no cumple el contrato:\n{exc}") from exc
            self.guiones[guion.id] = guion

        if not self.guiones:
            raise DatosInvalidos(f"No hay ningún guion en {DATOS / 'guiones'}.")

        self._verificar_referencias()

    def _verificar_referencias(self) -> None:
        for categoria, ids in self.mezcla_destinos.items():
            faltantes = [i for i in ids if i not in self.nodo_por_id]
            if faltantes:
                raise DatosInvalidos(
                    f"mezcla_destinos.json: la categoría '{categoria}' referencia nodos "
                    f"que no están en infraestructura.json: {faltantes}"
                )
        for guion in self.guiones.values():
            for evento in guion.eventos:
                if evento.destino_id and evento.destino_id not in self.nodo_por_id:
                    raise DatosInvalidos(
                        f"El guion '{guion.id}' usa destino_id '{evento.destino_id}', "
                        f"que no existe en infraestructura.json."
                    )
                if evento.via and evento.via not in self.nodo_por_id:
                    raise DatosInvalidos(
                        f"El guion '{guion.id}' usa via '{evento.via}', "
                        f"que no existe en infraestructura.json."
                    )

    def linea_base_de(self, dispositivo_id: str) -> dict:
        return self.linea_base.get("dispositivos", {}).get(
            dispositivo_id,
            {"bytes_salida_por_hora": 1_000_000, "asn_habituales": [], "paises_habituales": []},
        )


@lru_cache(maxsize=1)
def catalogo() -> Catalogo:
    return Catalogo()
