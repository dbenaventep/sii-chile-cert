"""Tests de siicl.types."""
import pytest

from siicl.types import (
    BOLETAS,
    Rut,
    TipoDTE,
    calcular_dv,
    es_boleta,
    es_nota_credito,
    es_nota_debito,
)


class TestCalcularDV:
    """Test del cálculo de dígito verificador chileno (módulo 11)."""

    @pytest.mark.parametrize("numero,dv_esperado", [
        (1, "9"),
        (11111111, "1"),
        (12345678, "5"),
        (76123456, "0"),
        (77777777, "7"),
        (88888888, "8"),
        (60803000, "K"),  # RUT del SII
        (66666666, "6"),
    ])
    def test_dv_correcto(self, numero, dv_esperado):
        assert calcular_dv(numero) == dv_esperado

    def test_negativo_falla(self):
        with pytest.raises(ValueError):
            calcular_dv(-1)

    def test_cero_falla(self):
        with pytest.raises(ValueError):
            calcular_dv(0)


class TestRut:
    """Test de parseo y validación de RUTs."""

    def test_parse_basico(self):
        rut = Rut.parse("76123456-0")
        assert rut.numero == 76123456
        assert rut.dv == "0"
        assert str(rut) == "76123456-0"

    def test_parse_con_puntos(self):
        rut = Rut.parse("76.123.456-0")
        assert str(rut) == "76123456-0"

    def test_parse_k_minuscula(self):
        rut = Rut.parse("60803000-k")
        assert rut.dv == "K"

    def test_parse_invalido(self):
        for invalido in ["abc", "76123456", "-7", "76123456-", "76.123-456-7"]:
            with pytest.raises(ValueError):
                Rut.parse(invalido)

    def test_es_valido(self):
        assert Rut.parse("76123456-0").es_valido()
        assert Rut.parse("60803000-K").es_valido()
        assert not Rut.parse("76123456-1").es_valido()  # DV equivocado

    def test_inmutable(self):
        from dataclasses import FrozenInstanceError

        rut = Rut.parse("76123456-0")
        with pytest.raises(FrozenInstanceError):
            rut.numero = 12345


class TestTipoDTE:
    """Test del enum TipoDTE."""

    def test_valores(self):
        assert TipoDTE.FACTURA == 33
        assert TipoDTE.BOLETA == 39
        assert TipoDTE.GUIA_DESPACHO == 52
        assert TipoDTE.NOTA_CREDITO == 61
        assert TipoDTE.NOTA_DEBITO == 56

    def test_es_boleta(self):
        assert es_boleta(39)
        assert es_boleta(41)
        assert es_boleta(TipoDTE.BOLETA)
        assert not es_boleta(33)
        assert not es_boleta(TipoDTE.FACTURA)

    def test_boletas_set(self):
        assert BOLETAS == {TipoDTE.BOLETA, TipoDTE.BOLETA_EXENTA}

    def test_es_nota_credito(self):
        assert es_nota_credito(61)
        assert es_nota_credito(112)
        assert not es_nota_credito(56)

    def test_es_nota_debito(self):
        assert es_nota_debito(56)
        assert es_nota_debito(111)
        assert not es_nota_debito(61)
