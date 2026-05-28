"""Cliente HTTP para SII Chile (SOAP clásico y REST nuevo de boletas).

Endpoints:
    SOAP clásico (DTE, libros, RCOF):
        cert:  https://maullin.sii.cl/cgi_dte/UPL/DTEUpload
        prod:  https://palena.sii.cl/cgi_dte/UPL/DTEUpload
        token: /DTEWS/CrSeed.jws + /DTEWS/GetTokenFromSeed.jws

    REST boletas (solo PRODUCCIÓN operativa, NO certificación):
        token: https://apicert.sii.cl/recursos/v1/boleta.electronica.{semilla,token}
        envío: https://pangal.sii.cl/recursos/v1/boleta.electronica.envio

IMPORTANTE: para certificación de boletas, usar SOAP clásico (DTEUpload).
El REST de pangal NO procesa envíos como set de pruebas — solo operativos.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import requests
from lxml import etree

from siicl.firma import Cert, firmar_get_token

Ambiente = Literal["cert", "prod"]

SOAP_HOSTS = {
    "cert": "maullin.sii.cl",
    "prod": "palena.sii.cl",
}

REST_TOKEN_HOSTS = {
    "cert": "apicert.sii.cl",
    "prod": "api.sii.cl",
}

REST_ENVIO_HOSTS = {
    "cert": "pangal.sii.cl",
    "prod": "rahue.sii.cl",
}

USER_AGENT = "siicl-python/0.1"

# Mensaje SOAP CrSeed (estático, sin parámetros)
SOAP_GET_SEED = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">'
    "<SOAP-ENV:Body>"
    '<getSeed xmlns="http://DefaultNamespace"/>'
    "</SOAP-ENV:Body>"
    "</SOAP-ENV:Envelope>"
)


@dataclass
class ResultadoEnvio:
    """Resultado de un upload al SII."""

    track_id: str | None
    status: str | None
    raw_response: str
    http_status: int

    @property
    def ok(self) -> bool:
        return self.track_id is not None


# ============================================================================
# SOAP CLÁSICO (maullin/palena) — para DTE, libros, RCOF, set boletas cert
# ============================================================================


def obtener_semilla_soap(ambiente: Ambiente = "cert") -> str:
    """Obtiene semilla del SII por SOAP."""
    host = SOAP_HOSTS[ambiente]
    url = f"https://{host}/DTEWS/CrSeed.jws"
    resp = requests.post(
        url,
        data=SOAP_GET_SEED.encode("UTF-8"),
        headers={
            "Content-Type": "text/xml; charset=UTF-8",
            "SOAPAction": "",
            "User-Agent": USER_AGENT,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return _extraer_semilla(resp.text)


def _extraer_semilla(soap_xml: str) -> str:
    """Extrae el valor SEMILLA del response SOAP."""
    # Limpiar el SOAP envelope para obtener el XML interno (escapado)
    root = etree.fromstring(soap_xml.encode("UTF-8"))
    inner_text = root.find(".//{*}getSeedReturn")
    if inner_text is None or inner_text.text is None:
        raise RuntimeError(f"No se pudo extraer semilla del SOAP response: {soap_xml[:300]}")
    inner_root = etree.fromstring(inner_text.text.encode("UTF-8"))
    return inner_root.find(".//{*}SEMILLA").text.strip()


def obtener_token_soap(semilla: str, cert: Cert, ambiente: Ambiente = "cert") -> str:
    """Firma la semilla y obtiene el token de autenticación SOAP."""
    host = SOAP_HOSTS[ambiente]
    url = f"https://{host}/DTEWS/GetTokenFromSeed.jws"

    token_xml = firmar_get_token(semilla, cert)
    # Envolver en SOAP envelope para getToken
    inner_xml = token_xml.replace('"', "&quot;")
    soap = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">'
        "<SOAP-ENV:Body>"
        '<getToken xmlns="http://DefaultNamespace">'
        f'<pszXml xsi:type="xsd:string" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema">'
        f"{inner_xml}"
        "</pszXml>"
        "</getToken>"
        "</SOAP-ENV:Body>"
        "</SOAP-ENV:Envelope>"
    )
    resp = requests.post(
        url,
        data=soap.encode("UTF-8"),
        headers={
            "Content-Type": "text/xml; charset=UTF-8",
            "SOAPAction": "",
            "User-Agent": USER_AGENT,
        },
        timeout=30,
    )
    resp.raise_for_status()

    root = etree.fromstring(resp.text.encode("UTF-8"))
    inner = root.find(".//{*}getTokenReturn")
    if inner is None or inner.text is None:
        raise RuntimeError(f"No se pudo extraer token: {resp.text[:300]}")
    inner_root = etree.fromstring(inner.text.encode("UTF-8"))
    estado = inner_root.find(".//{*}ESTADO")
    if estado is not None and estado.text != "00":
        raise RuntimeError(f"Token rechazado: ESTADO={estado.text}")
    return inner_root.find(".//{*}TOKEN").text.strip()


def upload_soap(
    xml_path: str | Path | bytes,
    *,
    rut_emisor: str,
    rut_envia: str,
    token: str,
    ambiente: Ambiente = "cert",
    filename: str | None = None,
) -> ResultadoEnvio:
    """Sube un archivo XML al SII por SOAP/multipart (DTEUpload).

    Args:
        xml_path: ruta al archivo XML o bytes en memoria.
        rut_emisor: RUT empresa (NNNNNNNN-D).
        rut_envia: RUT firmante (NNNNNNNN-D).
        token: token de autenticación.
        ambiente: "cert" o "prod".
        filename: nombre del archivo en multipart. Si es None se infiere.
                  IMPORTANTE: el SII usa este nombre como key de deduplicación.
                  Si reintentas con mismo filename → SCH-00001 "Invalid Schema".
                  Variar nombre entre reintentos.
    """
    if isinstance(xml_path, (str, Path)):
        xml_bytes = Path(xml_path).read_bytes()
        if filename is None:
            filename = Path(xml_path).name
    else:
        xml_bytes = xml_path
        if filename is None:
            raise ValueError("filename requerido si se pasa xml como bytes")

    host = SOAP_HOSTS[ambiente]
    url = f"https://{host}/cgi_dte/UPL/DTEUpload"

    rut_n, dv = rut_emisor.split("-")
    rut_en_n, dv_en = rut_envia.split("-")

    files = {"archivo": (filename, xml_bytes, "text/xml")}
    data = {
        "rutSender": rut_en_n,
        "dvSender": dv_en,
        "rutCompany": rut_n,
        "dvCompany": dv,
    }
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/xml",
        "Cookie": f"TOKEN={token}",
    }

    resp = requests.post(url, data=data, files=files, headers=headers, timeout=60)
    return _parse_soap_response(resp.text, resp.status_code)


def _parse_soap_response(body: str, http_status: int) -> ResultadoEnvio:
    """Parsea response SOAP del DTEUpload."""
    track_id = status = None
    try:
        root = etree.fromstring(body.encode("UTF-8"))
        status = (root.findtext("STATUS") or "").strip() or None
        track_id = (root.findtext("TRACKID") or "").strip() or None
    except etree.XMLSyntaxError:
        pass
    return ResultadoEnvio(
        track_id=track_id,
        status=status,
        raw_response=body,
        http_status=http_status,
    )


def enviar_soap(
    xml_path: str | Path | bytes,
    *,
    rut_emisor: str,
    rut_envia: str,
    cert: Cert,
    ambiente: Ambiente = "cert",
    filename: str | None = None,
) -> ResultadoEnvio:
    """Conveniencia: hace semilla → token → upload SOAP en una sola llamada."""
    semilla = obtener_semilla_soap(ambiente)
    token = obtener_token_soap(semilla, cert, ambiente)
    return upload_soap(
        xml_path,
        rut_emisor=rut_emisor,
        rut_envia=rut_envia,
        token=token,
        ambiente=ambiente,
        filename=filename,
    )


# ============================================================================
# REST NUEVO (apicert/api + pangal/rahue) — para boletas en PRODUCCIÓN
# ============================================================================


def obtener_semilla_rest(ambiente: Ambiente = "cert") -> str:
    """Obtiene semilla del API REST de boletas."""
    host = REST_TOKEN_HOSTS[ambiente]
    url = f"https://{host}/recursos/v1/boleta.electronica.semilla"
    resp = requests.get(
        url,
        headers={"Accept": "application/xml", "User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    root = etree.fromstring(resp.content)
    sem = root.xpath("string(//*[local-name()='SEMILLA' or local-name()='semilla'])")
    if not sem:
        raise RuntimeError(f"sin SEMILLA en respuesta: {resp.text[:300]}")
    return sem


def obtener_token_rest(semilla: str, cert: Cert, ambiente: Ambiente = "cert") -> str:
    """Firma la semilla y obtiene el token REST."""
    host = REST_TOKEN_HOSTS[ambiente]
    url = f"https://{host}/recursos/v1/boleta.electronica.token"

    token_xml = firmar_get_token(semilla, cert)
    resp = requests.post(
        url,
        data=token_xml.encode("UTF-8"),
        headers={
            "Content-Type": "application/xml",
            "Accept": "application/xml",
            "User-Agent": USER_AGENT,
        },
        timeout=30,
    )
    resp.raise_for_status()
    root = etree.fromstring(resp.content)
    tok = root.xpath("string(//*[local-name()='TOKEN' or local-name()='token'])")
    if not tok:
        raise RuntimeError(f"sin TOKEN en respuesta: {resp.text[:300]}")
    return tok


def upload_boleta_rest(
    xml_path: str | Path | bytes,
    *,
    rut_emisor: str,
    rut_envia: str,
    token: str,
    ambiente: Ambiente = "cert",
    filename: str | None = None,
) -> ResultadoEnvio:
    """Sube boletas operativas (producción) por REST a pangal/rahue.

    NO usar para certificación. El set de pruebas de boletas va por SOAP
    (enviar_soap o upload_soap).
    """
    if isinstance(xml_path, (str, Path)):
        xml_bytes = Path(xml_path).read_bytes()
        if filename is None:
            filename = Path(xml_path).name
    else:
        xml_bytes = xml_path
        if filename is None:
            raise ValueError("filename requerido si se pasa xml como bytes")

    host = REST_ENVIO_HOSTS[ambiente]
    url = f"https://{host}/recursos/v1/boleta.electronica.envio"

    rut_n, dv = rut_emisor.split("-")
    rut_en_n, dv_en = rut_envia.split("-")

    files = {"archivo": (filename, xml_bytes, "text/xml")}
    data = {
        "rutSender": rut_en_n,
        "dvSender": dv_en,
        "rutCompany": rut_n,
        "dvCompany": dv,
    }
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Cookie": f"TOKEN={token}",
    }
    resp = requests.post(url, data=data, files=files, headers=headers, timeout=60)

    # REST response es JSON
    track_id = status = None
    try:
        import json

        data_json = json.loads(resp.text)
        track_id = str(data_json.get("trackid", "")) or None
        status = data_json.get("estado") or None
    except (ValueError, TypeError):
        pass

    return ResultadoEnvio(
        track_id=track_id,
        status=status,
        raw_response=resp.text,
        http_status=resp.status_code,
    )


def consultar_estado_rest(
    track_id: str,
    *,
    rut_emisor: str,
    token: str,
    ambiente: Ambiente = "cert",
) -> dict:
    """Consulta estado de un envío de boletas por REST."""
    host = REST_TOKEN_HOSTS[ambiente]
    rut_n, dv = rut_emisor.split("-")
    url = f"https://{host}/recursos/v1/boleta.electronica.envio/{rut_n}-{dv}-{track_id}"

    resp = requests.get(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "Cookie": f"TOKEN={token}",
        },
        timeout=30,
    )
    import json

    try:
        return json.loads(resp.text)
    except ValueError:
        return {"raw": resp.text, "http_status": resp.status_code}
