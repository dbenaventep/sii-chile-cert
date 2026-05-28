"""Tests de siicl.timbre."""
import pytest
from lxml import etree

from siicl.caf import CAF
from siicl.timbre import (
    DatosTED,
    construir_ted,
    pdf417_png_b64_data_uri,
    ted_to_pdf417_png,
)


def _datos_demo(folio: int = 1, tipo: int = 39) -> DatosTED:
    return DatosTED(
        rut_emisor="76123456-0",
        tipo_dte=tipo,
        folio=folio,
        fecha_emision="2026-04-29",
        rut_receptor="66666666-6",
        razon_social_receptor="Sin RUT",
        monto_total=29800,
        nombre_item_1="Producto Demo",
    )


class TestConstruirTED:
    def test_basico(self, caf_demo_xml):
        caf = CAF.from_bytes(caf_demo_xml)
        ted = construir_ted(_datos_demo(), caf)
        assert ted.startswith(b'<TED version="1.0">')
        assert ted.endswith(b'</TED>')
        # Tiene los elementos clave
        assert b'<RE>76123456-0</RE>' in ted
        assert b'<TD>39</TD>' in ted
        assert b'<F>1</F>' in ted
        assert b'<MNT>29800</MNT>' in ted
        assert b'<FRMT algoritmo="SHA1withRSA">' in ted

    def test_parseable_como_xml(self, caf_demo_xml):
        caf = CAF.from_bytes(caf_demo_xml)
        ted = construir_ted(_datos_demo(), caf)
        # Debe ser XML válido
        root = etree.fromstring(ted)
        assert root.tag == "TED"
        assert root.get("version") == "1.0"
        # Estructura
        dd = root.find("DD")
        assert dd is not None
        assert dd.find("RE").text == "76123456-0"
        assert dd.find("TD").text == "39"
        assert dd.find("CAF") is not None
        frmt = root.find("FRMT")
        assert frmt is not None
        assert frmt.get("algoritmo") == "SHA1withRSA"
        assert len(frmt.text) > 50  # base64 de firma RSA

    def test_folio_fuera_de_rango_falla(self, caf_demo_xml):
        caf = CAF.from_bytes(caf_demo_xml)  # rango 1-50
        with pytest.raises(ValueError, match="fuera del rango"):
            construir_ted(_datos_demo(folio=51), caf)
        with pytest.raises(ValueError, match="fuera del rango"):
            construir_ted(_datos_demo(folio=0), caf)

    def test_rut_distinto_falla(self, caf_demo_xml):
        caf = CAF.from_bytes(caf_demo_xml)  # CAF para 76123456-0
        datos = _datos_demo()
        datos.rut_emisor = "77234567-4"
        with pytest.raises(ValueError, match="RUT emisor del CAF"):
            construir_ted(datos, caf)

    def test_tipo_dte_distinto_falla(self, caf_demo_xml):
        caf = CAF.from_bytes(caf_demo_xml)  # CAF para tipo 39
        with pytest.raises(ValueError, match="Tipo DTE del CAF"):
            construir_ted(_datos_demo(tipo=33), caf)

    def test_truncar_strings_largos(self, caf_demo_xml):
        caf = CAF.from_bytes(caf_demo_xml)
        datos = _datos_demo()
        datos.razon_social_receptor = "X" * 100  # se trunca a 40
        datos.nombre_item_1 = "Y" * 100
        ted = construir_ted(datos, caf)
        root = etree.fromstring(ted)
        assert len(root.find("DD/RSR").text) == 40
        assert len(root.find("DD/IT1").text) == 40


class TestPDF417:
    # CAF demo tiene RSA 1024 (cryptography no permite 512 que es el real del SII).
    # El TED demo resulta ~200 bytes más largo que real → bajamos security_level
    # solo para el test. En producción con CAF real (RSA 512) usar security_level=5.
    SECLEVEL_TEST = 3

    def test_genera_png(self, caf_demo_xml):
        caf = CAF.from_bytes(caf_demo_xml)
        ted = construir_ted(_datos_demo(), caf)
        png = ted_to_pdf417_png(ted, security_level=self.SECLEVEL_TEST)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"  # magic bytes PNG
        assert len(png) > 1000  # PNG razonable

    def test_data_uri(self, caf_demo_xml):
        caf = CAF.from_bytes(caf_demo_xml)
        ted = construir_ted(_datos_demo(), caf)
        png = ted_to_pdf417_png(ted, security_level=self.SECLEVEL_TEST)
        uri = pdf417_png_b64_data_uri(png)
        assert uri.startswith("data:image/png;base64,")
        assert len(uri) > 1000
