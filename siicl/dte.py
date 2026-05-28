"""Construcción de documentos DTE y cálculo de totales.

Provee builders para DTE (factura, boleta, NC, ND, guía) que generan el XML
listo para firmar. Incluye cálculo automático de Neto, IVA, MntTotal.

El XML generado se valida contra el XSD oficial del SII; el módulo NO incluye
campos no oficiales (RUTProvSW en boletas, TpoDocRef/FolioRef/FchRef en
referencias de boletas, etc.) — ver docs/xsd-oficial-vs-dansanti.md.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO

from lxml import etree

from siicl.firma import Cert, firmar_xml
from siicl.types import RUT_SII, es_boleta

NS_SII = "http://www.sii.cl/SiiDte"


@dataclass
class Item:
    """Línea de detalle de un DTE."""

    nombre: str
    cantidad: float
    precio_unitario: float
    exento: bool = False
    unidad_medida: str | None = None  # ej. "Kg", "Hora"
    codigo: str | None = None  # CdgItem.VlrCodigo
    descuento_pct: float | None = None


@dataclass
class Emisor:
    rut: str
    razon_social: str
    giro: str
    direccion: str
    comuna: str
    ciudad: str
    actecos: list[int] = field(default_factory=list)
    correo: str | None = None
    telefono: str | None = None


@dataclass
class Receptor:
    rut: str
    razon_social: str
    giro: str | None = None
    direccion: str | None = None
    comuna: str | None = None
    ciudad: str | None = None


@dataclass
class Referencia:
    """Referencia a otro documento (set de prueba u otra factura)."""

    razon: str
    codigo_referencia: str | int | None = None  # CodRef: "SET" o 1/2/3
    tipo_documento: str | int | None = None  # TpoDocRef: 33, 39, "SET"
    folio_referencia: int | None = None
    fecha_referencia: str | None = None


@dataclass
class DTE:
    """Documento Tributario Electrónico listo para timbrar y enviar."""

    tipo: int
    folio: int
    fecha_emision: str
    emisor: Emisor
    receptor: Receptor
    items: list[Item]
    referencias: list[Referencia] = field(default_factory=list)
    ind_servicio: int | None = None  # obligatorio para boletas (1/2/3)


def calcular_totales(items: list[Item], iva_pct: float = 19.0, *, boleta: bool = False) -> dict:
    """Calcula MntNeto, MntExe, IVA y MntTotal según los ítems.

    Para boletas, los precios incluyen IVA. Para facturas, los precios son netos.
    """
    monto_exento = 0
    monto_afecto_bruto = 0  # con IVA si boleta, sin IVA si factura

    for item in items:
        qty = item.cantidad
        prc = item.precio_unitario
        subtotal = qty * prc
        if item.descuento_pct:
            subtotal = subtotal * (1 - item.descuento_pct / 100)

        if item.exento:
            monto_exento += round(subtotal)
        elif boleta:
            monto_afecto_bruto += round(subtotal)
        else:
            monto_afecto_bruto += round(subtotal)  # factura: neto directamente

    if boleta:
        # Precios incluyen IVA → calcular neto a partir del bruto
        neto = round(monto_afecto_bruto / (1 + iva_pct / 100))
        iva = monto_afecto_bruto - neto
    else:
        neto = monto_afecto_bruto
        iva = round(neto * iva_pct / 100)

    total = neto + iva + monto_exento

    return {
        "MntNeto": neto,
        "MntExe": monto_exento,
        "IVA": iva,
        "MntTotal": total,
    }


def dte_a_xml(dte: DTE, dte_id: str | None = None, iva_pct: float = 19.0) -> bytes:
    """Construye el XML <DTE> listo para incrustar TED y firmar.

    El XML NO incluye TED ni Signature (esos se agregan después con
    construir_ted() y firmar_xml()).

    Retorna bytes en ISO-8859-1.
    """
    boleta = es_boleta(dte.tipo)
    totales = calcular_totales(dte.items, iva_pct, boleta=boleta)
    doc_id = dte_id or f"T{dte.tipo}F{dte.folio}"

    out = StringIO()
    out.write(f'<DTE xmlns="{NS_SII}" version="1.0">\n')
    out.write(f'<Documento ID="{doc_id}">\n')

    # Encabezado
    out.write("<Encabezado>\n")
    out.write("<IdDoc>\n")
    out.write(f"<TipoDTE>{dte.tipo}</TipoDTE>\n")
    out.write(f"<Folio>{dte.folio}</Folio>\n")
    out.write(f"<FchEmis>{dte.fecha_emision}</FchEmis>\n")
    if boleta:
        ind = dte.ind_servicio if dte.ind_servicio is not None else 3
        out.write(f"<IndServicio>{ind}</IndServicio>\n")
    out.write("</IdDoc>\n")

    # Emisor
    out.write("<Emisor>\n")
    out.write(f"<RUTEmisor>{dte.emisor.rut}</RUTEmisor>\n")
    tag_rzn = "RznSocEmisor" if boleta else "RznSoc"
    tag_giro = "GiroEmisor" if boleta else "GiroEmis"
    out.write(f"<{tag_rzn}>{_esc(dte.emisor.razon_social)}</{tag_rzn}>\n")
    out.write(f"<{tag_giro}>{_esc(dte.emisor.giro)}</{tag_giro}>\n")
    if not boleta:
        for act in dte.emisor.actecos:
            out.write(f"<Acteco>{act}</Acteco>\n")
    out.write(f"<DirOrigen>{_esc(dte.emisor.direccion)}</DirOrigen>\n")
    out.write(f"<CmnaOrigen>{_esc(dte.emisor.comuna)}</CmnaOrigen>\n")
    out.write(f"<CiudadOrigen>{_esc(dte.emisor.ciudad)}</CiudadOrigen>\n")
    out.write("</Emisor>\n")

    # Receptor
    out.write("<Receptor>\n")
    out.write(f"<RUTRecep>{dte.receptor.rut}</RUTRecep>\n")
    out.write(f"<RznSocRecep>{_esc(dte.receptor.razon_social)}</RznSocRecep>\n")
    if dte.receptor.giro:
        out.write(f"<GiroRecep>{_esc(dte.receptor.giro)}</GiroRecep>\n")
    if dte.receptor.direccion:
        out.write(f"<DirRecep>{_esc(dte.receptor.direccion)}</DirRecep>\n")
    if dte.receptor.comuna:
        out.write(f"<CmnaRecep>{_esc(dte.receptor.comuna)}</CmnaRecep>\n")
    if dte.receptor.ciudad:
        out.write(f"<CiudadRecep>{_esc(dte.receptor.ciudad)}</CiudadRecep>\n")
    out.write("</Receptor>\n")

    # Totales
    out.write("<Totales>\n")
    out.write(f"<MntNeto>{totales['MntNeto']}</MntNeto>\n")
    if totales["MntExe"] > 0:
        out.write(f"<MntExe>{totales['MntExe']}</MntExe>\n")
    out.write(f"<IVA>{totales['IVA']}</IVA>\n")
    out.write(f"<MntTotal>{totales['MntTotal']}</MntTotal>\n")
    if boleta:
        out.write(f"<VlrPagar>{totales['MntTotal']}</VlrPagar>\n")
    out.write("</Totales>\n")
    out.write("</Encabezado>\n")

    # Detalle
    for i, item in enumerate(dte.items, 1):
        out.write("<Detalle>\n")
        out.write(f"<NroLinDet>{i}</NroLinDet>\n")
        if item.codigo:
            out.write(
                "<CdgItem>"
                "<TpoCodigo>INT1</TpoCodigo>"
                f"<VlrCodigo>{_esc(item.codigo)}</VlrCodigo>"
                "</CdgItem>\n"
            )
        if item.exento:
            out.write("<IndExe>1</IndExe>\n")
        out.write(f"<NmbItem>{_esc(item.nombre)}</NmbItem>\n")
        out.write(f"<QtyItem>{item.cantidad}</QtyItem>\n")
        if item.unidad_medida:
            out.write(f"<UnmdItem>{_esc(item.unidad_medida)}</UnmdItem>\n")
        out.write(f"<PrcItem>{item.precio_unitario}</PrcItem>\n")
        if item.descuento_pct:
            out.write(f"<DescuentoPct>{item.descuento_pct}</DescuentoPct>\n")
        monto_item = round(item.cantidad * item.precio_unitario)
        if item.descuento_pct:
            monto_item = round(monto_item * (1 - item.descuento_pct / 100))
        out.write(f"<MontoItem>{monto_item}</MontoItem>\n")
        out.write("</Detalle>\n")

    # Referencia
    for n, ref in enumerate(dte.referencias, 1):
        out.write("<Referencia>\n")
        out.write(f"<NroLinRef>{n}</NroLinRef>\n")
        # Para boletas SOLO NroLinRef + CodRef + RazonRef (XSD oficial)
        if boleta:
            if ref.codigo_referencia is not None:
                out.write(f"<CodRef>{ref.codigo_referencia}</CodRef>\n")
            out.write(f"<RazonRef>{_esc(ref.razon)}</RazonRef>\n")
        else:
            if ref.tipo_documento is not None:
                out.write(f"<TpoDocRef>{ref.tipo_documento}</TpoDocRef>\n")
            if ref.folio_referencia is not None:
                out.write(f"<FolioRef>{ref.folio_referencia}</FolioRef>\n")
            fch = ref.fecha_referencia or dte.fecha_emision
            out.write(f"<FchRef>{fch}</FchRef>\n")
            if ref.codigo_referencia is not None:
                out.write(f"<CodRef>{ref.codigo_referencia}</CodRef>\n")
            out.write(f"<RazonRef>{_esc(ref.razon)}</RazonRef>\n")
        out.write("</Referencia>\n")

    # TmstFirma (se completa al firmar; placeholder)
    out.write(f"<TmstFirma>{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}</TmstFirma>\n")
    out.write("</Documento>\n</DTE>")

    return out.getvalue().encode("ISO-8859-1")


def _esc(s: str) -> str:
    """Escape XML mínimo."""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def envio_dte(
    dtes: Iterable[bytes],
    *,
    rut_emisor: str,
    rut_envia: str,
    fch_resol: str,
    nro_resol: int = 0,
    rut_receptor: str = RUT_SII,
    set_dte_id: str = "SetDoc",
) -> bytes:
    """Construye el wrapper <EnvioDTE> con uno o más DTEs ya firmados.

    Para boletas usar envio_boleta(). Para RCOF usar consumo_folios().
    """
    return _envio_wrapper(
        dtes,
        wrapper_tag="EnvioDTE",
        schema_loc="EnvioDTE_v10.xsd",
        rut_emisor=rut_emisor,
        rut_envia=rut_envia,
        rut_receptor=rut_receptor,
        fch_resol=fch_resol,
        nro_resol=nro_resol,
        set_dte_id=set_dte_id,
    )


def envio_boleta(
    dtes: Iterable[bytes],
    *,
    rut_emisor: str,
    rut_envia: str,
    fch_resol: str,
    nro_resol: int = 0,
    rut_receptor: str = RUT_SII,
    set_dte_id: str = "SetDoc",
) -> bytes:
    """Construye el wrapper <EnvioBOLETA> con boletas T39/T41 ya firmadas."""
    return _envio_wrapper(
        dtes,
        wrapper_tag="EnvioBOLETA",
        schema_loc="EnvioBOLETA_v11.xsd",
        rut_emisor=rut_emisor,
        rut_envia=rut_envia,
        rut_receptor=rut_receptor,
        fch_resol=fch_resol,
        nro_resol=nro_resol,
        set_dte_id=set_dte_id,
    )


def _envio_wrapper(
    dtes: Iterable[bytes],
    *,
    wrapper_tag: str,
    schema_loc: str,
    rut_emisor: str,
    rut_envia: str,
    rut_receptor: str,
    fch_resol: str,
    nro_resol: int,
    set_dte_id: str,
) -> bytes:
    """Helper interno para construir el wrapper de envío."""
    dtes_list = list(dtes)

    # Contar SubTotDTE
    subtotales: dict[int, int] = {}
    for dte_xml in dtes_list:
        root = etree.fromstring(dte_xml)
        tipo = int(root.findtext(f"{{{NS_SII}}}Documento/{{{NS_SII}}}Encabezado/{{{NS_SII}}}IdDoc/{{{NS_SII}}}TipoDTE"))
        subtotales[tipo] = subtotales.get(tipo, 0) + 1

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    out = StringIO()
    out.write('<?xml version="1.0" encoding="ISO-8859-1"?>\n')
    out.write(
        f'<{wrapper_tag} xmlns="{NS_SII}" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        f'xsi:schemaLocation="{NS_SII} {schema_loc}" version="1.0">\n'
    )
    out.write(f'<SetDTE ID="{set_dte_id}">\n')
    out.write('<Caratula version="1.0">\n')
    out.write(f'<RutEmisor>{rut_emisor}</RutEmisor>\n')
    out.write(f'<RutEnvia>{rut_envia}</RutEnvia>\n')
    out.write(f'<RutReceptor>{rut_receptor}</RutReceptor>\n')
    out.write(f'<FchResol>{fch_resol}</FchResol>\n')
    out.write(f'<NroResol>{nro_resol}</NroResol>\n')
    out.write(f'<TmstFirmaEnv>{timestamp}</TmstFirmaEnv>\n')
    for tipo in sorted(subtotales):
        out.write(
            f'<SubTotDTE><TpoDTE>{tipo}</TpoDTE>'
            f'<NroDTE>{subtotales[tipo]}</NroDTE></SubTotDTE>\n'
        )
    out.write('</Caratula>\n')

    # Insertar cada DTE
    for dte_xml in dtes_list:
        # quitar XML declaration si la tiene
        xml_str = dte_xml.decode("ISO-8859-1")
        if xml_str.startswith("<?xml"):
            xml_str = xml_str.split("?>", 1)[1].lstrip()
        out.write(xml_str)
        out.write("\n")

    out.write(f'</SetDTE>\n</{wrapper_tag}>')

    return out.getvalue().encode("ISO-8859-1")


def consumo_folios(
    *,
    rut_emisor: str,
    rut_envia: str,
    fch_resol: str,
    nro_resol: int = 0,
    fecha: str,
    tipo_dte: int,
    folio_inicial: int,
    folio_final: int,
    monto_neto: int,
    monto_iva: int,
    monto_exento: int,
    monto_total: int,
    folios_emitidos: int,
    sec_envio: int = 1,
    correlativo: int = 1,
) -> bytes:
    """Construye el XML <ConsumoFolios> para RCOF/RVD."""
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    folios_utilizados = folios_emitidos  # no contamos anulados acá
    tasa_iva = 19

    out = StringIO()
    out.write('<?xml version="1.0" encoding="ISO-8859-1"?>\n')
    out.write(
        f'<ConsumoFolios xmlns="{NS_SII}" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        f'xsi:schemaLocation="{NS_SII} ConsumoFolio_v10.xsd" version="1.0">\n'
    )
    out.write('<DocumentoConsumoFolios ID="SetDoc">\n')
    out.write('<Caratula version="1.0">\n')
    out.write(f'<RutEmisor>{rut_emisor}</RutEmisor>\n')
    out.write(f'<RutEnvia>{rut_envia}</RutEnvia>\n')
    out.write(f'<FchResol>{fch_resol}</FchResol>\n')
    out.write(f'<NroResol>{nro_resol}</NroResol>\n')
    out.write(f'<FchInicio>{fecha}</FchInicio>\n')
    out.write(f'<FchFinal>{fecha}</FchFinal>\n')
    out.write(f'<Correlativo>{correlativo}</Correlativo>\n')
    out.write(f'<SecEnvio>{sec_envio}</SecEnvio>\n')
    out.write(f'<TmstFirmaEnv>{timestamp}</TmstFirmaEnv>\n')
    out.write('</Caratula>\n')
    out.write('<Resumen>\n')
    out.write(f'<TipoDocumento>{tipo_dte}</TipoDocumento>\n')
    out.write(f'<MntNeto>{monto_neto}</MntNeto>\n')
    out.write(f'<MntIva>{monto_iva}</MntIva>\n')
    out.write(f'<TasaIVA>{tasa_iva}</TasaIVA>\n')
    out.write(f'<MntExento>{monto_exento}</MntExento>\n')
    out.write(f'<MntTotal>{monto_total}</MntTotal>\n')
    out.write(f'<FoliosEmitidos>{folios_emitidos}</FoliosEmitidos>\n')
    out.write('<FoliosAnulados>0</FoliosAnulados>\n')
    out.write(f'<FoliosUtilizados>{folios_utilizados}</FoliosUtilizados>\n')
    out.write('<RangoUtilizados>\n')
    out.write(f'<Inicial>{folio_inicial}</Inicial>\n')
    out.write(f'<Final>{folio_final}</Final>\n')
    out.write('</RangoUtilizados>\n')
    out.write('</Resumen>\n')
    out.write('</DocumentoConsumoFolios>\n')
    out.write('</ConsumoFolios>')

    return out.getvalue().encode("ISO-8859-1")


def firmar_envio(envio_xml: bytes, cert: Cert, set_dte_id: str = "SetDoc") -> bytes:
    """Firma un envío (EnvioDTE, EnvioBOLETA o ConsumoFolios) con XMLDSig.

    La firma referencia el ID del SetDTE/DocumentoConsumoFolios.
    """
    # Quitar XML decl para firmar (firma se aplica sobre el doc root)
    xml_str = envio_xml.decode("ISO-8859-1")
    if xml_str.startswith("<?xml"):
        xml_str = xml_str.split("?>", 1)[1].lstrip()

    firmado = firmar_xml(xml_str, cert, reference_uri=f"#{set_dte_id}")
    return ('<?xml version="1.0" encoding="ISO-8859-1"?>\n' + firmado).encode("ISO-8859-1")
