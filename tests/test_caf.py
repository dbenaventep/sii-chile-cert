"""Tests de siicl.caf."""
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from siicl.caf import CAF


class TestCAF:
    def test_parse_basico(self, caf_demo_xml):
        caf = CAF.from_bytes(caf_demo_xml)
        assert caf.rut_emisor == "76123456-0"
        assert caf.razon_social == "EMPRESA DEMO SPA"
        assert caf.tipo_dte == 39
        assert caf.folio_inicial == 1
        assert caf.folio_final == 50
        assert caf.fecha_autorizacion == "2026-01-01"
        assert caf.idk == 100

    def test_cubre_folio(self, caf_demo_xml):
        caf = CAF.from_bytes(caf_demo_xml)
        assert caf.cubre_folio(1)
        assert caf.cubre_folio(25)
        assert caf.cubre_folio(50)
        assert not caf.cubre_folio(0)
        assert not caf.cubre_folio(51)
        assert not caf.cubre_folio(100)

    def test_cargar_clave_privada(self, caf_demo_xml):
        caf = CAF.from_bytes(caf_demo_xml)
        key = caf.cargar_clave_privada()
        assert isinstance(key, rsa.RSAPrivateKey)

    def test_caf_xml_b64(self, caf_demo_xml):
        import base64

        caf = CAF.from_bytes(caf_demo_xml)
        b64 = caf.caf_xml_b64()
        # Roundtrip
        assert base64.b64decode(b64) == caf_demo_xml

    def test_xml_sin_da_falla(self):
        bad_xml = b'<?xml version="1.0"?><AUTORIZACION><CAF version="1.0"></CAF></AUTORIZACION>'
        with pytest.raises(ValueError, match="falta elemento <DA>"):
            CAF.from_bytes(bad_xml)

    def test_xml_sin_caf_falla(self):
        bad_xml = b'<?xml version="1.0"?><AUTORIZACION></AUTORIZACION>'
        with pytest.raises(ValueError, match="falta elemento <CAF>"):
            CAF.from_bytes(bad_xml)
