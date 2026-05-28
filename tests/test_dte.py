"""Tests de siicl.dte."""
from lxml import etree

from siicl.dte import (
    DTE,
    NS_SII,
    Emisor,
    Item,
    Receptor,
    Referencia,
    calcular_totales,
    consumo_folios,
    dte_a_xml,
    envio_boleta,
    envio_dte,
    firmar_envio,
)
from siicl.firma import Cert


def _emisor_demo():
    return Emisor(
        rut="76123456-0",
        razon_social="EMPRESA DEMO SPA",
        giro="SERVICIOS DEMO",
        direccion="CALLE DEMO 123",
        comuna="PROVIDENCIA",
        ciudad="SANTIAGO",
        actecos=[123456],
    )


def _receptor_demo():
    return Receptor(
        rut="77234567-4",
        razon_social="CLIENTE DEMO LTDA",
        giro="GIRO CLIENTE",
        direccion="Cliente 456",
        comuna="Providencia",
        ciudad="Santiago",
    )


def _receptor_boleta():
    return Receptor(
        rut="66666666-6",
        razon_social="Sin RUT",
        direccion="Santiago",
        comuna="Santiago",
    )


class TestCalcularTotales:
    def test_factura_simple(self):
        items = [Item("A", 10, 5000), Item("B", 5, 12000)]
        t = calcular_totales(items)
        assert t["MntNeto"] == 110000
        assert t["IVA"] == 20900
        assert t["MntTotal"] == 130900
        assert t["MntExe"] == 0

    def test_factura_con_exento(self):
        items = [Item("A", 10, 5000), Item("B", 1, 25000, exento=True)]
        t = calcular_totales(items)
        assert t["MntNeto"] == 50000
        assert t["IVA"] == 9500
        assert t["MntExe"] == 25000
        assert t["MntTotal"] == 84500

    def test_boleta_precio_incluye_iva(self):
        items = [Item("Cambio aceite", 1, 19900), Item("Alineacion", 1, 9900)]
        t = calcular_totales(items, boleta=True)
        # Precios brutos. Neto = round(29800/1.19) = 25042
        assert t["MntNeto"] == 25042
        assert t["IVA"] == 4758
        assert t["MntTotal"] == 29800

    def test_descuento_linea(self):
        items = [Item("X", 100, 1000, descuento_pct=10)]
        t = calcular_totales(items)
        # 100 * 1000 * 0.9 = 90000
        assert t["MntNeto"] == 90000


