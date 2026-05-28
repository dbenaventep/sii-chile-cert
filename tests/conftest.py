"""Fixtures compartidos para tests.

Genera certificados PFX y CAFs sintéticos (NO firmados por el SII real)
para pruebas locales. Estos fixtures NUNCA sirven para emitir DTEs reales.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID


@pytest.fixture(scope="session")
def pfx_demo():
    """Genera un PFX auto-firmado en memoria para tests.

    Returns:
        dict con: 'pfx_bytes' (bytes del PFX), 'password' (str).
    """
    # Generar clave RSA 2048 bits
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Crear certificado auto-firmado
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "CL"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TEST EMISOR DEMO"),
        x509.NameAttribute(NameOID.COMMON_NAME, "EMISOR DEMO TEST"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .sign(private_key, hashes.SHA256())
    )

    password = "test_pwd"
    pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=b"test-cert",
        key=private_key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode()),
    )

    return {"pfx_bytes": pfx_bytes, "password": password}


@pytest.fixture(scope="session")
def caf_demo_xml():
    """Genera un XML de CAF sintético para tests.

    El CAF tiene clave RSA propia (distinta a la del firmante) y NO está
    firmado por el SII (FRMA es placeholder). Solo sirve para validar parseo
    y generación de TED en tests; NO usar para emitir DTEs.

    Returns:
        bytes del CAF en ISO-8859-1.
    """
    # CAFs reales del SII usan RSA 512 bits, pero cryptography moderno exige >=1024
    # para generar. Para tests basta 1024 (sólo validamos parseo).
    private_key = rsa.generate_private_key(public_exponent=3, key_size=1024)
    public_numbers = private_key.public_key().public_numbers()

    modulus_bytes = public_numbers.n.to_bytes(
        (public_numbers.n.bit_length() + 7) // 8, "big"
    )
    exponent_bytes = public_numbers.e.to_bytes(
        (public_numbers.e.bit_length() + 7) // 8, "big"
    )

    modulus_b64 = base64.b64encode(modulus_bytes).decode()
    exponent_b64 = base64.b64encode(exponent_bytes).decode()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    caf_xml = (
        '<?xml version="1.0"?>\n'
        '<AUTORIZACION>\n'
        '<CAF version="1.0">\n'
        '<DA>\n'
        '<RE>76123456-0</RE>\n'
        '<RS>EMPRESA DEMO SPA</RS>\n'
        '<TD>39</TD>\n'
        '<RNG><D>1</D><H>50</H></RNG>\n'
        '<FA>2026-01-01</FA>\n'
        f'<RSAPK><M>{modulus_b64}</M><E>{exponent_b64}</E></RSAPK>\n'
        '<IDK>100</IDK>\n'
        '</DA>\n'
        # FRMA placeholder - en CAF real esto sería la firma SHA1withRSA del SII
        '<FRMA algoritmo="SHA1withRSA">'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        '</FRMA>\n'
        '</CAF>\n'
        f'<RSASK>{private_pem}</RSASK>\n'
        f'<RSAPUBK>{public_pem}</RSAPUBK>\n'
        '</AUTORIZACION>\n'
    )
    return caf_xml.encode("ISO-8859-1")
