"""Tests de siicl.firma."""
import base64

import pytest
from lxml import etree

from siicl.firma import NS_DS, Cert, calcular_digest, canonicalize, firmar_xml


class TestCert:
    def test_cargar_desde_bytes(self, pfx_demo):
        cert = Cert.from_pfx_bytes(pfx_demo["pfx_bytes"], pfx_demo["password"])
        assert cert.private_key is not None
        assert cert.certificate is not None

    def test_password_incorrecto(self, pfx_demo):
        with pytest.raises(ValueError):
            Cert.from_pfx_bytes(pfx_demo["pfx_bytes"], "password_incorrecto")

    def test_propiedades_publicas_b64(self, pfx_demo):
        cert = Cert.from_pfx_bytes(pfx_demo["pfx_bytes"], pfx_demo["password"])
        # base64 válido y razonable
        assert len(cert.public_key_modulus_b64) > 100  # 2048 bits
        assert len(cert.public_key_exponent_b64) > 0
        assert len(cert.cert_der_b64) > 500
        # Decodifica sin error
        base64.b64decode(cert.public_key_modulus_b64)
        base64.b64decode(cert.cert_der_b64)

    def test_firmar_bytes(self, pfx_demo):
        cert = Cert.from_pfx_bytes(pfx_demo["pfx_bytes"], pfx_demo["password"])
        firma = cert.firmar_bytes(b"datos a firmar")
        assert isinstance(firma, bytes)
        assert len(firma) == 256  # 2048 bits / 8

    def test_firmar_bytes_b64(self, pfx_demo):
        cert = Cert.from_pfx_bytes(pfx_demo["pfx_bytes"], pfx_demo["password"])
        b64 = cert.firmar_bytes_b64(b"datos")
        # Decodifica OK
        decoded = base64.b64decode(b64)
        assert len(decoded) == 256


class TestCanonicalize:
    def test_canonicalize_basico(self):
        # c14n requiere un documento parseado completo (no un Element suelto)
        tree = etree.ElementTree(etree.fromstring(b'<root><a>1</a></root>'))
        elem = tree.getroot()
        canon = canonicalize(elem)
        assert b'<root>' in canon
        assert b'<a>1</a>' in canon

    def test_canonicalize_estable(self):
        """Canonicalización determinística: 2 llamadas → mismo output."""
        tree = etree.ElementTree(etree.fromstring(b'<root><a>1</a><b>2</b></root>'))
        elem = tree.getroot()
        assert canonicalize(elem) == canonicalize(elem)


class TestDigest:
    def test_digest_basico(self):
        elem = etree.fromstring('<root><a>1</a></root>')
        digest = calcular_digest(elem)
        # SHA-1 base64 tiene 28 caracteres (20 bytes → 28 b64 chars)
        assert len(digest) == 28
        # Decodifica OK
        decoded = base64.b64decode(digest)
        assert len(decoded) == 20


class TestFirmarXml:
    def test_firma_envelope_basica(self, pfx_demo):
        cert = Cert.from_pfx_bytes(pfx_demo["pfx_bytes"], pfx_demo["password"])
        xml_input = '<doc><contenido>hola</contenido></doc>'
        firmado = firmar_xml(xml_input, cert)

        root = etree.fromstring(firmado.encode("ISO-8859-1"))
        # Tiene Signature como hijo
        sig = root.find(f"{{{NS_DS}}}Signature")
        assert sig is not None
        # SignedInfo presente
        signed_info = sig.find(f"{{{NS_DS}}}SignedInfo")
        assert signed_info is not None
        # DigestValue presente
        digest_value = signed_info.findall(f"{{{NS_DS}}}Reference")[0].find(
            f"{{{NS_DS}}}DigestValue"
        )
        assert digest_value is not None and digest_value.text
        # SignatureValue presente
        sig_value = sig.find(f"{{{NS_DS}}}SignatureValue")
        assert sig_value is not None and sig_value.text
        # X509Certificate presente
        x509 = sig.find(f"{{{NS_DS}}}KeyInfo/{{{NS_DS}}}X509Data/{{{NS_DS}}}X509Certificate")
        assert x509 is not None and x509.text

    def test_firma_con_id_referencia(self, pfx_demo):
        cert = Cert.from_pfx_bytes(pfx_demo["pfx_bytes"], pfx_demo["password"])
        xml_input = '<envelope><payload ID="data">contenido</payload></envelope>'
        firmado = firmar_xml(xml_input, cert, reference_uri="#data")

        root = etree.fromstring(firmado.encode("ISO-8859-1"))
        ref = root.find(f"{{{NS_DS}}}Signature/{{{NS_DS}}}SignedInfo/{{{NS_DS}}}Reference")
        assert ref.get("URI") == "#data"

    def test_firma_id_inexistente_falla(self, pfx_demo):
        cert = Cert.from_pfx_bytes(pfx_demo["pfx_bytes"], pfx_demo["password"])
        with pytest.raises(ValueError, match="ID=noexiste"):
            firmar_xml('<doc/>', cert, reference_uri="#noexiste")