class TestDteAXml:
    def test_factura_basica(self):
        dte = DTE(
            tipo=33,
            folio=1,
            fecha_emision="2026-04-29",
            emisor=_emisor_demo(),
            receptor=_receptor_demo(),
            items=[Item("Producto", 10, 5000)],
        )
        xml = dte_a_xml(dte)
        root = etree.fromstring(xml)
        assert root.tag == f"{{{NS_SII}}}DTE"
        # Documento ID
        doc = root.find(f"{{{NS_SII}}}Documento")
        assert doc.get("ID") == "T33F1"
        # Encabezado IdDoc
        iddoc = doc.find(f"{{{NS_SII}}}Encabezado/{{{NS_SII}}}IdDoc")
        assert iddoc.findtext(f"{{{NS_SII}}}TipoDTE") == "33"
        assert iddoc.findtext(f"{{{NS_SII}}}Folio") == "1"
        # Factura NO lleva IndServicio
        assert iddoc.find(f"{{{NS_SII}}}IndServicio") is None
        # Totales
        tot = doc.find(f"{{{NS_SII}}}Encabezado/{{{NS_SII}}}Totales")
        assert tot.findtext(f"{{{NS_SII}}}MntNeto") == "50000"
        assert tot.findtext(f"{{{NS_SII}}}MntTotal") == "59500"

    def test_boleta_t39_lleva_indservicio(self):
        dte = DTE(
            tipo=39,
            folio=1,
            fecha_emision="2026-04-29",
            emisor=_emisor_demo(),
            receptor=_receptor_boleta(),
            items=[Item("Producto", 1, 11900)],
        )
        xml = dte_a_xml(dte)
        root = etree.fromstring(xml)
        iddoc = root.find(
            f"{{{NS_SII}}}Documento/{{{NS_SII}}}Encabezado/{{{NS_SII}}}IdDoc"
        )
        assert iddoc.findtext(f"{{{NS_SII}}}IndServicio") == "3"

    def test_boleta_lleva_vlrpagar(self):
        dte = DTE(
            tipo=39,
            folio=1,
            fecha_emision="2026-04-29",
            emisor=_emisor_demo(),
            receptor=_receptor_boleta(),
            items=[Item("Producto", 1, 11900)],
        )
        xml = dte_a_xml(dte)
        root = etree.fromstring(xml)
        totales = root.find(
            f"{{{NS_SII}}}Documento/{{{NS_SII}}}Encabezado/{{{NS_SII}}}Totales"
        )
        assert totales.findtext(f"{{{NS_SII}}}VlrPagar") == "11900"

    def test_factura_NO_lleva_vlrpagar(self):
        dte = DTE(
            tipo=33,
            folio=1,
            fecha_emision="2026-04-29",
            emisor=_emisor_demo(),
            receptor=_receptor_demo(),
            items=[Item("Producto", 1, 10000)],
        )
        xml = dte_a_xml(dte)
        root = etree.fromstring(xml)
        totales = root.find(
            f"{{{NS_SII}}}Documento/{{{NS_SII}}}Encabezado/{{{NS_SII}}}Totales"
        )
        assert totales.find(f"{{{NS_SII}}}VlrPagar") is None

    def test_item_exento_marca_indexe(self):
        dte = DTE(
            tipo=33,
            folio=1,
            fecha_emision="2026-04-29",
            emisor=_emisor_demo(),
            receptor=_receptor_demo(),
            items=[Item("Servicio", 1, 10000, exento=True)],
        )
        xml = dte_a_xml(dte)
        root = etree.fromstring(xml)
        det = root.find(f"{{{NS_SII}}}Documento/{{{NS_SII}}}Detalle")
        assert det.findtext(f"{{{NS_SII}}}IndExe") == "1"

    def test_referencia_set_boleta(self):
        """En boletas, referencia al SET solo lleva NroLinRef + CodRef + RazonRef."""
        dte = DTE(
            tipo=39,
            folio=1,
            fecha_emision="2026-04-29",
            emisor=_emisor_demo(),
            receptor=_receptor_boleta(),
            items=[Item("X", 1, 11900)],
            referencias=[Referencia(razon="CASO-1", codigo_referencia="SET")],
        )
        xml = dte_a_xml(dte)
        root = etree.fromstring(xml)
        ref = root.find(f"{{{NS_SII}}}Documento/{{{NS_SII}}}Referencia")
        assert ref.findtext(f"{{{NS_SII}}}CodRef") == "SET"
        assert ref.findtext(f"{{{NS_SII}}}RazonRef") == "CASO-1"
        # NO debe llevar TpoDocRef ni FolioRef ni FchRef
        assert ref.find(f"{{{NS_SII}}}TpoDocRef") is None
        assert ref.find(f"{{{NS_SII}}}FolioRef") is None
        assert ref.find(f"{{{NS_SII}}}FchRef") is None

    def test_referencia_set_factura(self):
        """En facturas, referencia al SET lleva TpoDocRef + FolioRef + FchRef + RazonRef."""
        dte = DTE(
            tipo=33,
            folio=1,
            fecha_emision="2026-04-29",
            emisor=_emisor_demo(),
            receptor=_receptor_demo(),
            items=[Item("X", 1, 10000)],
            referencias=[
                Referencia(
                    razon="CASO 123-1",
                    tipo_documento="SET",
                    folio_referencia=1,
                    fecha_referencia="2026-04-29",
                )
            ],
        )
        xml = dte_a_xml(dte)
        root = etree.fromstring(xml)
        ref = root.find(f"{{{NS_SII}}}Documento/{{{NS_SII}}}Referencia")
        assert ref.findtext(f"{{{NS_SII}}}TpoDocRef") == "SET"
        assert ref.findtext(f"{{{NS_SII}}}FolioRef") == "1"
        assert ref.findtext(f"{{{NS_SII}}}FchRef") == "2026-04-29"
        assert ref.findtext(f"{{{NS_SII}}}RazonRef") == "CASO 123-1"

    def test_escapa_caracteres_xml(self):
        dte = DTE(
            tipo=33,
            folio=1,
            fecha_emision="2026-04-29",
            emisor=_emisor_demo(),
            receptor=_receptor_demo(),
            items=[Item("M&M's <pack>", 1, 1000)],
        )
        xml = dte_a_xml(dte)
        # Debe parsear sin error
        root = etree.fromstring(xml)
        det = root.find(f"{{{NS_SII}}}Documento/{{{NS_SII}}}Detalle")
        assert det.findtext(f"{{{NS_SII}}}NmbItem") == "M&M's <pack>"


