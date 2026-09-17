"""Endpoints REST (sección 7 del plan)."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from ..esquemas import (
    Alerta,
    DestinoTop,
    DispositivoConMetricas,
    EstadoSistema,
    EvaluacionEjercicio,
    Flujo,
    Guion,
    MetricasDispositivo,
    MetricasGlobal,
    Nodo,
    Organizacion,
    Paquete,
    ResumenTurno,
)
from ..informes import informe_pdf

router = APIRouter(prefix="/api")


def motor_de(request: Request):
    return request.app.state.motor


@router.get("/estado", response_model=EstadoSistema)
async def estado(request: Request) -> EstadoSistema:
    return motor_de(request).estado()


@router.get("/dispositivos", response_model=list[DispositivoConMetricas])
async def dispositivos(request: Request) -> list[DispositivoConMetricas]:
    motor = motor_de(request)
    abiertas = motor.almacen.listar("abierta")
    salida = []
    for dispositivo in motor.dispositivos():
        flujos = [f for f in motor.flujos.values() if f.dispositivo_id == dispositivo.id]
        salida.append(DispositivoConMetricas(
            **dispositivo.model_dump(),
            metricas=MetricasDispositivo(
                flujos_activos=len([f for f in flujos if f.estado == "activo"]),
                bytes_hora=sum(f.bytes_subida + f.bytes_bajada for f in flujos),
                alertas_abiertas=len([a for a in abiertas if a.dispositivo_id == dispositivo.id]),
            ),
        ))
    salida.sort(key=lambda d: (-d.metricas.alertas_abiertas, d.id))
    return salida


@router.get("/dispositivos/{dispositivo_id}")
async def dispositivo(request: Request, dispositivo_id: str) -> dict:
    motor = motor_de(request)
    encontrado = next((d for d in motor.dispositivos() if d.id == dispositivo_id), None)
    if not encontrado:
        raise HTTPException(404, f"No existe el dispositivo {dispositivo_id}")
    flujos = [f for f in motor.flujos.values() if f.dispositivo_id == dispositivo_id]
    por_organizacion: dict[str, int] = {}
    for flujo in flujos:
        por_organizacion[flujo.destino.organizacion] = (
            por_organizacion.get(flujo.destino.organizacion, 0)
            + flujo.bytes_subida + flujo.bytes_bajada
        )
    principales = sorted(por_organizacion.items(), key=lambda kv: kv[1], reverse=True)[:7]
    return {
        "dispositivo": encontrado.model_dump(),
        "linea_base": motor.catalogo.linea_base_de(dispositivo_id),
        "flujos_activos": len([f for f in flujos if f.estado == "activo"]),
        "destinos_principales": [{"organizacion": o, "bytes": b} for o, b in principales],
        "alertas": [a.model_dump() for a in motor.almacen.listar()
                    if a.dispositivo_id == dispositivo_id],
    }


@router.get("/infraestructura", response_model=list[Nodo])
async def infraestructura(request: Request) -> list[Nodo]:
    return motor_de(request).catalogo.nodos


@router.get("/flujos", response_model=list[Flujo])
async def flujos(request: Request, activos: bool = True, limite: int = 200,
                 dispositivo_id: str | None = None) -> list[Flujo]:
    motor = motor_de(request)
    seleccion = list(motor.flujos.values())
    if activos:
        seleccion = [f for f in seleccion if f.estado == "activo"]
    if dispositivo_id:
        seleccion = [f for f in seleccion if f.dispositivo_id == dispositivo_id]
    seleccion.sort(key=lambda f: f.bytes_subida + f.bytes_bajada, reverse=True)
    return seleccion[:limite]


@router.get("/flujos/{flujo_id}")
async def flujo(request: Request, flujo_id: str) -> dict:
    motor = motor_de(request)
    encontrado = motor.flujos.get(flujo_id)
    if not encontrado:
        raise HTTPException(404, f"No existe el flujo {flujo_id}")
    paquetes = [p for p in motor.paquetes if p.flujo_id == flujo_id]
    nodos = [motor.catalogo.nodo_por_id[h.nodo_id].model_dump()
             for h in encontrado.ruta if h.nodo_id in motor.catalogo.nodo_por_id]
    return {
        "flujo": encontrado.model_dump(),
        "nodos_ruta": nodos,
        "paquetes": [p.model_dump() for p in paquetes],
    }


@router.get("/paquetes", response_model=list[Paquete])
async def paquetes(request: Request, dispositivo_id: str | None = None,
                   limite: int = 200) -> list[Paquete]:
    motor = motor_de(request)
    seleccion = list(motor.paquetes)
    if dispositivo_id:
        seleccion = [p for p in seleccion if p.dispositivo_id == dispositivo_id]
    return seleccion[-limite:]


@router.get("/metricas/global", response_model=MetricasGlobal)
async def metricas_global(request: Request) -> MetricasGlobal:
    return motor_de(request).metricas()


@router.get("/metricas/destinos", response_model=list[DestinoTop])
async def metricas_destinos(request: Request,
                            por: str = Query("bytes", pattern="^(bytes|paquetes|flujos)$"),
                            limite: int = 7) -> list[DestinoTop]:
    return motor_de(request).destinos_top(por=por, limite=limite)


@router.get("/alertas", response_model=list[Alerta])
async def alertas(request: Request, estado: str | None = None) -> list[Alerta]:
    return motor_de(request).almacen.listar(estado)


@router.get("/alertas/export.csv")
async def exportar_alertas(request: Request) -> Response:
    motor = motor_de(request)
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";")
    escritor.writerow(["id", "hora", "severidad", "regla", "titulo", "dispositivo", "destino",
                       "estado", "fuente", "explicacion", "accion_sugerida"])
    for alerta in motor.almacen.listar():
        dispositivo = next((d for d in motor.dispositivos() if d.id == alerta.dispositivo_id), None)
        escritor.writerow([
            alerta.id, alerta.ts, alerta.severidad, alerta.regla, alerta.titulo,
            dispositivo.nombre if dispositivo else alerta.dispositivo_id,
            alerta.evidencia.get("destino", ""), alerta.estado, alerta.fuente_explicacion,
            alerta.explicacion, alerta.accion_sugerida,
        ])
    # BOM para que Excel abra los acentos bien.
    contenido = "\ufeff" + buffer.getvalue()
    return Response(
        contenido.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="alertas-trace.csv"'},
    )


@router.get("/alertas/{alerta_id}", response_model=Alerta)
async def alerta(request: Request, alerta_id: str) -> Alerta:
    encontrada = motor_de(request).almacen.obtener(alerta_id)
    if not encontrada:
        raise HTTPException(404, f"No existe la alerta {alerta_id}")
    return encontrada


@router.post("/alertas/{alerta_id}/reconocer", response_model=Alerta)
async def reconocer(request: Request, alerta_id: str) -> Alerta:
    alerta = motor_de(request).cambiar_estado_alerta(alerta_id, "reconocida")
    if not alerta:
        raise HTTPException(404, f"No existe la alerta {alerta_id}")
    return alerta


@router.post("/alertas/{alerta_id}/cerrar", response_model=Alerta)
async def cerrar(request: Request, alerta_id: str) -> Alerta:
    alerta = motor_de(request).cambiar_estado_alerta(alerta_id, "cerrada")
    if not alerta:
        raise HTTPException(404, f"No existe la alerta {alerta_id}")
    return alerta


@router.post("/asistente/resumen-turno", response_model=ResumenTurno)
async def resumen_turno(request: Request) -> ResumenTurno:
    motor = motor_de(request)
    return await motor.asistente.resumen_turno(motor.almacen.listar("abierta"))


@router.get("/organizaciones/{asn}", response_model=Organizacion)
async def organizacion(request: Request, asn: int) -> Organizacion:
    encontrada = motor_de(request).catalogo.organizacion_por_asn.get(asn)
    if not encontrada:
        raise HTTPException(404, f"No conocemos el AS {asn}")
    return encontrada


@router.get("/guiones", response_model=list[Guion])
async def guiones(request: Request) -> list[Guion]:
    return list(motor_de(request).catalogo.guiones.values())


@router.post("/guiones/{guion_id}/lanzar", response_model=EstadoSistema)
async def lanzar_guion(request: Request, guion_id: str) -> EstadoSistema:
    motor = motor_de(request)
    try:
        await motor.lanzar(guion_id)
    except KeyError:
        raise HTTPException(404, f"No existe el guion {guion_id}") from None
    return motor.estado()


@router.post("/guiones/detener", response_model=EvaluacionEjercicio)
async def detener_guion(request: Request) -> EvaluacionEjercicio:
    motor = motor_de(request)
    evaluacion = motor.evaluacion()
    await motor.detener()
    return evaluacion


@router.get("/informes/turno.pdf")
async def informe_turno(request: Request) -> Response:
    motor = motor_de(request)
    resumen = await motor.asistente.resumen_turno(motor.almacen.listar("abierta"))
    pdf = informe_pdf(
        generado=datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        metricas=motor.metricas(),
        destinos=motor.destinos_top(limite=10),
        alertas=motor.almacen.listar(),
        resumen=resumen.texto,
    )
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="informe-turno-trace.pdf"'},
    )
