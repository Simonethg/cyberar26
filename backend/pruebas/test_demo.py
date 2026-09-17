"""La demo tiene que ser siempre igual: mismos tiempos, misma alerta crítica."""

from __future__ import annotations

from trace.almacen import Almacen
from trace.app import app
from trace.motor import Motor

import pytest
from fastapi.testclient import TestClient

T_CRITICA_ESPERADA = 65.0
TOLERANCIA_S = 2.0


def correr(guion_id: str, hasta: float) -> list[tuple[float, object]]:
    motor = Motor(almacen=Almacen("sqlite://"))
    motor.preparar(guion_id)
    linea_tiempo = []
    while True:
        t, alertas, terminado = motor.paso()
        linea_tiempo += [(t, a) for a in alertas]
        if terminado or t >= hasta:
            return linea_tiempo


def test_exfiltracion_dispara_una_critica_correlacionada_a_los_65s():
    linea_tiempo = correr("exfiltracion-iot", 120)
    criticas = [(t, a) for t, a in linea_tiempo if a.severidad == "critica"]
    assert len(criticas) == 1
    t, alerta = criticas[0]
    assert alerta.regla == "secuencia_exfiltracion"
    assert abs(t - T_CRITICA_ESPERADA) <= TOLERANCIA_S
    assert alerta.dispositivo_id == "dev-11"
    assert len(alerta.alertas_relacionadas) == 3
    assert alerta.explicacion and alerta.accion_sugerida


def test_la_secuencia_es_deterministica():
    primera = [(t, a.regla, a.dispositivo_id) for t, a in correr("exfiltracion-iot", 90)]
    segunda = [(t, a.regla, a.dispositivo_id) for t, a in correr("exfiltracion-iot", 90)]
    assert primera == segunda


def test_la_operacion_normal_casi_no_alerta():
    linea_tiempo = correr("normal", 300)
    assert not [a for _t, a in linea_tiempo if a.severidad in {"alta", "critica"}]
    assert len(linea_tiempo) <= 5


def test_el_desvio_de_ruta_se_detecta_despues_del_evento():
    linea_tiempo = correr("desvio-de-ruta", 120)
    cambios = [t for t, a in linea_tiempo if a.regla == "cambio_ruta"]
    assert cambios and 30 <= cambios[0] <= 60


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setenv("TRACE_DB", f"sqlite:///{tmp_path/'alertas.db'}")
    with TestClient(app) as cliente:
        yield cliente


def test_los_endpoints_principales_responden(cliente):
    assert cliente.get("/api/estado").json()["guion_activo"] == "normal"
    assert len(cliente.get("/api/infraestructura").json()) > 50
    assert len(cliente.get("/api/dispositivos").json()) == 12
    assert {g["id"] for g in cliente.get("/api/guiones").json()} == {
        "normal", "exfiltracion-iot", "desvio-de-ruta"}
    assert cliente.get("/api/organizaciones/13335").json()["nombre"] == "Cloudflare"
    assert cliente.get("/api/organizaciones/999999").status_code == 404
    assert "mbps_subida" in cliente.get("/api/metricas/global").json()
    assert cliente.get("/api/alertas/export.csv").headers["content-type"].startswith("text/csv")
    assert cliente.get("/api/informes/turno.pdf").content.startswith(b"%PDF")


def test_el_websocket_manda_el_estado_inicial(cliente):
    with cliente.websocket_connect("/ws/flujos") as ws:
        primero = ws.receive_json()
        assert primero["tipo"] == "estado"
        tipos = {ws.receive_json()["tipo"] for _ in range(5)}
        assert tipos & {"flujo", "metricas", "paquete", "alerta", "guion"}


def test_reconocer_y_cerrar_alertas(cliente):
    cliente.post("/api/guiones/exfiltracion-iot/lanzar")
    motor = cliente.app.state.motor
    for _ in range(4 * 70):
        motor.paso()
    alertas = cliente.get("/api/alertas").json()
    assert any(a["severidad"] == "critica" for a in alertas)

    alerta_id = alertas[0]["id"]
    assert cliente.post(f"/api/alertas/{alerta_id}/reconocer").json()["estado"] == "reconocida"
    assert cliente.post(f"/api/alertas/{alerta_id}/cerrar").json()["estado"] == "cerrada"
    assert cliente.post("/api/alertas/al-9999/reconocer").status_code == 404
    assert [a["id"] for a in cliente.get("/api/alertas?estado=cerrada").json()] == [alerta_id]
    evaluacion = cliente.post("/api/guiones/detener").json()
    assert evaluacion["alertas_generadas"] >= 5
