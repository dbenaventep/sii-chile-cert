"""Parser de archivos CAF (Código de Autorización de Folios) del SII.

El CAF es el archivo XML que el SII entrega al solicitar timbraje. Contiene:
- Datos del rango autorizado (RUT emisor, tipo DTE, folio inicial/final)
- Clave pública RSA del solicitante (para validar el TED)
- Clave privada RSA (para que el contribuyente firme el TED de cada DTE)
- Firma SHA1withRSA del SII sobre los datos de autorización
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.serialization import load_pem_private_key
from lxml import etree


@dataclass
class CAF:
    """Datos parseados de un archivo CAF.

    Atributos:
        rut_emisor: RUT autorizado (NNNNNNNN-D).
        razon_social: razón social del emisor (puede tener Ñ/acentos).
        tipo_dte: tipo de DTE autorizado (33, 39, etc).
        folio_inicial: primer folio del rango.
        folio_final: último folio del rango.
        fecha_autorizacion: fecha de emisión del CAF (AAAA-MM-DD).
        rsa_private_pem: clave privada RSA en PEM (para firmar TEDs).
        rsa_public_modulus_b64: módulo RSA público en base64.
        rsa_public_exponent_b64: exponente RSA público en base64.
        idk: identificador de llave (típicamente 100).
        firma_sii_b64: firma SHA1withRSA del SII sobre <DA>.
        da_xml: XML del bloque <DA> tal cual viene en el CAF (para verificación).
        raw_xml: bytes del archivo CAF completo (para incrustarlo en el TED).
    """

    rut_emisor: str
    razon_social: str
    tipo_dte: int
    folio_inicial: int
    folio_final: int
    fecha_autorizacion: str
    rsa_private_pem: bytes
    rsa_public_modulus_b64: str
    rsa_public_exponent_b64: str
    idk: int
    firma_sii_b64: str
    da_xml: bytes
    raw_xml: bytes

    @classmethod
    def from_file(cls, path: str | Path) -> CAF:
        """Carga y parsea un CAF desde disco. Detecta encoding ISO-8859-1."""
        raw = Path(path).read_bytes()
        return cls.from_bytes(raw)

    @classmethod
    def from_bytes(cls, raw: bytes) -> CAF:
        """Parsea un CAF desde bytes (típicamente leídos ISO-8859-1)."""
        # El CAF viene en ISO-8859-1; lxml lo detecta del XML decl o por defecto
        parser = etree.XMLParser(remove_blank_text=False)
        root = etree.fromstring(raw, parser)

        # Estructura: <AUTORIZACION><CAF><DA>...</DA><FRMA/></CAF><RSASK/><RSAPUBK/></AUTORIZACION>
        caf_elem = root.find("CAF")
        if caf_elem is None:
            raise ValueError("CAF inválido: falta elemento <CAF>")

        da = caf_elem.find("DA")
        if da is None:
            raise ValueError("CAF inválido: falta elemento <DA>")

        rng = da.find("RNG")
        if rng is None:
            raise ValueError("CAF inválido: falta elemento <RNG>")

        rsapk = da.find("RSAPK")
        if rsapk is None:
            raise ValueError("CAF inválido: falta clave pública RSA <RSAPK>")

        frma = caf_elem.find("FRMA")
        if frma is None or frma.text is None:
            raise ValueError("CAF inválido: falta firma SII <FRMA>")

        rsask = root.find("RSASK")
        if rsask is None or rsask.text is None:
            raise ValueError("CAF inválido: falta clave privada <RSASK>")

        # Bytes del <DA> tal cual aparece en el CAF (firma SII se hace sobre estos bytes)
        da_xml = etree.tostring(da)

        return cls(
            rut_emisor=da.findtext("RE", "").strip(),
            razon_social=da.findtext("RS", "").strip(),
            tipo_dte=int(da.findtext("TD", "0")),
            folio_inicial=int(rng.findtext("D", "0")),
            folio_final=int(rng.findtext("H", "0")),
            fecha_autorizacion=da.findtext("FA", "").strip(),
            rsa_private_pem=rsask.text.strip().encode("ascii"),
            rsa_public_modulus_b64=(rsapk.findtext("M") or "").strip(),
            rsa_public_exponent_b64=(rsapk.findtext("E") or "").strip(),
            idk=int(da.findtext("IDK", "0")),
            firma_sii_b64=frma.text.strip(),
            da_xml=da_xml,
            raw_xml=raw,
        )

    def cubre_folio(self, folio: int) -> bool:
        """Retorna True si el folio cae dentro del rango autorizado."""
        return self.folio_inicial <= folio <= self.folio_final

    def cargar_clave_privada(self):
        """Carga la clave privada RSA del CAF como objeto cryptography.

        Returns:
            cryptography.hazmat.primitives.asymmetric.rsa.RSAPrivateKey
        """
        return load_pem_private_key(self.rsa_private_pem, password=None)

    def caf_xml_b64(self) -> str:
        """Retorna el CAF XML completo en base64 (formato esperado por dansanti)."""
        import base64

        return base64.b64encode(self.raw_xml).decode()
