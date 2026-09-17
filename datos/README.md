# Datos de TRACE

Contrato compatible con `backend/trace/esquemas.py`. Los JSON se guardan en UTF-8,
con IDs únicos, fechas ISO-8601 UTC y cantidades en bytes (KB = 1.000 bytes).

La base, equipos, MACs y tráfico son ficticios. La infraestructura usa nombres de redes
públicas y coordenadas aproximadas a nivel de ciudad. No es un inventario operativo ni
una medición de conectividad. Consultá [fuentes y alcance](../docs/fuentes.md).

## Archivos

| Archivo | Contenido | Mantenimiento |
| --- | --- | --- |
| `infraestructura.json` | Nodos del mapa y del trazador | Curado |
| `dispositivos.json` | 12 dispositivos iniciales | Curado |
| `organizaciones.json` | Fichas por ASN | Curado |
| `cables.json` | Cables y puntos de amarre representativos | Curado |
| `mezcla_destinos.json` | Destinos elegibles por categoría | Curado |
| `linea_base.json` | Actividad habitual por dispositivo | Curado |
| `guiones/*.json` | Tres ejercicios temporizados | Curado |
| `ejemplo_flujos.json` | 40 flujos listos para el frontend | Generado |
| `herramientas/generar_datos.py` | Exportador de la muestra | Código |
| `herramientas/verificar_datos.py` | Validación de contrato y referencias | Código |

Se mantienen los IDs usados por el backend, las categorías de tráfico y sus guiones.
`dev-13` se incorpora durante el ejercicio; no es uno de los 12 equipos iniciales.
Las etiquetas de ciudades pertenecen al mapa: `geografia` no es un tipo de nodo del contrato.

## Infraestructura

Array de objetos `Nodo`:

| Campo | Tipo | Significado |
| --- | --- | --- |
| `id` | string | Referencia estable usada por rutas, destinos y guiones |
| `tipo` | enum | `dispositivo`, `router`, `isp`, `ixp`, `backbone`, `cable`, `satelite`, `datacenter`, `nube` |
| `nombre` | string | Etiqueta legible |
| `organizacion` | string | Operador o entidad de referencia |
| `asn` | entero | ASN cuando corresponde; `0` significa no asignado en este catálogo, nunca `null` |
| `ciudad` | string | Ciudad de referencia; un cable puede tener un punto representativo oceánico |
| `pais` | string | Código de dos letras; `XX` cuando no se atribuye un país al punto |
| `lat`, `lon` | número | Grados decimales, rangos [-90, 90] y [-180, 180] |
| `capa` | string | `dispositivos`, `isp`, `ixp`, `backbone`, `cables`, `satelites`, `datacenters`, `nubes` |

La base se conserva en Neuquén según el backend integrado. El router es `router-01` y
los nodos de dispositivos usan exactamente los mismos IDs y nombres que su inventario.
Los puntos de amarre tienen `tipo: "cable"`; no representan sensores.

## Dispositivos

Array de objetos `Dispositivo`:

| Campo | Tipo | Significado |
| --- | --- | --- |
| `id` | string | `dev-01` a `dev-12` en el inventario inicial |
| `nombre` | string | Nombre visible del equipo |
| `tipo` | enum | `notebook`, `celular`, `servidor`, `camara`, `sensor`, `impresora`, `tablet`, `desconocido` |
| `ip` | string | Dirección privada ficticia |
| `mac` | string | MAC ficticia y única; se compara sin distinguir mayúsculas |
| `sector` | string | Área de la base |
| `critico` | booleano | Afecta la severidad de algunas reglas; no indica infección |
| `primera_vez_visto` | string | Fecha ISO-8601 UTC de referencia |

`dev-11` es el Sensor de acceso 3. `dev-12` ya está dado de alta.
El dispositivo nuevo del guion debe usar otro ID y otra MAC (`dev-13` en la demo).

## Organizaciones

Array de objetos `Organizacion`, sin ASNs duplicados:

| Campo | Tipo | Significado |
| --- | --- | --- |
| `asn` | entero | Clave para unir destino y organización |
| `nombre` | string | Entidad de referencia |
| `pais` | string | País de referencia de la ficha, distinto del país del nodo |
| `tipo_servicio` | string | CDN, nube, IXP, ISP, backbone, hosting, etc. |
| `jurisdiccion` | string | Referencia orientativa; no resuelve la ley aplicable a un paquete |
| `contexto` | string | Explicación breve en español |

