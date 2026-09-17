"""Persistencia de alertas en SQLite (lo único que se consulta después de la demo)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from sqlmodel import Field, Session, SQLModel, create_engine, select

from .esquemas import Alerta

RUTA_DB_POR_DEFECTO = Path(__file__).resolve().parents[1] / "trace.db"


def url_por_defecto() -> str:
    """`TRACE_DB` acepta una ruta de archivo o una URL de SQLAlchemy."""
    valor = os.environ.get("TRACE_DB")
    if not valor:
        return f"sqlite:///{RUTA_DB_POR_DEFECTO}"
    return valor if "://" in valor else f"sqlite:///{Path(valor).resolve()}"


class AlertaDB(SQLModel, table=True):
    __tablename__ = "alertas"

    id: str = Field(primary_key=True)
    ts: str
    severidad: str
    regla: str
    titulo: str
    dispositivo_id: str
    flujo_id: str | None = None
    evidencia_json: str = "{}"
    explicacion: str = ""
    accion_sugerida: str = ""
    estado: str = "abierta"
    fuente_explicacion: str = "plantilla"
    relacionadas_json: str = "[]"
    ts_reconocida: str | None = None

    @classmethod
    def desde_alerta(cls, alerta: Alerta) -> AlertaDB:
        return cls(
            id=alerta.id,
            ts=alerta.ts,
            severidad=alerta.severidad,
            regla=alerta.regla,
            titulo=alerta.titulo,
            dispositivo_id=alerta.dispositivo_id,
            flujo_id=alerta.flujo_id,
            evidencia_json=json.dumps(alerta.evidencia, ensure_ascii=False),
            explicacion=alerta.explicacion,
            accion_sugerida=alerta.accion_sugerida,
            estado=alerta.estado,
            fuente_explicacion=alerta.fuente_explicacion,
            relacionadas_json=json.dumps(alerta.alertas_relacionadas),
        )

    def a_alerta(self) -> Alerta:
        return Alerta(
            id=self.id,
            ts=self.ts,
            severidad=self.severidad,
            regla=self.regla,
            titulo=self.titulo,
            dispositivo_id=self.dispositivo_id,
            flujo_id=self.flujo_id,
            evidencia=json.loads(self.evidencia_json),
            explicacion=self.explicacion,
            accion_sugerida=self.accion_sugerida,
            estado=self.estado,
            fuente_explicacion=self.fuente_explicacion,
            alertas_relacionadas=json.loads(self.relacionadas_json),
        )


ORDEN_SEVERIDAD = {"critica": 0, "alta": 1, "media": 2, "info": 3}


class Almacen:
    def __init__(self, url: str | None = None) -> None:
        self.engine = create_engine(url or url_por_defecto(), echo=False)
        SQLModel.metadata.create_all(self.engine)

    def guardar(self, alerta: Alerta) -> None:
        with Session(self.engine) as sesion:
            existente = sesion.get(AlertaDB, alerta.id)
            fila = AlertaDB.desde_alerta(alerta)
            if existente:
                for campo, valor in fila.model_dump(exclude={"ts_reconocida"}).items():
                    setattr(existente, campo, valor)
                sesion.add(existente)
            else:
                sesion.add(fila)
            sesion.commit()

    def listar(self, estado: str | None = None) -> list[Alerta]:
        with Session(self.engine) as sesion:
            consulta = select(AlertaDB)
            if estado:
                consulta = consulta.where(AlertaDB.estado == estado)
            filas = sesion.exec(consulta).all()
        alertas = [f.a_alerta() for f in filas]
        alertas.sort(key=lambda a: (ORDEN_SEVERIDAD.get(a.severidad, 9), a.ts), reverse=False)
        return alertas

    def obtener(self, alerta_id: str) -> Alerta | None:
        with Session(self.engine) as sesion:
            fila = sesion.get(AlertaDB, alerta_id)
        return fila.a_alerta() if fila else None

    def cambiar_estado(self, alerta_id: str, estado: str, ts: str | None = None) -> Alerta | None:
        with Session(self.engine) as sesion:
            fila = sesion.get(AlertaDB, alerta_id)
            if not fila:
                return None
            fila.estado = estado
            if estado == "reconocida" and not fila.ts_reconocida:
                fila.ts_reconocida = ts
            sesion.add(fila)
            sesion.commit()
            sesion.refresh(fila)
            return fila.a_alerta()

    def tiempos_de_reconocimiento(self) -> list[tuple[str, str, str]]:
        with Session(self.engine) as sesion:
            filas = sesion.exec(select(AlertaDB).where(AlertaDB.ts_reconocida.is_not(None))).all()
        return [(f.id, f.ts, f.ts_reconocida) for f in filas]

    def vaciar(self) -> None:
        with Session(self.engine) as sesion:
            for fila in sesion.exec(select(AlertaDB)).all():
                sesion.delete(fila)
            sesion.commit()
