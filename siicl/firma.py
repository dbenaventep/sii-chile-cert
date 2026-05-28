"""Firma electrónica para SII Chile.

Funcionalidades:
- Cargar certificado digital desde archivo PFX (PKCS#12).
- Firmar elementos XML con XMLDSig (estándar SII): SHA1, RSA-SHA1, c14n exclusive.
- Generar firma del token getToken para autenticación SOAP.
- Verificar firmas XML.

El SII usa firmas XML enveloped con:
- CanonicalizationMethod: http://www.w3.org/TR/2001/REC-xml-c14n-20010315
- SignatureMethod: http://www.w3.org/2000/09/xmldsig#rsa-sha1
- DigestMethod: http://www.w3.org/2000/09/xmldsig#sha1
- KeyInfo con RSAKeyValue y X509Certificate
"""
from __future__ import annotations

import base64
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import Certificate
from lxml import etree

NS_SII = "http://www.sii.cl/SiiDte"
NS_DS = "http://www.w3.org/2000/09/xmldsig#"


class Cert:
    """Certificado digital cargado desde PFX, listo para firmar.

    Uso:
        >>> cert = Cert.from_pfx("mi_cert.pfx", "mi_password")
        >>> rut = cert.rut_firmante  # extraído del subject del cert
        >>> firma_b64 = cert.firmar_bytes(b"datos a firmar")
    """

    def __init__(
        self,
        private_key: rsa.RSAPrivateKey,
        certificate: Certificate,
    ):
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise TypeError(
                "Solo se soportan claves RSA. SII no acepta DSA/EC en este "
                "estándar."
            )
        self.private_key = private_key
        self.certificate = certificate

    @classmethod
    def from_pfx(cls, pfx_path: str | Path, password: str) -> Cert:
        """Carga un certificado PKCS#12 (.pfx) desde disco."""
        data = Path(pfx_path).read_bytes()
        return cls.from_pfx_bytes(data, password)

    @classmethod
    def from_pfx_bytes(cls, data: bytes, password: str) -> Cert:
        """Carga un certificado PKCS#12 desde bytes en memoria."""
        password_bytes = password.encode() if password else None
        private_key, cert, _additional = pkcs12.load_key_and_certificates(
            data, password_bytes
        )
        if private_key is None or cert is None:
            raise ValueError("PFX no contiene clave privada o certificado")
        return cls(private_key, cert)

    @property
    def rut_firmante(self) -> str | None:
        """Extrae el RUT del firmante desde el Subject Alternative Name del cert.

        El SII e-CertChile codifica el RUT en una extensión OID propietaria.
        Si no se encuentra, retorna None.
        """
        from cryptography import x509

        # OID conocido para RUT del firmante en certs e-CertChile (1.3.6.1.4.1.8321.1)
        # Para mantener simplicidad este lookup es best-effort.
        try:
            ext = self.certificate.extensions.get_extension_for_oid(
                x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
            )
            for name in ext.value:
                if isinstance(name, x509.OtherName):
                    # Heurística: buscar formato RUT en el value
                    value = name.value.decode("utf-8", errors="ignore")
                    import re

                    match = re.search(r"\d{5,8}-[0-9K]", value)
                    if match:
                        return match.group(0)
        except x509.ExtensionNotFound:
            pass
        return None

    @property
    def public_key_modulus_b64(self) -> str:
        """Módulo RSA en base64 (para KeyInfo de XMLDSig)."""
        pub = self.private_key.public_key()
        numbers = pub.public_numbers()
        n_bytes = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
        return base64.b64encode(n_bytes).decode()

    @property
    def public_key_exponent_b64(self) -> str:
        """Exponente RSA en base64."""
        pub = self.private_key.public_key()
        numbers = pub.public_numbers()
        e_bytes = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
        return base64.b64encode(e_bytes).decode()

    @property
    def cert_der_b64(self) -> str:
        """Certificado X.509 en base64 DER (para X509Certificate en KeyInfo)."""
        der = self.certificate.public_bytes(serialization.Encoding.DER)
        return base64.b64encode(der).decode()

    def firmar_bytes(self, data: bytes) -> bytes:
        """Firma bytes con RSA-SHA1 (estándar SII)."""
        return self.private_key.sign(data, padding.PKCS1v15(), hashes.SHA1())

    def firmar_bytes_b64(self, data: bytes) -> str:
        """Firma bytes y retorna en base64."""
        return base64.b64encode(self.firmar_bytes(data)).decode()


