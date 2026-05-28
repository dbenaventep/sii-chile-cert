"""Tipos y validaciones básicas del SII Chile.

Incluye:
- Validación de RUT con dígito verificador módulo 11.
- Normalización y parseo de RUTs.
- Tipos para los documentos soportados.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum


class TipoDTE(IntEnum):
    """Tipos de Documento Tributario Electrónico soportados por el SII."""

    FACTURA = 33
    FACTURA_EXENTA = 34
    BOLETA = 39
    BOLETA_EXENTA = 41
    LIQUIDACION = 43
    FACTURA_COMPRA = 46
    GUIA_DESPACHO = 52
    NOTA_DEBITO = 56
    NOTA_CREDITO = 61
    FACTURA_EXPORTACION = 110
    NC_EXPORTACION = 111
    ND_EXPORTACION = 112


# Tipos de DTE considerados "boletas" - tienen flujo distinto a facturas
BOLETAS = {TipoDTE.BOLETA, TipoDTE.BOLETA_EXENTA}


def es_boleta(tipo: int | TipoDTE) -> bool:
    """Retorna True si el tipo corresponde a una boleta electrónica."""
    return int(tipo) in BOLETAS


def es_nota_credito(tipo: int | TipoDTE) -> bool:
    """Retorna True si el tipo es Nota de Crédito (T61, T112)."""
    return int(tipo) in (61, 112)


def es_nota_debito(tipo: int | TipoDTE) -> bool:
    """Retorna True si el tipo es Nota de Débito (T56, T111)."""
    return int(tipo) in (56, 111)


_RUT_PATTERN = re.compile(r"^(\d{1,8})-([0-9K])$")


def calcular_dv(rut_numerico: int) -> str:
    """Calcula el dígito verificador chileno de un RUT (módulo 11).

    Args:
        rut_numerico: número entero del RUT (sin dígito verificador).

    Returns:
        El dígito verificador como string: '0'-'9' o 'K'.

    Ejemplo:
        >>> calcular_dv(76123456)
        '7'
    """
    if rut_numerico <= 0:
        raise ValueError(f"RUT debe ser positivo, recibido: {rut_numerico}")

    suma = 0
    multiplicador = 2
    for digito in reversed(str(rut_numerico)):
        suma += int(digito) * multiplicador
        multiplicador = multiplicador + 1 if multiplicador < 7 else 2

    resto = 11 - (suma % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


@dataclass(frozen=True)
class Rut:
    """RUT chileno validado.

    Atributos:
        numero: parte numérica (sin dígito verificador).
        dv: dígito verificador ('0'-'9' o 'K').

    Uso:
        >>> rut = Rut.parse("76123456-0")
        >>> rut.es_valido()
        True
        >>> str(rut)
        '76123456-0'
    """

    numero: int
    dv: str

    def __post_init__(self):
        if self.numero <= 0:
            raise ValueError(f"RUT debe ser positivo, recibido: {self.numero}")
        if self.dv not in "0123456789K":
            raise ValueError(f"DV inválido: {self.dv!r}")

    @classmethod
    def parse(cls, rut_str: str) -> Rut:
        """Parsea un RUT en formato 'NNNNNNNN-D'.

        Acepta también con puntos: '76.123.456-7'. Normaliza la K a mayúscula.
        """
        s = rut_str.replace(".", "").strip().upper()
        match = _RUT_PATTERN.match(s)
        if not match:
            raise ValueError(f"Formato de RUT inválido: {rut_str!r}")
        return cls(numero=int(match.group(1)), dv=match.group(2))

    def es_valido(self) -> bool:
        """Verifica que el DV sea el correcto para el número."""
        return self.dv == calcular_dv(self.numero)

    def __str__(self) -> str:
        return f"{self.numero}-{self.dv}"


# RUTs de uso común en certificación
RUT_SII = "60803000-K"  # Receptor en carátula de todos los envíos al SII
RUT_CONSUMIDOR_FINAL = "66666666-6"  # Receptor genérico para boletas
RUT_EXPORTACION = "55555555-5"  # Receptor para facturas de exportación
