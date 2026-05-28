"""Generación del Timbre Electrónico DTE (TED) y código de barras PDF417.

El TED es un XML con los datos básicos del DTE más el CAF y firma RSA del
contribuyente. Se imprime como PDF417 en la representación impresa del DTE.

Reglas críticas del PDF417 según SII:
- Encoding ISO-8859-1 (NO UTF-8). Si se codifica UTF-8 caracteres como Ñ/Ó
  cambian de bytes y la firma falla al escanear.
- security_level=5 (máximo, exigido por el manual).
- numeric_compaction=False (forzar byte compaction para preservar bytes).
- Render como PNG raster (NO SVG, pierde resolución en HTML→PDF).
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from datetime import datetime

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree

from siicl.caf import CAF


@dataclass
class DatosTED:
    """Datos mínimos para construir un TED.

    Atributos:
        rut_emisor: NNNNNNNN-D
        tipo_dte: 33, 39, 52, etc.
        folio: número de folio del DTE
        fecha_emision: AAAA-MM-DD
        rut_receptor: NNNNNNNN-D
        razon_social_receptor: maxLength 40 (el TED trunca a 40 chars)
        monto_total: monto total del DTE en pesos enteros
        nombre_item_1: primer item del Detalle, maxLength 40
    """

    rut_emisor: str
    tipo_dte: int
    folio: int
    fecha_emision: str
    rut_receptor: str
    razon_social_receptor: str
    monto_total: int
    nombre_item_1: str


def construir_ted(datos: DatosTED, caf: CAF) -> bytes:
    """Construye el TED firmado con la clave privada del CAF.

    Retorna el TED como bytes en ISO-8859-1, listo para incrustar en el DTE.
    """
    if not caf.cubre_folio(datos.folio):
        raise ValueError(
            f"Folio {datos.folio} fuera del rango del CAF "
            f"({caf.folio_inicial}-{caf.folio_final})"
        )
    if caf.rut_emisor != datos.rut_emisor:
        raise ValueError(
            f"RUT emisor del CAF ({caf.rut_emisor}) no coincide con el del DTE "
            f"({datos.rut_emisor})"
        )
    if caf.tipo_dte != datos.tipo_dte:
        raise ValueError(
            f"Tipo DTE del CAF ({caf.tipo_dte}) no coincide con el del DTE "
            f"({datos.tipo_dte})"
        )

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    rsr = (datos.razon_social_receptor or "")[:40]
    it1 = (datos.nombre_item_1 or "")[:40]

    # Construir <DD> en ISO-8859-1 sin canonicalización extra.
    # El orden de los elementos es estricto (RE, TD, F, FE, RR, RSR, MNT, IT1, CAF, TSTED).
    # El CAF se incrusta tal cual viene en el archivo (preservar bytes).
    caf_inner = _extract_caf_element(caf.raw_xml)

    dd_xml = (
        b"<DD>"
        b"<RE>" + datos.rut_emisor.encode("ISO-8859-1") + b"</RE>"
        b"<TD>" + str(datos.tipo_dte).encode("ascii") + b"</TD>"
        b"<F>" + str(datos.folio).encode("ascii") + b"</F>"
        b"<FE>" + datos.fecha_emision.encode("ascii") + b"</FE>"
        b"<RR>" + datos.rut_receptor.encode("ISO-8859-1") + b"</RR>"
        b"<RSR>" + rsr.encode("ISO-8859-1") + b"</RSR>"
        b"<MNT>" + str(datos.monto_total).encode("ascii") + b"</MNT>"
        b"<IT1>" + it1.encode("ISO-8859-1") + b"</IT1>"
        + caf_inner
        + b"<TSTED>" + timestamp.encode("ascii") + b"</TSTED>"
        b"</DD>"
    )

    # Firma SHA1withRSA del <DD> usando clave privada del CAF
    private_key = caf.cargar_clave_privada()
    signature = private_key.sign(dd_xml, padding.PKCS1v15(), hashes.SHA1())
    frmt_b64 = base64.b64encode(signature).decode("ascii")

    ted = (
        b'<TED version="1.0">'
        + dd_xml
        + b'<FRMT algoritmo="SHA1withRSA">' + frmt_b64.encode("ascii") + b'</FRMT>'
        b'</TED>'
    )
    return ted


def _extract_caf_element(caf_raw: bytes) -> bytes:
    """Extrae el elemento <CAF>...</CAF> completo del XML CAF en sus bytes originales."""
    root = etree.fromstring(caf_raw)
    caf_elem = root.find("CAF")
    if caf_elem is None:
        raise ValueError("XML del CAF no tiene elemento <CAF>")
    return etree.tostring(caf_elem)


def ted_to_pdf417_png(
    ted_bytes: bytes,
    *,
    columns: int = 14,
    security_level: int = 5,
    scale: int = 4,
    ratio: int = 3,
    padding: int = 10,
) -> bytes:
    """Codifica el TED como código de barras PDF417 y retorna PNG en bytes.

    Args:
        ted_bytes: el TED en ISO-8859-1 (tal cual sale de construir_ted).
        columns: número de columnas del PDF417 (default 14, recomendación SII).
        security_level: 0-8, default 5 (máximo recomendado por SII).
        scale: factor de escala del raster.
        ratio: relación alto/ancho de cada módulo.
        padding: espacio en blanco alrededor.

    Returns:
        Bytes del PNG.
    """
    from pdf417 import encode, render_image

    # CRÍTICO: codificar como string en ISO-8859-1 NO UTF-8.
    # La librería pdf417 acepta strings, así que decodificamos los bytes a ISO-8859-1
    # y luego le decimos que use ese encoding.
    ted_str = ted_bytes.decode("ISO-8859-1")

    codes = encode(
        ted_str,
        columns=columns,
        security_level=security_level,
        encoding="ISO-8859-1",
        numeric_compaction=False,
    )
    img = render_image(codes, scale=scale, ratio=ratio, padding=padding)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def pdf417_png_b64_data_uri(png_bytes: bytes) -> str:
    """Convierte PNG en data URI base64 para incrustar en HTML."""
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"
