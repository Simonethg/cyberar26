# TRACE — Mirá adónde van tus datos

Visualizador y analizador de rutas de tráfico de red **simulado** de una base ficticia
(Base Aérea El Chañar). Demo CYBER.AR 2026, 100% local y determinística.

**CYBER.AR 2026 · Eje 2 — IA para la defensa de redes e infraestructura.**

El repositorio provisional se llama `cyberar26`; el producto se llama **TRACE**.
Incluye el backend de Persona B y los datos, documentación y pitch de Persona C.
También incluye un frontend mínimo de HTML/JS servido por FastAPI: mapamundi en canvas
con rutas en vivo, panel de alertas con detalle y acciones, métricas, top destinos
y resumen de turno. El globo y los controles completos de Persona A siguen pendientes.

## El problema y la propuesta

El destino de un flujo no explica todo su recorrido. Una ruta puede atravesar redes de
terceros y distintos países: el operador necesita reconocer qué dispositivo se comunica,
con quién, por dónde y qué cambió respecto de su actividad habitual.

Hay precedentes públicos. El 12 de noviembre de 2018, una fuga accidental de rutas de
MainOne provocó caminos inusuales e interrupciones de servicios de Google durante 74 minutos.
[El análisis de Cloudflare](https://blog.cloudflare.com/how-a-nigerian-isp-knocked-google-offline/)
explica cómo se propagaron esos anuncios. Es un ejemplo de riesgo de enrutamiento; no implica
que un país de destino o una empresa sean maliciosos.

TRACE propone representar ese viaje sobre un globo: dispositivo → router → ISP → IXP →
backbone/cable → destino. En esta demo, **todos los flujos y recorridos son simulados**.
Los nodos tienen coordenadas de referencia; las rutas no provienen de traceroute ni BGP real.

El backend detecta destino nuevo, ASN desconocido, volumen inusual, cambio de ruta,
dispositivo nuevo y tráfico sin cifrar. Correlaciona señales en `secuencia_exfiltracion`,
con evidencia y línea de base. Esa correlación es una señal para investigar.
La IA local explica alertas y propone acciones: el operador conserva la decisión.

## Encaje con el Eje 2

Mapeo basado en el plan de trabajo recibido para el hackathon:

| Línea del eje | Entrega y estado |
| --- | --- |
| Monitor de la red industrial de una base ficticia | Simulador, API, 12 dispositivos iniciales, catálogo geográfico y mapamundi con rutas en vivo |
| Asistente en español para resumir, clasificar y priorizar alertas | Reglas asignan severidad; Ollama explica alertas graves y resume el turno con fallback |
| Correlación de eventos para reconstruir la secuencia de un ataque | Guion IoT y alerta crítica a los 65 s; correlación temporal sin vínculo causal verificado |
| Infraestructura propia y control de los datos | Backend, SQLite y modelo local; instalar dependencias y descargar el modelo antes de desconectarse |

La crítica del guion IoT combina señales de dos dispositivos: el contacto nuevo de
`dev-13` con Telegram y el volumen de `dev-11`. La alerta del destino desconocido del
sensor existe por separado, pero no está enlazada en la crítica. Es una limitación del
correlador actual, detallada en el [pitch](docs/pitch.md), y no prueba una exfiltración.

| Condición común del plan | Cobertura |
| --- | --- |
| Software puro y demo funcional | Backend ejecutable y frontend mínimo; globo y controles completos pendientes de Persona A |
| Datos simulados o públicos | Base y tráfico ficticios; referencias de infraestructura con alcance documentado |
| IA ejecutada en infraestructura propia | Ollama local opcional, sin API de IA externa |
| Repositorio, README y pitch de tres minutos | Este repositorio y [guion del pitch](docs/pitch.md) |
| Interfaz en español | Datos, alertas, documentación y frontend mínimo en español |

## Requisitos

- Python 3.10+
- Opcional: [Ollama](https://ollama.com) local con `qwen2.5:7b` (`ollama pull qwen2.5:7b`).
  Si no está, todas las explicaciones salen de plantillas en español rioplatense.
  En CPU el modelo tarda ~8 s por respuesta: sólo se mandan al modelo las alertas altas y
  críticas, de a una por vez, y la interfaz nunca espera (la alerta sale con plantilla y se
  reemite cuando el modelo contesta).

## Cómo correrlo

Desde una copia nueva:

```bash
git clone https://github.com/Simonethg/cyberar26.git
cd cyberar26
```

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cd backend && ../.venv/bin/python -m uvicorn trace.app:app --reload --port 8000
```

- Interfaz: http://localhost:8000
- API y docs: http://localhost:8000/docs
- WebSocket de eventos: `ws://localhost:8000/ws/flujos`

Variables de entorno útiles:

| Variable | Default | Para qué sirve |
| --- | --- | --- |
| `TRACE_GUION_INICIAL` | `normal` | Guion que arranca con el servidor |
| `TRACE_DB` | `backend/trace.db` | Ruta o URL SQLAlchemy de la base de alertas |
| `TRACE_OLLAMA_URL` | `http://localhost:11434` | Endpoint de Ollama |
| `TRACE_OLLAMA_MODELO` | `qwen2.5:7b` | Modelo preferido |
| `TRACE_OLLAMA_TIMEOUT` | `12` | Timeout en segundos antes del fallback |
| `TRACE_OLLAMA_TIMEOUT_PRIORITARIO` | `90` | Timeout para alertas graves y resumen de turno |

## Guiones

- `normal`: operación tranquila, sin alertas altas ni críticas.
- `exfiltracion-iot`: dispositivo no declarado + destino nuevo + pico de volumen; genera
  la alerta crítica correlacionada `secuencia_exfiltracion` a los ~65 s.
- `desvio-de-ruta`: cambio de camino hacia un destino conocido.

Para ver la línea de tiempo de un guion sin levantar el servidor:

```bash
cd backend && ../.venv/bin/python -m herramientas.verificar_guion exfiltracion-iot
```

Para agregar un ejercicio, copiá un guion, asignale un `id` único y editá los eventos
admitidos. Validalo y reiniciá el backend. El contrato completo y los comandos están en
[`datos/README.md`](datos/README.md#agregar-un-guion).

## Datos para trabajar sin backend

Los catálogos JSON están versionados y se editan como datos curados. El frontend puede
consumir `infraestructura.json`, `dispositivos.json`, `organizaciones.json` y los
40 flujos de `ejemplo_flujos.json` sin ejecutar Python. La muestra es estática y no genera alertas.
El catálogo incluye 154 nodos, 12 dispositivos iniciales, 35 fichas por ASN, 11 cables
y los tres guiones compatibles con el backend.

Para regenerar la muestra desde la raíz del repo, con las dependencias instaladas:

```bash
PYTHONPATH=backend .venv/bin/python datos/herramientas/generar_datos.py
PYTHONPATH=backend .venv/bin/python datos/herramientas/verificar_datos.py
PYTHONPATH=backend .venv/bin/python datos/herramientas/generar_datos.py --verificar
```

El exportador usa el contrato `Flujo` y el trazador del backend, con semilla y fecha fijas.
No reemplaza los catálogos, los guiones ni la línea base.
El generador provisional de `backend/herramientas/` recrea los datos iniciales de Persona B:
**no lo ejecutes sobre el catálogo curado**, porque lo sobrescribe.

## Pruebas y lint

Instalá las herramientas de desarrollo desde la raíz:

```bash
.venv/bin/pip install pytest==8.3.4 ruff==0.8.4
```

```bash
cd backend
../.venv/bin/python -m pytest -q
../.venv/bin/ruff check .
```

Para las herramientas de Persona C, desde la raíz:

```bash
.venv/bin/ruff check --config backend/pyproject.toml datos/herramientas
```

## Documentación de producto

- [Diccionario de datos y guía de guiones](datos/README.md).
- [Pitch de tres minutos, ensayo y respuestas al jurado](docs/pitch.md).
- [Fuentes y límites de la representación](docs/fuentes.md).

## Alcance

El tráfico es **siempre simulado**: no hay captura real de paquetes, ni autenticación,
ni dependencias de internet en tiempo de ejecución.

La línea de base es fija: reconocer o cerrar una alerta no la entrena.
`jurisdiccion` es una referencia sobre la organización, no una determinación legal sobre
cada paquete. Un hop marcado `observado` también es simulado en esta demo.
La confianza de ruta es una heurística del trazador, no una probabilidad calibrada.
El código no ejecuta las acciones sugeridas por la IA.

El ensayo de tres minutos y la prueba en modo avión quedan pendientes. El pitch distingue
la demo objetivo con globo de lo disponible en el frontend mínimo y por API.
