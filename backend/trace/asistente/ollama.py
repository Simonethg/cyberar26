"""Asistente en español: Ollama local con timeout y fallback a plantillas.

La interfaz nunca espera al modelo: la alerta sale con su plantilla y, si el modelo
contesta dentro del timeout, se reemplaza la explicación y se reemite.
"""

from __future__ import annotations

import json
import os

import httpx

from ..esquemas import Alerta, ResumenTurno

URL_OLLAMA = os.environ.get("TRACE_OLLAMA_URL", "http://localhost:11434")
MODELO = os.environ.get("TRACE_OLLAMA_MODELO", "qwen2.5:7b")
MODELO_ALTERNATIVO = os.environ.get("TRACE_OLLAMA_MODELO_ALT", "llama3.1:8b")
TIMEOUT_S = float(os.environ.get("TRACE_OLLAMA_TIMEOUT", "4"))

SISTEMA = (
    "Sos un analista de SOC argentino. Explicá la alerta en dos oraciones en español "
    "rioplatense, con voseo, sin tecnicismos innecesarios, y proponé una acción concreta. "
    "No inventes datos que no estén en la evidencia. Respondé sólo un JSON con las claves "
    '"explicacion" y "accion_sugerida".'
)


class Asistente:
    def __init__(self) -> None:
        self.conectado = False
        self.modelo = MODELO

    async def verificar(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=1.5) as cliente:
                respuesta = await cliente.get(f"{URL_OLLAMA}/api/tags")
                respuesta.raise_for_status()
                modelos = [m.get("name", "") for m in respuesta.json().get("models", [])]
        except Exception:
            self.conectado = False
            return False

        for candidato in (MODELO, MODELO_ALTERNATIVO):
            if any(nombre.startswith(candidato.split(":")[0]) for nombre in modelos):
                self.modelo = candidato
                self.conectado = True
                return True
        self.conectado = bool(modelos)
        if modelos:
            self.modelo = modelos[0]
        return self.conectado

    async def _generar(self, prompt: str, sistema: str = SISTEMA) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_S) as cliente:
                respuesta = await cliente.post(
                    f"{URL_OLLAMA}/api/generate",
                    json={
                        "model": self.modelo,
                        "system": sistema,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.2},
                    },
                )
                respuesta.raise_for_status()
                return respuesta.json().get("response", "").strip()
        except Exception:
            self.conectado = False
            return None

    async def explicar(self, alerta: Alerta) -> Alerta:
        """Devuelve la alerta con la explicación del modelo, o la plantilla si no responde."""
        carga = alerta.model_dump(include={
            "regla", "severidad", "titulo", "dispositivo_id", "evidencia", "explicacion",
        })
        texto = await self._generar(json.dumps(carga, ensure_ascii=False))
        if not texto:
            alerta.fuente_explicacion = "plantilla"
            return alerta

        datos = _json_flexible(texto)
        if not datos or not datos.get("explicacion"):
            alerta.fuente_explicacion = "plantilla"
            return alerta

        alerta.explicacion = datos["explicacion"].strip()
        if datos.get("accion_sugerida"):
            alerta.accion_sugerida = datos["accion_sugerida"].strip()
        alerta.fuente_explicacion = "ollama"
        self.conectado = True
        return alerta

    async def resumen_turno(self, alertas: list[Alerta]) -> ResumenTurno:
        plantilla = _plantilla_resumen(alertas)
        if not self.conectado:
            return ResumenTurno(texto=plantilla, fuente="plantilla")

        resumen = [
            {"severidad": a.severidad, "titulo": a.titulo, "dispositivo_id": a.dispositivo_id,
             "explicacion": a.explicacion}
            for a in alertas
        ]
        texto = await self._generar(
            json.dumps({"alertas_abiertas": resumen}, ensure_ascii=False),
            sistema=(
                "Sos un analista de SOC argentino. Escribí un párrafo corto en español "
                "rioplatense, con voseo, para el jefe de turno: qué pasó, qué es lo más urgente "
                "y qué conviene hacer. No inventes datos. Respondé sólo el párrafo, sin JSON."
            ),
        )
        if not texto:
            return ResumenTurno(texto=plantilla, fuente="plantilla")
        # Algunos modelos contestan igual en JSON aunque se les pida un párrafo.
        datos = _json_flexible(texto)
        if datos:
            texto = next((datos[c] for c in ("texto", "resumen", "explicacion") if datos.get(c)),
                         plantilla)
        return ResumenTurno(texto=texto.strip(), fuente="ollama")


def _json_flexible(texto: str) -> dict | None:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.strip("`")
        texto = texto[texto.find("{"):] if "{" in texto else texto
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fin == -1:
        return None
    try:
        return json.loads(texto[inicio:fin + 1])
    except json.JSONDecodeError:
        return None


def _plantilla_resumen(alertas: list[Alerta]) -> str:
    if not alertas:
        return "El turno viene tranquilo: no hay alertas abiertas. Seguí mirando el mapa."
    por_severidad = {s: [a for a in alertas if a.severidad == s]
                     for s in ("critica", "alta", "media", "info")}
    partes = [f"{len(v)} {k}" for k, v in por_severidad.items() if v]
    primera = next((a for s in ("critica", "alta", "media", "info")
                    for a in por_severidad[s]), None)
    detalle = (f" Lo más urgente: {primera.titulo.lower()} — {primera.explicacion}"
               if primera else "")
    return (
        f"Tenés {len(alertas)} alertas abiertas ({', '.join(partes)})."
        f"{detalle} Empezá por esa y después revisá el resto."
    )
