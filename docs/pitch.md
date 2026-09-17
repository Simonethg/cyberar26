# TRACE · Mirá adónde van tus datos

**Pitch de tres minutos · Persona C · CYBER.AR 2026 · Eje 2**

Este es el guion objetivo para ensayar con la interfaz de Persona A integrada.
En esta rama están el backend y los datos; el globo, paneles y sus controles todavía
no están disponibles. La alternativa por API aparece al final.

## Preparación

1. Instalá dependencias, descargá el modelo Ollama y los recursos del frontend antes
   de desconectarte. No esperes a la presentación para descargar el modelo.
2. Ejecutá las pruebas y el verificador desde `backend/`:
   `../.venv/bin/python -m herramientas.verificar_guion exfiltracion-iot 95`.
   Debe aparecer una sola crítica a los 65 s de reloj virtual.
3. Ensayá el asistente en el hardware de la demo. La cola local procesa de a uno:
   si tarda o entra el fallback, mostrá la evidencia sin esperar una respuesta instantánea.
4. Con la interfaz integrada, dejá TRACE en primer plano, mapa en Argentina,
   inventario inicial visible, todas las capas necesarias y velocidad 1×.
   Prepará una grabación sólo después de probar ese recorrido.
5. Probá previamente desconectar internet con todo ya cargado. Si hay un recurso remoto
   faltante, corregilo antes de prometer modo avión en vivo.

## Guion cronometrado

### 0:00–0:25 · El problema

**Pantalla:** Base Aérea El Chañar en Argentina. Aclaración visible: «Tráfico simulado».

> «Una base puede saber cuánto tráfico sale de su red y aun así no saber por dónde
> viaja. Un servicio puede cruzar proveedores y países que el operador no esperaba.
> TRACE pone ese recorrido a la vista y conecta los cambios de la red con sus alertas.»

### 0:25–0:45 · Seguir una ruta

**Acción:** lanzar `exfiltracion-iot` a velocidad 1× exactamente a 0:25.
Seleccionar un flujo habitual y recorrer router, ISP, IXP, cable y destino.

> «Esta base y su tráfico son ficticios. Cada arco une un dispositivo con su destino.
> Podemos recorrer los saltos y consultar la organización y el país de referencia.
> Los tramos de cable y backbone son inferidos; la confianza indica esa aproximación.»

### 0:45–1:30 · Ver la secuencia

**Pantalla:** el reloj del ejercicio sigue corriendo.

| Reloj del pitch | Reloj del guion | Señal |
| --- | --- | --- |
| 0:45 | 20 s | `dev-13`: dispositivo nuevo, informativa |
| 0:47 | 22 s | `dev-13`: destino nuevo, Telegram, media |
| 1:10 | 45 s | `dev-11`: destino nuevo, ASN ficticio desconocido y tráfico sin cifrar |
| 1:23 | 58 s | Volumen inusual, alta |
| 1:30 | 65 s | Secuencia de exfiltración, crítica |

> «Aparece un equipo no declarado y contacta un destino fuera de su línea base.
> Después, el sensor de acceso envía datos a un destino desconocido y aumenta su volumen.
> TRACE junta eventos de distintos equipos por cercanía temporal:
> es una hipótesis para revisar, no una prueba de exfiltración.»

**Acción:** abrir la crítica de `dev-11` y mostrar sus tres alertas relacionadas.
Con semilla 42, enlaza el dispositivo nuevo `dev-13` a 20 s, su contacto con
Telegram (AS62041) a 22 s y el volumen de `dev-11` a 58 s. La alerta del destino
desconocido del sensor a 45 s existe por separado: **no está enlazada en la crítica**.
El correlador toma la primera señal disponible de cada regla dentro de la ventana;
no exige un mismo dispositivo, destino ni flujo. No presentar a Telegram como malicioso
ni contar `dev-13` como si fuera el sensor.

### 1:30–1:55 · De la alerta a la decisión

> «Acá están los eventos que sostienen la prioridad y la comparación con lo habitual.
> La IA local los explica en español y propone un siguiente paso para el operador.
> Las reglas detectan y priorizan; la IA no decide qué bloquear. La persona revisa,
> reconoce la alerta y deja constancia de su intervención.»

**Acción:** señalar explicación, acción sugerida y evidencia. Reconocer la crítica.
El desvío secundario de `dev-03` comienza en el segundo 90 del ejercicio, a 1:55 del pitch:
no es necesario abrirlo para contar la historia principal.

### 1:55–2:20 · Resumen del turno

**Acción:** pedir resumen para jefe de turno y mostrar el resultado disponible.

