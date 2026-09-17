# TRACE — Mirá adónde van tus datos

Visualizador y analizador de rutas de tráfico de red **simulado** de una base ficticia
(Base Aérea El Chañar). Demo CYBER.AR 2026, 100% local y determinística.

Este repositorio contiene, por ahora, el **backend** (Persona B).

## Requisitos

- Python 3.10+
- Opcional: [Ollama](https://ollama.com) local con `qwen2.5:7b` (si no está, todas las
  explicaciones salen de plantillas en español rioplatense).

## Cómo correrlo

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend && ../.venv/bin/python -m uvicorn trace.app:app --reload --port 8000
```

- API y docs: http://localhost:8000/docs
- WebSocket de eventos: `ws://localhost:8000/ws/flujos`

Variables de entorno útiles:

| Variable | Default | Para qué sirve |
| --- | --- | --- |
| `TRACE_GUION_INICIAL` | `normal` | Guion que arranca con el servidor |
| `TRACE_DB` | `backend/trace.db` | Ruta o URL SQLAlchemy de la base de alertas |
| `TRACE_OLLAMA_URL` | `http://localhost:11434` | Endpoint de Ollama |
| `TRACE_OLLAMA_MODELO` | `qwen2.5:7b` | Modelo preferido |
| `TRACE_OLLAMA_TIMEOUT` | `4` | Timeout en segundos antes del fallback |

## Guiones

- `normal`: operación tranquila, sin alertas altas ni críticas.
- `exfiltracion-iot`: dispositivo no declarado + destino nuevo + pico de volumen; genera
  la alerta crítica correlacionada `secuencia_exfiltracion` a los ~65 s.
- `desvio-de-ruta`: cambio de camino hacia un destino conocido.

Para ver la línea de tiempo de un guion sin levantar el servidor:

```bash
cd backend && ../.venv/bin/python -m herramientas.verificar_guion exfiltracion-iot
```

## Pruebas y lint

```bash
cd backend
../.venv/bin/python -m pytest -q
../.venv/bin/ruff check .
```

## Alcance

El tráfico es **siempre simulado**: no hay captura real de paquetes, ni autenticación,
ni dependencias de internet en tiempo de ejecución.