El backend no usa un booleano `conocida`: `asn_desconocido` se dispara cuando falta la
ficha o su nombre es exactamente `AS desconocido`. La ficha de la demo es una excepción
deliberada y ficticia, documentada en las fuentes.

## Cables

Array de objetos con `id`, `nombre`, `organizacion` (strings).
`id` debe existir como nodo de tipo `cable` en infraestructura.

`amarre` conserva el punto representativo que ya usaba el backend:
`ciudad`, `pais` (strings), `lat`, `lon` (números).
`amarres`, cuando existe, amplía esa referencia con una lista de objetos con los mismos
campos más `nodo_id`. Cada `nodo_id` debe existir y coincidir en ciudad, país y coordenadas.
La selección de amarres no es necesariamente completa ni define el trazado físico del cable.

No se publican años de entrada en servicio ni longitudes sin verificar.
No hay un endpoint de cables: la interfaz puede leer este JSON como recurso estático.

## Mezcla de destinos

Objeto `categoría → lista de nodo_id` para `cdn`, `mensajeria`, `nube`, `otros`.
Todos deben existir en infraestructura. Agregar un nodo al mapa no lo incorpora
automáticamente al tráfico: también hay que incluirlo en una categoría.

El simulador procura elegir destinos cuyos ASNs estén en la línea base del dispositivo,
con excepciones poco frecuentes. Cambiar esta lista puede cambiar la secuencia de alertas:
repetí las pruebas de los tres guiones después de editarla.

## Línea base

| Campo | Tipo | Significado |
| --- | --- | --- |
| `generada_con` | string | Procedencia o criterio de calibración de los valores |
| `dispositivos` | objeto | Claves: IDs de los 12 dispositivos iniciales |
| `dispositivos[id].bytes_salida_por_hora` | entero | Volumen saliente habitual por hora |
| `dispositivos[id].asn_habituales` | lista de enteros | ASNs esperables |
| `dispositivos[id].paises_habituales` | lista de strings | Países de referencia |

Son parámetros fijos de demo, no estadísticas obtenidas de una captura.
Se conserva la calibración del backend: `dev-11` tiene **240.000 bytes/hora**.
La regla de volumen compara una ventana de 60 s contra diez veces el promedio horario;
no divide ese promedio por 60. Cambiarlo altera el momento de la correlación.
Reconocer o cerrar alertas no modifica estos valores.

## Guiones

| Campo | Tipo | Significado |
| --- | --- | --- |
| `id` | string | Único, igual al nombre del archivo sin extensión |
| `nombre`, `descripcion` | string | Nombre e intención del ejercicio |
| `duracion_s` | número | Duración en segundos de reloj virtual |
| `semilla` | entero | Determina las elecciones aleatorias del simulador |
| `fondo.flujos_por_segundo` | número | Tasa de creación de flujos |
| `fondo.mezcla` | objeto | Pesos no negativos por categoría; deben sumar 1 |
| `eventos` | lista | Eventos que se ejecutan por orden de `t` |

Cada evento tiene `t` (segundo virtual), `tipo` y `dispositivo_id`:

| `tipo` | Campos adicionales | Uso |
| --- | --- | --- |
| `dispositivo_nuevo` | `nombre`, `ip`, `mac` | Equipo no registrado; ID y MAC nuevos |
| `flujo_forzado` | `destino_id`, `bytes_por_s`, `duracion_s`, `cifrado` | `cifrado: null` para tráfico sin cifrar; todos estos campos van directamente en el evento |
| `cambio_ruta` | `via` | ID de un nodo por el que pasarán los nuevos flujos del equipo |

No se admiten eventos de tipo `esperado`. Las alertas las calcula el motor;
sus tiempos esperados se documentan fuera de `eventos`.

| Guion | Duración | Eventos |
| --- | --- | --- |
| `normal` | 600 s | Sin eventos inyectados; puede producir alertas informativas o medias |
| `exfiltracion-iot` | 180 s | Equipo nuevo a 20 s; sensor a 150.000 B/s durante 120 s desde 45 s; desvío de `dev-03` a 90 s |
| `desvio-de-ruta` | 180 s | `dev-02` vía Madrid a 30 s; `dev-01` vía Ámsterdam a 75 s; flujo sin cifrar de `dev-09` a 120 s |

En el backend integrado, el guion IoT produce `volumen_inusual` **alta** a 58 s
y `secuencia_exfiltracion` **crítica** a 65 s. El plan proponía volumen crítico cerca de
60 s; la severidad actual pertenece a las reglas del backend y no se cambia desde el JSON.
`asn_desconocido` es media. La correlación conserva las tres señales relacionadas.