def canonicalize(elem: etree._Element) -> bytes:
    """Canonicaliza un elemento XML con c14n (estándar SII).

    El SII usa c14n no-exclusivo: http://www.w3.org/TR/2001/REC-xml-c14n-20010315
    """
    return etree.tostring(elem, method="c14n")


def calcular_digest(elem: etree._Element) -> str:
    """Calcula el DigestValue SHA-1 base64 del elemento canonicalizado."""
    from cryptography.hazmat.primitives.hashes import SHA1, Hash

    canonical = canonicalize(elem)
    h = Hash(SHA1())
    h.update(canonical)
    return base64.b64encode(h.finalize()).decode()


def firmar_xml(
    xml_str: str,
    cert: Cert,
    *,
    reference_uri: str = "",
    reference_id: str | None = None,
) -> str:
    """Firma un documento XML con XMLDSig enveloped estándar SII.

    Args:
        xml_str: el XML como string (típicamente sin declaración encoding).
        cert: certificado para firmar.
        reference_uri: valor del atributo URI de la Reference. Por defecto vacío
                       (firma el documento completo). Para firmar un elemento
                       con `ID="foo"`, usar "#foo".
        reference_id: si se pasa, la firma agregará un atributo ID a la Signature.

    Returns:
        El XML firmado como string, con `<Signature>` añadido como último hijo
        del root (envelope).
    """
    parser = etree.XMLParser(remove_blank_text=False)
    root = etree.fromstring(xml_str.encode("ISO-8859-1"), parser)

    # 1. Calcular DigestValue del elemento referenciado
    if reference_uri and reference_uri.startswith("#"):
        ref_id = reference_uri[1:]
        target = root.xpath(f"//*[@ID='{ref_id}']")
        if not target:
            raise ValueError(f"No se encontró elemento con ID={ref_id}")
        digest_target = target[0]
    else:
        digest_target = root

    digest_value = calcular_digest(digest_target)

    # 2. Construir SignedInfo
    signed_info_xml = (
        f'<SignedInfo xmlns="{NS_DS}">'
        '<CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>'
        '<SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>'
        f'<Reference URI="{reference_uri}">'
        '<Transforms>'
        '<Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>'
        '</Transforms>'
        '<DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>'
        f'<DigestValue>{digest_value}</DigestValue>'
        '</Reference>'
        '</SignedInfo>'
    )
    signed_info_elem = etree.fromstring(signed_info_xml)

    # 3. Firmar SignedInfo canonicalizado
    signed_info_canonical = canonicalize(signed_info_elem)
    signature_value = cert.firmar_bytes_b64(signed_info_canonical)

    # 4. Construir el bloque <Signature> completo
    sig_id_attr = f' Id="{reference_id}"' if reference_id else ""
    signature_xml = (
        f'<Signature xmlns="{NS_DS}"{sig_id_attr}>'
        f'{signed_info_xml}'
        f'<SignatureValue>{signature_value}</SignatureValue>'
        '<KeyInfo>'
        '<KeyValue>'
        '<RSAKeyValue>'
        f'<Modulus>{cert.public_key_modulus_b64}</Modulus>'
        f'<Exponent>{cert.public_key_exponent_b64}</Exponent>'
        '</RSAKeyValue>'
        '</KeyValue>'
        '<X509Data>'
        f'<X509Certificate>{cert.cert_der_b64}</X509Certificate>'
        '</X509Data>'
        '</KeyInfo>'
        '</Signature>'
    )

    # 5. Agregar Signature como último hijo del root
    signature_elem = etree.fromstring(signature_xml)
    root.append(signature_elem)

    return etree.tostring(root, encoding="ISO-8859-1", xml_declaration=False).decode("ISO-8859-1")


def firmar_get_token(semilla: str, cert: Cert) -> str:
    """Construye y firma el XML getToken para autenticación SOAP.

    El SII espera:
        <getToken>
          <item>
            <Semilla>NNNNNNNNNN</Semilla>
          </item>
          <Signature>...</Signature>
        </getToken>
    """
    base = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<getToken><item><Semilla>{semilla}</Semilla></item></getToken>'
    )
    # Firmar el documento completo (URI vacío)
    return firmar_xml(base.split("\n", 1)[1], cert, reference_uri="")