> «Al terminar el turno necesitamos transmitir lo importante, no una lista interminable.
> El asistente resume los eventos con evidencia y recomendaciones. Corre en la máquina
> local. Si el modelo no responde, las plantillas mantienen disponible la explicación
> básica y el monitoreo sigue funcionando.»

Si devuelve `fuente: "plantilla"`, decirlo. No presentar esa respuesta como inferencia del modelo.

### 2:20–2:40 · Continuidad sin internet

**Acción, sólo si ya se ensayó:** desconectar internet y mostrar actividad local.

> «Con los recursos preparados, el sistema puede trabajar sin conexión externa.
> Los datos de la demo y las alertas quedan en infraestructura propia.
> El ejercicio es repetible: misma semilla, mismos eventos y una secuencia que permite
> entrenar al operador sin intervenir una red real.»

### 2:40–3:00 · Cierre

> «TRACE reúne visibilidad de rutas, detección, correlación y una explicación en español.
> Para ampliar el entrenamiento se agrega un guion JSON y se vuelve a ensayar.
> Entregamos el repositorio, datos y documentación para continuar el trabajo.
> TRACE: mirá adónde van tus datos.»

Si falta el frontend, reemplazar «entregamos» por la enumeración del alcance disponible
al presentar. No afirmar que se probó la demo visual ni modo avión antes de hacerlo.

## Alternativa disponible por API

Con el backend iniciado según el README, abrir la documentación local de FastAPI
en `http://127.0.0.1:8000/docs`. Ejecución equivalente desde una terminal:

```bash
curl -fsS -X POST http://127.0.0.1:8000/api/guiones/exfiltracion-iot/lanzar
curl -fsS http://127.0.0.1:8000/api/estado
curl -fsS http://127.0.0.1:8000/api/dispositivos
# Consultar después de los 65 s virtuales para ver la crítica.
curl -fsS http://127.0.0.1:8000/api/alertas
curl -fsS -X POST http://127.0.0.1:8000/api/asistente/resumen-turno
```

Si no se puede esperar el reloj real, el verificador de consola muestra la línea de tiempo
a reloj acelerado y usa plantillas; no necesita servidor, modelo ni red.
Los 40 flujos estáticos permiten maquetar una interfaz sin servidor, pero no animan la
secuencia de alertas por sí solos.

## Preguntas del jurado

**¿Esto captura tráfico real?** No. El alcance acordado usa metadatos y recorridos
simulados. Una integración con telemetría real es trabajo posterior y requiere permisos.

**¿Qué tiene que ver con ciberdefensa?** Visibilidad de comunicaciones de una base,
detección de cambios, correlación de señales y entrenamiento del operador. Los cuatro
puntos del Eje 2 y su estado están detallados en el README.

**¿Dónde está la IA?** Ollama local explica alertas graves y resume el turno. La detección,
severidad y correlación actuales se basan en reglas. El fallback se identifica como plantilla.

**¿Qué determina la confianza del camino?** Una heurística según la cantidad de saltos
inferidos. No representa una certeza medida ni verifica la ruta física de un paquete.

**¿Una ruta fuera de Argentina significa un ataque?** No. El destino, el cambio de volumen
y la actividad habitual aportan contexto. La jurisdicción de una ficha tampoco resuelve
por sí sola el régimen legal de cada dato.

**¿La crítica demuestra que los eventos están conectados?** No. La regla actual combina
señales dentro de una ventana temporal sin comprobar que compartan dispositivo o destino.
En el guion IoT, el destino nuevo enlazado pertenece a `dev-13`, mientras que el volumen
pertenece al sensor `dev-11`. Esa limitación debe resolverse en el backend para atribuir
una secuencia concreta; la plantilla de explicación no aporta evidencia adicional.

**¿Por qué el ASN desconocido está en la tabla?** Es una ficha pedagógica que el backend
reconoce por su nombre. Usa un ASN reservado para documentación, sin atribuir el ejercicio
a una organización real.

**¿Aprende si marco una alerta como normal?** No. Reconocer/cerrar cambia el estado de
atención. La línea base sigue siendo la calibración fija del ejercicio.

**¿Aísla equipos o bloquea conexiones?** No. Sugiere acciones y registra la atención de
alertas; el operador ejecutaría cualquier respuesta en sus herramientas autorizadas.

**¿Qué está verificado y qué falta?** Contratos, referencias, reproducción de datos,
pruebas del backend y cronometraje por consola. Faltan la integración visual, el ensayo
de tres minutos, la latencia del modelo en el equipo final y el ensayo sin internet.
