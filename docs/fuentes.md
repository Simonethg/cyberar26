# Fuentes y alcance de los datos

Consulta: 17 de septiembre de 2026. Catálogo para una demo defensiva; no usar para
planificar enlaces, atribuir incidentes o determinar obligaciones legales.

## Qué es ficticio

- Base Aérea El Chañar, su ubicación de demo en Neuquén, equipos, personas y sectores.
- MACs, IPs de dispositivos, flujos, paquetes, volúmenes, latencias y alertas.
- Los recorridos del trazador: ni BGP, traceroute ni capturas alimentan esta versión.
- El destino `dc-desconocido-nl`. Usa **AS65536**, reservado para documentación por
  [RFC 5398](https://www.rfc-editor.org/rfc/rfc5398).
  No se atribuye el incidente a un proveedor real ni a Países Bajos.
- Las IPs del archivo de ejemplo pertenecen a TEST-NET-2, según
  [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737).

## Redes y organizaciones

Los nombres y ASNs se contrastaron con la respuesta `holder` del servicio público
[RIPEstat AS Overview](https://stat.ripe.net/docs/data-api/api-endpoints/as-overview)
(`https://stat.ripe.net/data/as-overview/data.json?resource=AS13335`, por ejemplo).
El registro identifica una red; no verifica la presencia de un operador en un edificio
ni la ubicación geográfica de un flujo. Los nombres comerciales se simplifican en la ficha.

Referencias adicionales:

- [ARSAT, AS52361 en PeeringDB](https://www.peeringdb.com/net/4771).
- [SG.GS, AS24482 en PeeringDB](https://www.peeringdb.com/asn/24482): este ASN no se
  utiliza para atribuir SGIX.
- [CABASE](https://www.cabase.org.ar/) e [IX.br](https://ix.br/) para contexto de intercambio local.

Se retiraron asociaciones incorrectas del material inicial: AS62887 no es FL-IX;
AS16467 no es CoreSite; AS15404 no identifica Digital Realty; AS264409 no identifica
Ascenty; AS264663 no identifica Nabiax; AS19626 no identifica el IXP de Los Ángeles.
Cuando no se verificó un ASN aplicable al nodo, se usa `0`. El catálogo también actualiza
la denominación de AS1299 a Arelion.

Las fichas `jurisdiccion` son referencias orientativas sobre el operador. No sustituyen
el análisis del lugar de procesamiento, contratos, residencia del titular y demás leyes
aplicables. Terminar en un nodo argentino no demuestra que el tránsito haya permanecido
dentro del país. Transitar por un IXP tampoco ofrece esa garantía.

## Cables

Se usan nombres de sistemas reales y una selección de ciudades de amarre para el globo.
Las coordenadas están aproximadas a nivel de ciudad: no identifican edificios ni
infraestructura de acceso. Las líneas entre puntos son ilustrativas.

| Sistema | Amarres seleccionados | Referencia |
| --- | --- | --- |
| SAm-1 | Las Toninas, Santos, Boca Ratón | [Submarine Networks](https://www.submarinenetworks.com/en/systems/brazil-us/sam-1) |
| South American Crossing | Las Toninas, Valparaíso, St. Croix | [Submarine Networks](https://submarinenetworks.com/en/systems/brazil-us/sac) |
| Atlantis-2 | Las Toninas, Fortaleza, Carcavelos | [Submarine Networks](https://www.submarinenetworks.com/en/systems/brazil-europe) |
| UNISUR | Las Toninas, Maldonado | [GeoCables](https://geocables.com/cable/unisur) |
| Malbec | Las Toninas, Praia Grande, Río de Janeiro | [Submarine Networks](https://www.submarinenetworks.com/en/systems/brazil-us/malbec) |
| Firmina | Las Toninas, Praia Grande, Myrtle Beach | [Submarine Networks](https://www.submarinenetworks.com/en/systems/brazil-us/firmina) |

La selección no es exhaustiva: por ejemplo Firmina también incluye Punta del Este.
Las Toninas se representa aproximadamente en **-36.47, -56.70**.
UNISUR no se representa como un enlace hacia Valparaíso o Florianópolis.
El catálogo conserva los IDs de Bicentenario, Tannat, Monet, Marea y Curie usados por
Persona B, con un punto representativo; no se afirma haber relevado todos sus amarres.

El campo `organizacion` de un cable identifica una referencia comercial y puede no
enumerar todos los propietarios del consorcio. No se incluyen longitudes ni fechas
de servicio, porque requieren verificación y actualización específicas.

## Topología y cobertura

Los nodos adicionales amplían la cobertura del mapa en América, Europa, Asia y África.
No todos son elegibles para generar tráfico: eso lo decide `mezcla_destinos.json`.
Los puntos oceánicos son representativos; no usar sus coordenadas como trayecto físico.
Las nubes se colocan por ciudad/región de referencia, sin inferir la ubicación de
usuarios de servicios anycast.

El trazador del backend aproxima regiones y usa Europa como fallback para países sin
entrada propia. Por eso una ruta generada hacia África u Oceanía puede usar ese patrón.
`via` permite desvíos pedagógicos que no constituyen rutas BGP verificadas.
Un enlace dibujado no prueba que exista una relación de peering entre los dos nodos.

## Antecedente para el pitch

[Cloudflare: How a Nigerian ISP Accidentally Knocked Google Offline](https://blog.cloudflare.com/how-a-nigerian-isp-knocked-google-offline/)
describe el incidente del 12 de noviembre de 2018, de 74 minutos.
Se cita como ejemplo de una fuga accidental de rutas y su impacto, sin atribuir intención
maliciosa. TRACE no reproduce ese incidente ni demuestra haberlo detectado.
