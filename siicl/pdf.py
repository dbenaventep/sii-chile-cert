"""Renderizado de DTE/Boleta a PDF con timbre PDF417.

Genera 1 o 2 PDFs por DTE (tributario y cedible) usando Jinja2 + WeasyPrint.

Reglas críticas (ver docs/05-documentos-impresos.md):
- PDF417 incrustado como PNG raster base64 (NO SVG)
- Recuadro SII en rojo (RUT, tipo doc, folio) en esquina superior derecha
- Para T33/T34/T46: leyenda "CEDIBLE" en cedible
- Para T52: leyenda "CEDIBLE CON SU FACTURA"
- Boletas T39/T41: NO llevan cedible ni acuse de recibo
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from lxml import etree

from siicl.timbre import pdf417_png_b64_data_uri, ted_to_pdf417_png
from siicl.types import es_boleta

NS_SII = "http://www.sii.cl/SiiDte"
TEMPLATES_DIR = Path(__file__).parent / "templates"


TIPO_DTE_PALABRAS = {
    33: "FACTURA ELECTRONICA",
    34: "FACTURA NO AFECTA O EXENTA ELECTRONICA",
    39: "BOLETA ELECTRONICA",
    41: "BOLETA EXENTA ELECTRONICA",
    43: "LIQUIDACION FACTURA ELECTRONICA",
    46: "FACTURA DE COMPRA ELECTRONICA",
    52: "GUIA DE DESPACHO ELECTRONICA",
    56: "NOTA DE DEBITO ELECTRONICA",
    61: "NOTA DE CREDITO ELECTRONICA",
}


@dataclass
class DatosPDF:
    """Datos para renderizar el PDF de un DTE.

    Atributos derivados del XML del DTE + metadatos adicionales:
    - unidad_sii: ej "SANTIAGO ORIENTE" (de la resolución SII)
    - url_verificacion: URL para verificar el DTE en sii.cl
    - cedible: True para imprimir versión cedible (con acuse)
    """

    tipo_dte: int
    folio: int
    fecha_emision: str
    rut_emisor: str
    razon_social_emisor: str
    giro_emisor: str
    direccion_emisor: str
    comuna_emisor: str
    ciudad_emisor: str
    rut_receptor: str
    razon_social_receptor: str
    giro_receptor: str
    direccion_receptor: str
    comuna_receptor: str
    ciudad_receptor: str
    items: list[dict]
    monto_neto: int
    monto_exento: int
    monto_iva: int
    monto_total: int
    referencias: list[dict]
    barcode_data_uri: str
    unidad_sii: str = "SANTIAGO"
    url_verificacion: str = "https://www.sii.cl"
    cedible: bool = False


def _findtext_ns(elem, path: str) -> str:
    """Helper para encontrar texto en un path con namespace SII."""
    ns_path = path.replace("/", f"/{{{NS_SII}}}").lstrip(f"{{{NS_SII}}}")
    if not path.startswith("/"):
        ns_path = f"{{{NS_SII}}}{ns_path}"
    return elem.findtext(ns_path) or ""


def datos_desde_dte_xml(
    dte_xml: bytes,
    ted_bytes: bytes,
    *,
    cedible: bool = False,
    unidad_sii: str = "SANTIAGO",
    url_verificacion: str = "https://www.sii.cl",
    pdf417_security_level: int = 5,
) -> DatosPDF:
    """Extrae datos del XML del DTE firmado para renderizar PDF.

    Args:
        dte_xml: bytes del <DTE> firmado.
        ted_bytes: bytes del TED (para generar el PDF417).
        cedible: si True, marca como versión cedible.
        pdf417_security_level: nivel 0-8. SII recomienda 5 para CAFs reales.
    """
    root = etree.fromstring(dte_xml)
    doc = root.find(f"{{{NS_SII}}}Documento")
    enc = doc.find(f"{{{NS_SII}}}Encabezado")
    iddoc = enc.find(f"{{{NS_SII}}}IdDoc")
    emi = enc.find(f"{{{NS_SII}}}Emisor")
    rec = enc.find(f"{{{NS_SII}}}Receptor")
    tot = enc.find(f"{{{NS_SII}}}Totales")
    detalles = doc.findall(f"{{{NS_SII}}}Detalle")
    refs = doc.findall(f"{{{NS_SII}}}Referencia")

    tipo = int(iddoc.findtext(f"{{{NS_SII}}}TipoDTE"))
    boleta = es_boleta(tipo)

    items = []
    for det in detalles:
        items.append({
            "linea": int(det.findtext(f"{{{NS_SII}}}NroLinDet", "0")),
            "codigo": det.findtext(f"{{{NS_SII}}}CdgItem/{{{NS_SII}}}VlrCodigo", ""),
            "nombre": det.findtext(f"{{{NS_SII}}}NmbItem", ""),
            "cantidad": float(det.findtext(f"{{{NS_SII}}}QtyItem", "0")),
            "unidad": det.findtext(f"{{{NS_SII}}}UnmdItem", ""),
            "precio": float(det.findtext(f"{{{NS_SII}}}PrcItem", "0")),
            "monto": int(det.findtext(f"{{{NS_SII}}}MontoItem", "0")),
            "exento": det.find(f"{{{NS_SII}}}IndExe") is not None,
        })

    referencias = []
    for r in refs:
        referencias.append({
            "linea": int(r.findtext(f"{{{NS_SII}}}NroLinRef", "0")),
            "tipo_doc": r.findtext(f"{{{NS_SII}}}TpoDocRef", ""),
            "folio": r.findtext(f"{{{NS_SII}}}FolioRef", ""),
            "fecha": r.findtext(f"{{{NS_SII}}}FchRef", ""),
            "codigo": r.findtext(f"{{{NS_SII}}}CodRef", ""),
            "razon": r.findtext(f"{{{NS_SII}}}RazonRef", ""),
        })

    # Generar PDF417 desde el TED
    # Para CAFs sintéticos con RSA grande, security_level menor evita "data too long"
    png = ted_to_pdf417_png(ted_bytes, security_level=pdf417_security_level)
    barcode_data_uri = pdf417_png_b64_data_uri(png)

    # Tags Emisor distintos en boletas
    if boleta:
        rzn = emi.findtext(f"{{{NS_SII}}}RznSocEmisor", "")
        giro = emi.findtext(f"{{{NS_SII}}}GiroEmisor", "")
    else:
        rzn = emi.findtext(f"{{{NS_SII}}}RznSoc", "")
        giro = emi.findtext(f"{{{NS_SII}}}GiroEmis", "")

    return DatosPDF(
        tipo_dte=tipo,
        folio=int(iddoc.findtext(f"{{{NS_SII}}}Folio", "0")),
        fecha_emision=iddoc.findtext(f"{{{NS_SII}}}FchEmis", ""),
        rut_emisor=emi.findtext(f"{{{NS_SII}}}RUTEmisor", ""),
        razon_social_emisor=rzn,
        giro_emisor=giro,
        direccion_emisor=emi.findtext(f"{{{NS_SII}}}DirOrigen", ""),
        comuna_emisor=emi.findtext(f"{{{NS_SII}}}CmnaOrigen", ""),
        ciudad_emisor=emi.findtext(f"{{{NS_SII}}}CiudadOrigen", ""),
        rut_receptor=rec.findtext(f"{{{NS_SII}}}RUTRecep", ""),
        razon_social_receptor=rec.findtext(f"{{{NS_SII}}}RznSocRecep", ""),
        giro_receptor=rec.findtext(f"{{{NS_SII}}}GiroRecep", ""),
        direccion_receptor=rec.findtext(f"{{{NS_SII}}}DirRecep", ""),
        comuna_receptor=rec.findtext(f"{{{NS_SII}}}CmnaRecep", ""),
        ciudad_receptor=rec.findtext(f"{{{NS_SII}}}CiudadRecep", ""),
        items=items,
        monto_neto=int(tot.findtext(f"{{{NS_SII}}}MntNeto", "0")),
        monto_exento=int(tot.findtext(f"{{{NS_SII}}}MntExe", "0")),
        monto_iva=int(tot.findtext(f"{{{NS_SII}}}IVA", "0")),
        monto_total=int(tot.findtext(f"{{{NS_SII}}}MntTotal", "0")),
        referencias=referencias,
        barcode_data_uri=barcode_data_uri,
        unidad_sii=unidad_sii,
        url_verificacion=url_verificacion,
        cedible=cedible and not boleta,  # boletas no llevan cedible
    )


def _clp(valor) -> str:
    """Formatea entero como CLP con separadores de miles."""
    return f"{int(valor):,}".replace(",", ".")


def _tipo_palabras(tipo: int) -> str:
    return TIPO_DTE_PALABRAS.get(tipo, f"DTE TIPO {tipo}")


def _leyenda_cedible(tipo: int) -> str:
    """T52 lleva 'CEDIBLE CON SU FACTURA', otros solo 'CEDIBLE'."""
    if tipo == 52:
        return "CEDIBLE CON SU FACTURA"
    return "CEDIBLE"


def render_pdf(datos: DatosPDF, template_name: str = "dte.html") -> bytes:
    """Renderiza el DTE como PDF. Requiere WeasyPrint instalado."""
    from weasyprint import HTML

    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["clp"] = _clp
    env.filters["tipo_palabras"] = _tipo_palabras
    env.filters["leyenda_cedible"] = _leyenda_cedible

    template = env.get_template(template_name)
    html_str = template.render(d=datos)

    pdf_bytes = HTML(string=html_str, base_url=str(TEMPLATES_DIR)).write_pdf()
    return pdf_bytes


def render_html(datos: DatosPDF, template_name: str = "dte.html") -> str:
    """Versión que retorna HTML (útil para debug del template sin generar PDF)."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["clp"] = _clp
    env.filters["tipo_palabras"] = _tipo_palabras
    env.filters["leyenda_cedible"] = _leyenda_cedible

    template = env.get_template(template_name)
    return template.render(d=datos)
