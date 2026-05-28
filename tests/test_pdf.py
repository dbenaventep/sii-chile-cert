"""Tests de siicl.pdf."""
import pytest

from siicl.caf import CAF
from siicl.dte import DTE, Emisor, Item, Receptor, Referencia, dte_a_xml
from siicl.pdf import datos_desde_dte_xml, render_html, render_pdf
from siicl.timbre import DatosTED, construir_ted


def _crear_dte_y_ted(caf_xml, tipo: int = 39, folio: int = 1):
    """Helper: genera un DTE simple y su TED para tests de PDF."""
    caf = CAF.from_bytes(caf_xml)
    if tipo == 39:
        receptor = Receptor(rut="66666666-6", razon_social="Sin RUT",
                            direccion="Santiago", comuna="Santiago")
    else:
        receptor = Receptor(rut="77234567-4", razon_social="CLIENTE DEMO LTDA",
                            giro="GIRO DEMO", direccion="Cliente 456",
                            comuna="Providencia", ciudad="Santiago")
    emisor = Emisor(
        rut="76123456-0", razon_social="EMPRESA DEMO SPA",
        giro="SERVICIOS DEMO", direccion="CALLE DEMO 123",
        comuna="PROVIDENCIA", ciudad="SANTIAGO", actecos=[123456],
    )
    items = [Item("Producto Demo", 1, 11900)]
    refs = [Referencia(razon="CASO-1", codigo_referencia="SET")] if tipo == 39 else []

    dte = DTE(
        tipo=tipo, folio=folio, fecha_emision="2026-04-29",
        emisor=emisor, receptor=receptor, items=items, referencias=refs,
    )
    dte_xml = dte_a_xml(dte)

    datos_ted = DatosTED(
        rut_emisor=emisor.rut, tipo_dte=tipo, folio=folio,
        fecha_emision="2026-04-29",
        rut_receptor=receptor.rut, razon_social_receptor=receptor.razon_social,
        monto_total=11900, nombre_item_1="Producto Demo",
    )
    ted = construir_ted(datos_ted, caf)

    return dte_xml, ted


class TestDatosDesdeDTEXml:
    def test_extrae_datos_boleta(self, caf_demo_xml):
        dte_xml, ted = _crear_dte_y_ted(caf_demo_xml, tipo=39)
        # Usar security_level=3 porque CAF demo tiene RSA 1024 (más largo que real)
        datos = datos_desde_dte_xml(dte_xml, ted, pdf417_security_level=3)
        assert datos.tipo_dte == 39
        assert datos.folio == 1
        assert datos.rut_emisor == "76123456-0"
        assert datos.razon_social_emisor == "EMPRESA DEMO SPA"
        assert datos.razon_social_receptor == "Sin RUT"
        assert datos.monto_total == 11900
        assert datos.barcode_data_uri.startswith("data:image/png;base64,")
        assert len(datos.items) == 1
        assert datos.items[0]["nombre"] == "Producto Demo"
        assert len(datos.referencias) == 1
        assert datos.referencias[0]["razon"] == "CASO-1"
        # Boletas NO llevan cedible aunque se pida
        assert datos.cedible is False

    def test_extrae_datos_factura_cedible(self, caf_demo_xml):
        # Necesitamos un CAF de tipo 33 para esto. Reusamos el de 39 pero
        # parchando el tipo en memoria (solo para extraer datos, no construir_ted)
        from siicl.dte import dte_a_xml
        emisor = Emisor(rut="76123456-0", razon_social="EMPRESA DEMO SPA",
                        giro="SERVICIOS DEMO", direccion="CALLE DEMO 123",
                        comuna="PROVIDENCIA", ciudad="SANTIAGO", actecos=[123456])
        receptor = Receptor(rut="77234567-4", razon_social="CLIENTE DEMO LTDA",
                            giro="GIRO DEMO", direccion="Cliente 456",
                            comuna="Providencia", ciudad="Santiago")
        dte = DTE(tipo=33, folio=1, fecha_emision="2026-04-29",
                  emisor=emisor, receptor=receptor, items=[Item("X", 1, 10000)])
        dte_xml = dte_a_xml(dte)

        # Reusar TED del CAF demo (no nos importa que TED sea de tipo 39, solo
        # validamos extracción de datos del DTE)
        caf = CAF.from_bytes(caf_demo_xml)
        ted = construir_ted(DatosTED(
            rut_emisor="76123456-0", tipo_dte=39, folio=1,
            fecha_emision="2026-04-29", rut_receptor="77234567-4",
            razon_social_receptor="CLIENTE DEMO LTDA",
            monto_total=11900, nombre_item_1="X",
        ), caf)

        datos = datos_desde_dte_xml(dte_xml, ted, cedible=True,
                                    pdf417_security_level=3)
        assert datos.tipo_dte == 33
        # Factura SÍ acepta cedible
        assert datos.cedible is True


class TestRenderHTML:
    def test_render_boleta(self, caf_demo_xml):
        dte_xml, ted = _crear_dte_y_ted(caf_demo_xml, tipo=39)
        datos = datos_desde_dte_xml(dte_xml, ted, pdf417_security_level=3)
        html = render_html(datos)
        assert "<html" in html
        assert "BOLETA ELECTRONICA" in html
        assert "76123456-0" in html
        assert "Producto Demo" in html
        assert "11.900" in html  # formato CLP con separador de miles
        assert "data:image/png;base64," in html


class TestRenderPDF:
    def test_render_pdf_basico(self, caf_demo_xml):
        dte_xml, ted = _crear_dte_y_ted(caf_demo_xml, tipo=39)
        datos = datos_desde_dte_xml(dte_xml, ted, pdf417_security_level=3)
        pdf = render_pdf(datos)
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 5000
