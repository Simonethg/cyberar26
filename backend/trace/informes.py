"""Informe del turno en PDF, generado a mano para no sumar dependencias ni salir a internet."""

from __future__ import annotations

from .esquemas import Alerta, DestinoTop, MetricasGlobal

ANCHO, ALTO = 595, 842  # A4 en puntos
MARGEN = 50
INTERLINEA = 15
LINEAS_POR_PAGINA = (ALTO - 2 * MARGEN) // INTERLINEA


def _escapar(texto: str) -> bytes:
    crudo = texto.encode("cp1252", errors="replace")
    return crudo.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _cortar(texto: str, ancho: int = 95) -> list[str]:
    palabras, lineas, actual = texto.split(), [], ""
    for palabra in palabras:
        if len(actual) + len(palabra) + 1 > ancho:
            lineas.append(actual)
            actual = palabra
        else:
            actual = f"{actual} {palabra}".strip()
    if actual:
        lineas.append(actual)
    return lineas or [""]


def _formatear_bytes(cantidad: float) -> str:
    for unidad, divisor in (("GB", 1e9), ("MB", 1e6), ("KB", 1e3)):
        if cantidad >= divisor:
            return f"{cantidad / divisor:.1f} {unidad}"
    return f"{int(cantidad)} B"


def _lineas_del_informe(generado: str, metricas: MetricasGlobal, destinos: list[DestinoTop],
                        alertas: list[Alerta], resumen: str) -> list[tuple[str, bool]]:
    """Devuelve (texto, es_titulo) por línea."""
    lineas: list[tuple[str, bool]] = [
        ("TRACE — Informe del turno", True),
        ("Mira adonde van tus datos · Base Aerea El Chanar · trafico simulado", False),
        (f"Generado: {generado}", False),
        ("", False),
        ("Resumen de trafico", True),
        (f"Bajada: {metricas.mbps_bajada} Mbps · Subida: {metricas.mbps_subida} Mbps", False),
        (f"Flujos activos: {metricas.flujos_activos} · "
         f"Destinos distintos: {metricas.destinos}", False),
        (f"Trafico cifrado: {metricas.porcentaje_cifrado} % · "
         f"Alertas abiertas: {metricas.alertas_abiertas}", False),
        ("", False),
        ("Destinos principales", True),
    ]
    for destino in destinos:
        lineas.append(
            (f"  {destino.organizacion} (AS{destino.asn}) — {_formatear_bytes(destino.valor)} "
             f"({destino.porcentaje} %)", False)
        )
    lineas += [("", False), ("Alertas del turno", True)]
    if not alertas:
        lineas.append(("  Sin alertas en el turno.", False))
    for alerta in alertas:
        lineas.append((f"  [{alerta.severidad.upper()}] {alerta.ts[11:19]} · {alerta.titulo} · "
                       f"{alerta.dispositivo_id} · {alerta.estado}", False))
        for linea in _cortar(alerta.explicacion, 90):
            lineas.append((f"      {linea}", False))
        if alerta.accion_sugerida:
            for linea in _cortar(f"Accion: {alerta.accion_sugerida}", 90):
                lineas.append((f"      {linea}", False))
    lineas += [("", False), ("Resumen del asistente", True)]
    lineas += [(f"  {linea}", False) for linea in _cortar(resumen, 90)]
    return lineas


def informe_pdf(generado: str, metricas: MetricasGlobal, destinos: list[DestinoTop],
                alertas: list[Alerta], resumen: str) -> bytes:
    lineas = _lineas_del_informe(generado, metricas, destinos, alertas, resumen)
    paginas = [lineas[i:i + LINEAS_POR_PAGINA] for i in range(0, len(lineas), LINEAS_POR_PAGINA)] \
        or [[("Sin datos", False)]]

    objetos: list[bytes] = []
    ids_paginas = [4 + 2 * i for i in range(len(paginas))]

    objetos.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{i} 0 R" for i in ids_paginas)
    objetos.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(paginas)} >>".encode())
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                   b"/Encoding /WinAnsiEncoding >>")

    for indice, pagina in enumerate(paginas):
        contenido = bytearray(b"BT\n")
        y = ALTO - MARGEN
        for texto, es_titulo in pagina:
            fuente = b"/F1 13 Tf" if es_titulo else b"/F1 10 Tf"
            contenido += b"1 0 0 1 %d %d Tm %s (" % (MARGEN, y, fuente)
            contenido += _escapar(texto)
            contenido += b") Tj\n"
            y -= INTERLINEA
        contenido += b"ET"
        objetos.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {ANCHO} {ALTO}] "
            f"/Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {ids_paginas[indice] + 1} 0 R >>".encode()
        )
        objetos.append(b"<< /Length %d >>\nstream\n%s\nendstream"
                       % (len(contenido), bytes(contenido)))

    salida = bytearray(b"%PDF-1.4\n")
    posiciones = []
    for numero, cuerpo in enumerate(objetos, start=1):
        posiciones.append(len(salida))
        salida += b"%d 0 obj\n" % numero + cuerpo + b"\nendobj\n"

    inicio_xref = len(salida)
    salida += b"xref\n0 %d\n" % (len(objetos) + 1)
    salida += b"0000000000 65535 f \n"
    for posicion in posiciones:
        salida += b"%010d 00000 n \n" % posicion
    salida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objetos) + 1, inicio_xref
    )
    return bytes(salida)
