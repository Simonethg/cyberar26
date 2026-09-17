"""Contrato de datos entre backend y frontend (sección 3 del plan)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TipoNodo = Literal[
    "dispositivo", "router", "isp", "ixp", "backbone", "cable", "satelite", "datacenter", "nube"
]
TipoDispositivo = Literal[
    "notebook", "celular", "servidor", "camara", "sensor", "impresora", "tablet", "desconocido"
]
Severidad = Literal["info", "media", "alta", "critica"]
EstadoAlerta = Literal["abierta", "reconocida", "cerrada"]
FuenteExplicacion = Literal["ollama", "plantilla"]


class Nodo(BaseModel):
    id: str
    tipo: TipoNodo
    nombre: str
    organizacion: str
    asn: int = 0
    ciudad: str
    pais: str
    lat: float
    lon: float
    capa: str


class Dispositivo(BaseModel):
    id: str
    nombre: str
    tipo: TipoDispositivo
    ip: str
    mac: str
    sector: str
    critico: bool = False
    primera_vez_visto: str


class MetricasDispositivo(BaseModel):
    flujos_activos: int = 0
    bytes_hora: int = 0
    alertas_abiertas: int = 0


class DispositivoConMetricas(Dispositivo):
    metricas: MetricasDispositivo = Field(default_factory=MetricasDispositivo)


class Organizacion(BaseModel):
    asn: int
    nombre: str
    pais: str
    tipo_servicio: str
    jurisdiccion: str
    contexto: str


class Destino(BaseModel):
    ip: str
    asn: int
    organizacion: str
    servicio: str
    ciudad: str
    pais: str
    lat: float
    lon: float
    nodo_id: str


class Protocolo(BaseModel):
    transporte: Literal["TCP", "UDP"] = "TCP"
    cifrado: str | None = None
    aplicacion: str = "HTTPS"


class Hop(BaseModel):
    nodo_id: str
    latencia_ms: int
    observado: bool


class Flujo(BaseModel):
    id: str
    ts_inicio: str
    dispositivo_id: str
    destino: Destino
    protocolo: Protocolo
    bytes_subida: int = 0
    bytes_bajada: int = 0
    paquetes_subida: int = 0
    paquetes_bajada: int = 0
    rtt_ms: int = 0
    estado: Literal["activo", "cerrado"] = "activo"
    ruta: list[Hop] = Field(default_factory=list)
    confianza_ruta: float = 1.0
    etiquetas: list[str] = Field(default_factory=list)


class Paquete(BaseModel):
    ts: str
    flujo_id: str
    dispositivo_id: str
    direccion: Literal["SAL", "ENT"]
    origen: str
    destino: str
    protocolo: str
    tamano: int
    info: str


class Alerta(BaseModel):
    id: str
    ts: str
    severidad: Severidad
    regla: str
    titulo: str
    dispositivo_id: str
    flujo_id: str | None = None
    evidencia: dict = Field(default_factory=dict)
    explicacion: str = ""
    accion_sugerida: str = ""
    estado: EstadoAlerta = "abierta"
    fuente_explicacion: FuenteExplicacion = "plantilla"
    alertas_relacionadas: list[str] = Field(default_factory=list)


class MetricasGlobal(BaseModel):
    mbps_bajada: float = 0.0
    mbps_subida: float = 0.0
    flujos_activos: int = 0
    destinos: int = 0
    porcentaje_cifrado: float = 0.0
    alertas_abiertas: int = 0


class DestinoTop(BaseModel):
    organizacion: str
    asn: int
    valor: int
    porcentaje: float


class EventoGuion(BaseModel):
    t: float
    tipo: Literal["dispositivo_nuevo", "flujo_forzado", "cambio_ruta"]
    dispositivo_id: str
    # dispositivo_nuevo
    nombre: str | None = None
    mac: str | None = None
    ip: str | None = None
    # flujo_forzado
    destino_id: str | None = None
    bytes_por_s: int | None = None
    duracion_s: float | None = None
    cifrado: str | None = None
    # cambio_ruta
    via: str | None = None


class Fondo(BaseModel):
    flujos_por_segundo: float = 6
    mezcla: dict[str, float] = Field(default_factory=dict)


class Guion(BaseModel):
    id: str
    nombre: str
    descripcion: str = ""
    duracion_s: float
    semilla: int = 42
    fondo: Fondo = Field(default_factory=Fondo)
    eventos: list[EventoGuion] = Field(default_factory=list)


class EstadoSistema(BaseModel):
    en_vivo: bool
    guion_activo: str | None
    t: float = 0.0
    duracion_s: float = 0.0
    ia_conectada: bool = False
    modelo: str = ""


class ResumenTurno(BaseModel):
    texto: str
    fuente: FuenteExplicacion


class EvaluacionEjercicio(BaseModel):
    guion_id: str
    alertas_generadas: int
    alertas_reconocidas: int
    segundos_hasta_reconocer_critica: float | None = None
    texto: str


def ahora_iso() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
