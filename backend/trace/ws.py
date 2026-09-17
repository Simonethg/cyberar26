"""WebSocket `/ws/flujos`: un mensaje JSON por evento (sección 7 del plan)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/flujos")
async def flujos(websocket: WebSocket) -> None:
    await websocket.accept()
    motor = websocket.app.state.motor
    cola = motor.suscribir()

    # Estado inicial para que el cliente que se conecta tarde no arranque en blanco.
    await websocket.send_json({"tipo": "estado", "datos": motor.estado().model_dump()})
    for flujo in list(motor.flujos.values())[-60:]:
        await websocket.send_json({"tipo": "flujo", "datos": flujo.model_dump()})
    for alerta in motor.almacen.listar("abierta"):
        await websocket.send_json({"tipo": "alerta", "datos": alerta.model_dump()})
    await websocket.send_json({"tipo": "metricas", "datos": motor.metricas().model_dump()})

    try:
        while True:
            mensaje = await cola.get()
            await websocket.send_json(mensaje)
    except (WebSocketDisconnect, asyncio.CancelledError, RuntimeError):
        pass
    finally:
        motor.desuscribir(cola)
