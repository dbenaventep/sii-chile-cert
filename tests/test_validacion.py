"""Tests de siicl.validacion."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from siicl.validacion import descargar_xsds, validar_xml, validar_xml_str


# Mini XSD para test sin red
MINI_XSD = b"""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="hijo" type="xs:string"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>"""


class TestValidarXml:
    def test_valido(self, tmp_path):
        xsd = tmp_path / "test.xsd"
        xsd.write_bytes(MINI_XSD)
        errores = validar_xml(b"<root><hijo>texto</hijo></root>", xsd)
        assert errores == []

    def test_invalido_devuelve_errores(self, tmp_path):
        xsd = tmp_path / "test.xsd"
        xsd.write_bytes(MINI_XSD)
        errores = validar_xml(b"<root><otro>x</otro></root>", xsd)
        assert len(errores) > 0
        assert "otro" in errores[0]

    def test_validar_xml_str(self, tmp_path):
        xsd = tmp_path / "test.xsd"
        xsd.write_bytes(MINI_XSD)
        errores = validar_xml_str("<root><hijo>x</hijo></root>", xsd)
        assert errores == []


class TestDescargarXsds:
    @patch("siicl.validacion.requests.get")
    def test_descarga_xsd_directo(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = MINI_XSD
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        paths = descargar_xsds(tmp_path)

        # Al menos los XSDs directos
        nombres = [p.name for p in paths]
        assert "EnvioBOLETA_v11.xsd" in nombres
        assert "ConsumoFolio_v10.xsd" in nombres
        assert "xmldsignature_v10.xsd" in nombres