class TestEnvioWrappers:
    def _dte_xml_minimo(self, tipo: int = 33, folio: int = 1) -> bytes:
        dte = DTE(
            tipo=tipo,
            folio=folio,
            fecha_emision="2026-04-29",
            emisor=_emisor_demo(),
            receptor=_receptor_demo() if tipo == 33 else _receptor_boleta(),
            items=[Item("X", 1, 10000)],
        )
        return dte_a_xml(dte)

    def test_envio_dte_basico(self):
        d1 = self._dte_xml_minimo(33, 1)
        envio = envio_dte(
            [d1],
            rut_emisor="76123456-0",
            rut_envia="11111111-1",
            fch_resol="2026-04-28",
        )
        root = etree.fromstring(envio)
        assert root.tag == f"{{{NS_SII}}}EnvioDTE"
        caratula = root.find(f"{{{NS_SII}}}SetDTE/{{{NS_SII}}}Caratula")
        assert caratula.findtext(f"{{{NS_SII}}}RutEmisor") == "76123456-0"
        assert caratula.findtext(f"{{{NS_SII}}}RutReceptor") == "60803000-K"
        subtot = caratula.find(f"{{{NS_SII}}}SubTotDTE")
        assert subtot.findtext(f"{{{NS_SII}}}TpoDTE") == "33"
        assert subtot.findtext(f"{{{NS_SII}}}NroDTE") == "1"

    def test_envio_boleta(self):
        d1 = self._dte_xml_minimo(39, 1)
        d2 = self._dte_xml_minimo(39, 2)
        envio = envio_boleta(
            [d1, d2],
            rut_emisor="76123456-0",
            rut_envia="11111111-1",
            fch_resol="2026-04-28",
        )
        root = etree.fromstring(envio)
        assert root.tag == f"{{{NS_SII}}}EnvioBOLETA"
        subtot = root.find(
            f"{{{NS_SII}}}SetDTE/{{{NS_SII}}}Caratula/{{{NS_SII}}}SubTotDTE"
        )
        assert subtot.findtext(f"{{{NS_SII}}}TpoDTE") == "39"
        assert subtot.findtext(f"{{{NS_SII}}}NroDTE") == "2"

    def test_consumo_folios(self):
        rcof = consumo_folios(
            rut_emisor="76123456-0",
            rut_envia="11111111-1",
            fch_resol="2026-04-28",
            fecha="2026-04-29",
            tipo_dte=39,
            folio_inicial=1,
            folio_final=5,
            monto_neto=43831,
            monto_iva=8329,
            monto_exento=2000,
            monto_total=54160,
            folios_emitidos=5,
        )
        root = etree.fromstring(rcof)
        assert root.tag == f"{{{NS_SII}}}ConsumoFolios"
        resumen = root.find(f"{{{NS_SII}}}DocumentoConsumoFolios/{{{NS_SII}}}Resumen")
        assert resumen.findtext(f"{{{NS_SII}}}TipoDocumento") == "39"
        assert resumen.findtext(f"{{{NS_SII}}}MntTotal") == "54160"
        rango = resumen.find(f"{{{NS_SII}}}RangoUtilizados")
        assert rango.findtext(f"{{{NS_SII}}}Inicial") == "1"
        assert rango.findtext(f"{{{NS_SII}}}Final") == "5"

    def test_firmar_envio(self, pfx_demo):
        cert = Cert.from_pfx_bytes(pfx_demo["pfx_bytes"], pfx_demo["password"])
        d1 = self._dte_xml_minimo(33, 1)
        envio = envio_dte(
            [d1],
            rut_emisor="76123456-0",
            rut_envia="11111111-1",
            fch_resol="2026-04-28",
        )
        firmado = firmar_envio(envio, cert)
        root = etree.fromstring(firmado)
        # Tiene Signature como hijo del root
        sig = root.find("{http://www.w3.org/2000/09/xmldsig#}Signature")
        assert sig is not None
