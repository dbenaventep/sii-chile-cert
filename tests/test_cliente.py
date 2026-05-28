"""Tests de siicl.cliente.

Estos tests NO golpean el SII real — usan mocks de requests.
"""
from unittest.mock import MagicMock, patch

import pytest

from siicl.cliente import (
    REST_ENVIO_HOSTS,
    REST_TOKEN_HOSTS,
    SOAP_HOSTS,
    ResultadoEnvio,
    _parse_soap_response,
    upload_boleta_rest,
    upload_soap,
)


class TestConstants:
    def test_hosts_cert_prod(self):
        assert SOAP_HOSTS["cert"] == "maullin.sii.cl"
        assert SOAP_HOSTS["prod"] == "palena.sii.cl"
        assert REST_TOKEN_HOSTS["cert"] == "apicert.sii.cl"
        assert REST_TOKEN_HOSTS["prod"] == "api.sii.cl"
        assert REST_ENVIO_HOSTS["cert"] == "pangal.sii.cl"
        assert REST_ENVIO_HOSTS["prod"] == "rahue.sii.cl"


class TestParseSoap:
    def test_response_ok(self):
        body = (
            "<RECEPCIONDTE>"
            "<STATUS>0</STATUS>"
            "<TRACKID>0249800000</TRACKID>"
            "</RECEPCIONDTE>"
        )
        r = _parse_soap_response(body, 200)
        assert r.ok
        assert r.track_id == "0249800000"
        assert r.status == "0"

    def test_response_error(self):
        body = (
            "<RECEPCIONDTE>"
            "<STATUS>7</STATUS>"
            "<DETAIL><ERROR>SCH-00001</ERROR></DETAIL>"
            "</RECEPCIONDTE>"
        )
        r = _parse_soap_response(body, 200)
        assert not r.ok
        assert r.track_id is None
        assert r.status == "7"

    def test_response_no_xml(self):
        r = _parse_soap_response("texto plano", 500)
        assert not r.ok
        assert r.http_status == 500


class TestUploadSoap:
    @patch("siicl.cliente.requests.post")
    def test_upload_arma_request_correctamente(self, mock_post, tmp_path):
        # Mock response OK
        mock_resp = MagicMock()
        mock_resp.text = "<RECEPCIONDTE><STATUS>0</STATUS><TRACKID>123</TRACKID></RECEPCIONDTE>"
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        xml_path = tmp_path / "envio.xml"
        xml_path.write_bytes(b"<EnvioDTE/>")

        result = upload_soap(
            xml_path,
            rut_emisor="76123456-0",
            rut_envia="11111111-1",
            token="ABC123",
            ambiente="cert",
        )

        assert result.ok
        assert result.track_id == "123"
        # Verificar que se llamó al endpoint correcto
        call_args = mock_post.call_args
        assert "maullin.sii.cl/cgi_dte/UPL/DTEUpload" in call_args[0][0]
        # Headers incluyen TOKEN cookie
        assert "ABC123" in call_args[1]["headers"]["Cookie"]
        # Data tiene rut/dv correctos
        data = call_args[1]["data"]
        assert data["rutCompany"] == "76123456"
        assert data["dvCompany"] == "0"
        assert data["rutSender"] == "11111111"
        assert data["dvSender"] == "1"

    @patch("siicl.cliente.requests.post")
    def test_upload_filename_personalizado(self, mock_post, tmp_path):
        mock_resp = MagicMock()
        mock_resp.text = "<RECEPCIONDTE><STATUS>0</STATUS><TRACKID>1</TRACKID></RECEPCIONDTE>"
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        xml_path = tmp_path / "default.xml"
        xml_path.write_bytes(b"<EnvioDTE/>")

        upload_soap(
            xml_path,
            rut_emisor="76123456-0",
            rut_envia="11111111-1",
            token="ABC",
            filename="CF_2026-05-27_v2.xml",
        )

        # Verificar que el filename pasado se usó
        files = mock_post.call_args[1]["files"]
        assert files["archivo"][0] == "CF_2026-05-27_v2.xml"


class TestUploadRest:
    @patch("siicl.cliente.requests.post")
    def test_upload_rest_arma_request(self, mock_post, tmp_path):
        mock_resp = MagicMock()
        mock_resp.text = '{"trackid": "27000000", "estado": "EPR"}'
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        xml_path = tmp_path / "envio.xml"
        xml_path.write_bytes(b"<EnvioBOLETA/>")

        result = upload_boleta_rest(
            xml_path,
            rut_emisor="76123456-0",
            rut_envia="11111111-1",
            token="TOK",
            ambiente="cert",
        )

        assert result.ok
        assert result.track_id == "27000000"
        assert result.status == "EPR"
        # Endpoint correcto: pangal en cert
        assert "pangal.sii.cl/recursos/v1/boleta.electronica.envio" in mock_post.call_args[0][0]


class TestResultadoEnvio:
    def test_ok_property(self):
        assert ResultadoEnvio(track_id="123", status="0", raw_response="", http_status=200).ok
        assert not ResultadoEnvio(track_id=None, status="7", raw_response="", http_status=200).ok
