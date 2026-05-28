"""CLI scripts del paquete siicl.

Comandos disponibles:
    siicl-emit-factura       Emite un DTE (factura, NC, ND, guía) desde JSON.
    siicl-emit-boleta        Emite una boleta T39/T41 desde JSON.
    siicl-upload             Sube un XML al SII (SOAP o REST).
    siicl-generar-pdf        Genera PDF de un DTE firmado.
    siicl-validar-xsd        Valida un XML contra XSD oficial.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def emit_factura():
    """CLI: emite una factura/NC/ND/guía desde JSON."""
    parser = argparse.ArgumentParser(description=emit_factura.__doc__)
    parser.add_argument("json_file", help="Archivo JSON con datos del DTE")
    parser.add_argument("--caf", required=True, help="Archivo CAF del SII")
    parser.add_argument("--pfx", required=True, help="Certificado .pfx")
    parser.add_argument("--password", required=True, help="Password del .pfx")
    parser.add_argument("--out", help="Archivo XML de salida")
    args = parser.parse_args()

    from siicl.caf import CAF
    from siicl.dte import DTE, Emisor, Item, Receptor, Referencia, dte_a_xml
    from siicl.firma import Cert, firmar_xml
    from siicl.timbre import DatosTED, construir_ted

    data = json.loads(Path(args.json_file).read_text())
    caf = CAF.from_file(args.caf)
    cert = Cert.from_pfx(args.pfx, args.password)

    emisor = Emisor(**data["emisor"])
    receptor = Receptor(**data["receptor"])
    items = [Item(**i) for i in data["items"]]
    refs = [Referencia(**r) for r in data.get("referencias", [])]

    dte = DTE(
        tipo=data["tipo"], folio=data["folio"],
        fecha_emision=data["fecha_emision"],
        emisor=emisor, receptor=receptor, items=items, referencias=refs,
        ind_servicio=data.get("ind_servicio"),
    )
    dte_xml = dte_a_xml(dte)

    # Generar TED
    primer_item = items[0].nombre if items else ""
    monto_total = data.get("monto_total")
    if monto_total is None:
        from siicl.dte import calcular_totales
        from siicl.types import es_boleta
        t = calcular_totales(items, boleta=es_boleta(data["tipo"]))
        monto_total = t["MntTotal"]

    ted_datos = DatosTED(
        rut_emisor=emisor.rut, tipo_dte=data["tipo"], folio=data["folio"],
        fecha_emision=data["fecha_emision"],
        rut_receptor=receptor.rut,
        razon_social_receptor=receptor.razon_social,
        monto_total=monto_total, nombre_item_1=primer_item,
    )
    ted = construir_ted(ted_datos, caf)

    # Insertar TED antes de cerrar </Documento>
    dte_str = dte_xml.decode("ISO-8859-1")
    ted_str = ted.decode("ISO-8859-1")
    dte_str = dte_str.replace("</Documento>", f"{ted_str}</Documento>")

    # Firmar
    doc_id = f"T{data['tipo']}F{data['folio']}"
    firmado = firmar_xml(dte_str, cert, reference_uri=f"#{doc_id}")

    out_path = args.out or f"DTE_T{data['tipo']}F{data['folio']}.xml"
    Path(out_path).write_text(
        '<?xml version="1.0" encoding="ISO-8859-1"?>\n' + firmado,
        encoding="ISO-8859-1",
    )
    print(f"DTE generado: {out_path}")


def emit_boleta():
    """Alias para emit_factura — boletas T39/T41 usan el mismo flujo."""
    emit_factura()


def upload():
    """CLI: sube un XML al SII."""
    parser = argparse.ArgumentParser(description=upload.__doc__)
    parser.add_argument("xml_file", help="Archivo XML a subir")
    parser.add_argument("--rut-emisor", required=True)
    parser.add_argument("--rut-envia", required=True)
    parser.add_argument("--pfx", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--ambiente", choices=["cert", "prod"], default="cert")
    parser.add_argument(
        "--canal",
        choices=["soap", "rest"],
        default="soap",
        help="soap = maullin/palena DTEUpload (default, sirve para todo cert). "
             "rest = pangal/rahue (SOLO boletas producción operativa)",
    )
    parser.add_argument("--filename", help="Nombre del archivo en multipart")
    args = parser.parse_args()

    from siicl.cliente import enviar_soap, obtener_semilla_rest, obtener_token_rest, upload_boleta_rest
    from siicl.firma import Cert

    cert = Cert.from_pfx(args.pfx, args.password)

    if args.canal == "soap":
        result = enviar_soap(
            args.xml_file,
            rut_emisor=args.rut_emisor,
            rut_envia=args.rut_envia,
            cert=cert,
            ambiente=args.ambiente,
            filename=args.filename,
        )
    else:
        semilla = obtener_semilla_rest(args.ambiente)
        token = obtener_token_rest(semilla, cert, args.ambiente)
        result = upload_boleta_rest(
            args.xml_file,
            rut_emisor=args.rut_emisor,
            rut_envia=args.rut_envia,
            token=token,
            ambiente=args.ambiente,
            filename=args.filename,
        )

    print(f"Status: {result.status}")
    print(f"Track ID: {result.track_id}")
    if not result.ok:
        print(f"\nRespuesta SII:\n{result.raw_response[:500]}", file=sys.stderr)
        sys.exit(2)


def generar_pdf():
    """CLI: genera PDF de un DTE firmado."""
    parser = argparse.ArgumentParser(description=generar_pdf.__doc__)
    parser.add_argument("dte_xml", help="Archivo XML del DTE firmado")
    parser.add_argument("--out", required=True, help="Archivo PDF de salida")
    parser.add_argument(
        "--cedible", action="store_true",
        help="Genera versión cedible (con acuse). Ignorado en boletas T39/T41.",
    )
    parser.add_argument(
        "--unidad-sii", default="SANTIAGO",
        help='Unidad SII a mostrar (ej "SANTIAGO ORIENTE")',
    )
    args = parser.parse_args()

    from siicl.pdf import datos_desde_dte_xml, render_pdf

    dte_xml = Path(args.dte_xml).read_bytes()
    # Extraer TED del XML
    from lxml import etree

    root = etree.fromstring(dte_xml)
    ted = root.find(".//{http://www.sii.cl/SiiDte}TED")
    if ted is None:
        print("Error: el DTE no tiene TED", file=sys.stderr)
        sys.exit(1)
    ted_bytes = etree.tostring(ted)

    datos = datos_desde_dte_xml(
        dte_xml, ted_bytes,
        cedible=args.cedible,
        unidad_sii=args.unidad_sii,
    )
    pdf = render_pdf(datos)
    Path(args.out).write_bytes(pdf)
    print(f"PDF generado: {args.out}")


def validar_xsd():
    """CLI: valida un XML contra el XSD oficial del SII."""
    parser = argparse.ArgumentParser(description=validar_xsd.__doc__)
    parser.add_argument("xml_file", help="XML a validar")
    parser.add_argument("--xsd", required=True, help="XSD oficial (descargar con --download primero)")
    args = parser.parse_args()

    from siicl.validacion import validar_xml

    errores = validar_xml(Path(args.xml_file).read_bytes(), args.xsd)
    if not errores:
        print("OK: XML válido")
    else:
        print(f"FALLA: {len(errores)} errores:")
        for e in errores:
            print(f"  - {e}")
        sys.exit(2)


if __name__ == "__main__":
    # Permite ejecutar python -m siicl.cli COMANDO ARGS
    if len(sys.argv) < 2:
        print("Uso: python -m siicl.cli {emit_factura|emit_boleta|upload|generar_pdf|validar_xsd} ARGS")
        sys.exit(1)
    comando = sys.argv.pop(1)
    sys.argv[0] = f"siicl-{comando}"
    funciones = {
        "emit_factura": emit_factura,
        "emit_boleta": emit_boleta,
        "upload": upload,
        "generar_pdf": generar_pdf,
        "validar_xsd": validar_xsd,
    }
    if comando not in funciones:
        print(f"Comando desconocido: {comando}")
        sys.exit(1)
    funciones[comando]()