Con semilla 42, esas señales son `dispositivo_nuevo` de `dev-13` a 20 s,
`destino_nuevo` de `dev-13` hacia Telegram (AS62041) a 22 s y `volumen_inusual`
de `dev-11` a 58 s. El destino desconocido de `dev-11` a 45 s genera su propia
alerta, pero no forma parte de las relacionadas de la crítica. El correlador selecciona
la primera señal de cada regla dentro de la ventana temporal, sin comprobar que
compartan dispositivo, destino o flujo. La coincidencia temporal no demuestra causalidad.

### Agregar un guion

Desde la raíz del repo:

1. Copiá `datos/guiones/normal.json` con un nombre nuevo.
2. Cambiá `id`, `nombre`, `descripcion` y duración.
3. Agregá eventos de los tipos admitidos. Verificá IDs, tiempos y pesos.
4. Ejecutá `PYTHONPATH=backend .venv/bin/python datos/herramientas/verificar_datos.py`.
5. Ensayá el ejercicio: desde `backend/`,
   `../.venv/bin/python -m herramientas.verificar_guion mi-ejercicio 180`.
6. Reiniciá el backend para recargar su catálogo. Consultá `GET /api/guiones` y
   lanzalo con `POST /api/guiones/mi-ejercicio/lanzar`.

El backend valida campos y referencias de destinos al arrancar. La herramienta de
Persona C agrega comprobaciones de unicidad, pesos, MACs y línea base.

## Flujos de ejemplo

Array de 40 objetos `Flujo`; se puede importar directamente desde el frontend.
Es una muestra variada para maquetar y no una grabación de `normal` ni una reproducción
del incidente. Incluye flujos activos y cerrados, con y sin cifrado.

| Campo | Tipo | Significado |
| --- | --- | --- |
| `id` | string | ID único de seis caracteres hexadecimales |
| `ts_inicio` | string | Fecha UTC fija de muestra |
| `dispositivo_id` | string | Origen, presente en el inventario |
| `destino` | objeto | Ver campos debajo |
| `protocolo.transporte` | enum | `TCP` o `UDP` |
| `protocolo.cifrado` | string o null | Por ejemplo `TLS 1.3`; null si no hay cifrado |
| `protocolo.aplicacion` | string | HTTPS, HTTP, DNS, etc. |
| `bytes_subida`, `bytes_bajada` | enteros | Acumulados sintéticos |
| `paquetes_subida`, `paquetes_bajada` | enteros | Contadores sintéticos |
| `rtt_ms` | entero | Estimación de ida y vuelta |
| `estado` | enum | `activo` o `cerrado` |
| `ruta` | lista | Hops en orden desde el equipo hasta el destino |
| `confianza_ruta` | número | Heurística del backend, entre 0 y 1 |
| `etiquetas` | lista de strings | `ejemplo` identifica esta muestra |

`destino` contiene `ip`, `organizacion`, `servicio`, `ciudad`, `pais`, `nodo_id` (strings),
`asn` (entero), `lat`, `lon` (números). Las IPs de muestra usan TEST-NET-2
(`198.51.100.0/24`): no pertenecen a las organizaciones representadas ni se contactan.

Cada hop contiene `nodo_id`, `latencia_ms` acumulada y `observado` (booleano).
El trazador marca backbone, cables y satélites como inferidos. **También los hops
observados son ficticios**: la marca expresa el papel del nodo dentro de la simulación.
La confianza es `max(0.4, 1 - 0.12 × cantidad_de_hops_inferidos)`, redondeada a dos decimales.

## Regeneración y validación

Desde la raíz, después de instalar las dependencias del backend:

```bash
PYTHONPATH=backend .venv/bin/python datos/herramientas/generar_datos.py
PYTHONPATH=backend .venv/bin/python datos/herramientas/verificar_datos.py
PYTHONPATH=backend .venv/bin/python datos/herramientas/generar_datos.py --verificar
.venv/bin/ruff check --config backend/pyproject.toml datos/herramientas
```

El exportador sólo escribe la muestra. Semilla 42, fecha fija, mismos catálogos y mismo
trazador producen el mismo archivo byte a byte; no se usa el reloj ni `hash()` del proceso.
Los demás JSON se mantienen como datos curados. El generador provisional del backend
los reemplaza con el catálogo anterior: no lo uses para regenerar esta entrega.
