"""Validación de XML contra XSDs oficiales del SII.

Descarga los XSDs vigentes desde sii.cl la primera vez y los cachea localmente.
Use siempre el XSD oficial para validar, NO el de librerías de terceros
(ver docs/xsd-oficial-vs-dansanti.md).
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Iterable

import requests
from lxml import etree

# XSDs directos (URL sin ZIP)
XSDS_DIRECTOS = {
    "EnvioBOLETA_v11.xsd": "https://www.sii.cl/factura_electronica/EnvioBOLETA_v11.xsd",
    "ConsumoFolio_v10.xsd": "https://www.sii.cl/factura_electronica/factura_mercado/ConsumoFolio_v10.xsd",
    "xmldsignature_v10.xsd": "https://www.sii.cl/factura_electronica/xmldsignature_v10.xsd",
}

# ZIPs que contienen los XSDs (URL → archivos esperados)
ZIPS = {
    "schema_dte.zip": "https://www.sii.cl/factura_electronica/factura_mercado/schema_dte.zip",
    "schema_iecv.zip": "https://www.sii.cl/factura_electronica/factura_mercado/schema_iecv.zip",
    "schema_lgd.zip": "https://www.sii.cl/factura_electronica/factura_mercado/schema_lgd.zip",
    "schema_ic.zip": "https://www.sii.cl/factura_electronica/factura_mercado/schema_ic.zip",
    "schema19983.zip": "https://www.sii.cl/factura_electronica/factura_mercado/schema19983.zip",
    "schema_resp.zip": "https://www.sii.cl/factura_electronica/factura_mercado/schema_resp.zip",
    "schema_resp_libros.zip": "https://www.sii.cl/factura_electronica/factura_mercado/schema_resp_libros.zip",
    "schema_envio_bol.zip": "https://www.sii.cl/factura_electronica/factura_mercado/schema_envio_bol.zip",
    "schema_libro_bol.zip": "https://www.sii.cl/factura_electronica/factura_mercado/schema_libro_bol.zip",
}


def descargar_xsds(destino: str | Path) -> list[Path]:
    """Descarga todos los XSDs oficiales del SII a la carpeta destino.

    Retorna lista de paths a los XSDs descargados.
    """
    dest = Path(destino)
    dest.mkdir(parents=True, exist_ok=True)
    descargados = []

    # XSDs directos
    for nombre, url in XSDS_DIRECTOS.items():
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        path = dest / nombre
        path.write_bytes(resp.content)
        descargados.append(path)

    # ZIPs
    for nombre_zip, url in ZIPS.items():
        resp = requests.get(url, timeout=60)
        if resp.status_code != 200:
            continue  # algunos ZIPs pueden no estar disponibles
        try:
            z = zipfile.ZipFile(io.BytesIO(resp.content))
        except zipfile.BadZipFile:
            continue  # response no era un ZIP válido
        for name in z.namelist():
            if name.endswith(".xsd"):
                path = dest / Path(name).name
                path.write_bytes(z.read(name))
                descargados.append(path)

    return sorted(set(descargados))


def validar_xml(xml_bytes: bytes, xsd_path: str | Path) -> list[str]:
    """Valida un XML contra un XSD.

    Returns:
        Lista de errores (vacía si el XML es válido).
    """
    xml = etree.fromstring(xml_bytes)
    xsd = etree.XMLSchema(etree.parse(str(xsd_path)))
    if xsd.validate(xml):
        return []
    return [
        f"línea {e.line}: {e.message}"
        for e in xsd.error_log
    ]


def validar_xml_str(xml_str: str, xsd_path: str | Path) -> list[str]:
    """Conveniencia para pasar XML como string."""
    return validar_xml(xml_str.encode("ISO-8859-1"), xsd_path)
