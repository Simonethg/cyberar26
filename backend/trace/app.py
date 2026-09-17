"""Aplicación FastAPI de TRACE."""

from __future__ import annotations

import asyncio
import contextlib
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .motor import Motor
from .rutas.api import router as router_api
from .ws import router as router_ws

GUION_INICIAL = os.environ.get("TRACE_GUION_INICIAL", "normal")


@contextlib.asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    motor = Motor()
    app.state.motor = motor
    await motor.asistente.verificar()
    tarea_precalentado = asyncio.create_task(motor.asistente.precalentar())
    if GUION_INICIAL in motor.catalogo.guiones:
        await motor.lanzar(GUION_INICIAL)
    try:
        yield
    finally:
        tarea_precalentado.cancel()
        await motor.detener()


app = FastAPI(
    title="TRACE",
    description=(
        "Monitor de tráfico de red con visualización geográfica. Todo el tráfico es simulado: "
        "el backend genera flujos a partir de guiones JSON, los rutea sobre la topología pública "
        "de internet, aplica seis reglas de detección explicables y los explica en español con "
        "un modelo local."
    ),
    version="1.0.0",
    lifespan=ciclo_de_vida,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_api)
app.include_router(router_ws)


@app.get("/salud")
async def salud() -> dict:
    return {"ok": True}
