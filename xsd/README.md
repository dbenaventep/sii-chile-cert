# XSDs oficiales del SII Chile

Esta carpeta originalmente no incluye archivos XSD para mantener el repo liviano y siempre apuntando a la **versión vigente del SII**. Los XSDs se descargan desde `sii.cl` cuando los necesites.

## ¿Dónde están los XSDs oficiales?

Página índice del SII: [https://www.sii.cl/servicios_online/3532-formato_xml-3811.html](https://www.sii.cl/servicios_online/3532-formato_xml-3811.html)

Los XSDs vienen empaquetados en ZIPs por familia de documento:

| ZIP | Contiene | Para qué |
|---|---|---|
| [`schema_dte.zip`](https://www.sii.cl/factura_electronica/factura_mercado/schema_dte.zip) | `EnvioDTE_v10.xsd`, `DTE_v10.xsd`, `SiiTypes_v10.xsd`, `xmldsignature_v10.xsd` | Documentos tributarios (T33, T34, T46, T52, T56, T61) |
| [`schema_envio_bol.zip`](https://www.sii.cl/factura_electronica/factura_mercado/schema_envio_bol.zip) | `EnvioBOLETA_v11.xsd` y referenciados | Boletas T39 / T41 |
| [`schema_iecv.zip`](https://www.sii.cl/factura_electronica/factura_mercado/schema_iecv.zip) | `LibroCV_v10.xsd` | Información Electrónica de Compras y Ventas (LCV) |
| [`schema_lgd.zip`](https://www.sii.cl/factura_electronica/factura_mercado/schema_lgd.zip) | `LibroGuia_v10.xsd` | Libro de Guías de Despacho |
| [`schema_libro_bol.zip`](https://www.sii.cl/factura_electronica/factura_mercado/schema_libro_bol.zip) | `LibroBOLETA_v10.xsd` | Libro de Boletas |
| [`schema_ic.zip`](https://www.sii.cl/factura_electronica/factura_mercado/schema_ic.zip) | `RespuestaEnvioDTE_v10.xsd`, `RespuestaDTE_v10.xsd` y otros | Intercambio entre contribuyentes |
| [`schema19983.zip`](https://www.sii.cl/factura_electronica/factura_mercado/schema19983.zip) | `EnvioRecibos_v10.xsd`, `Recibos_v10.xsd` | Recibo de mercaderías (Ley 19.983) |
| [`schema_resp.zip`](https://www.sii.cl/factura_electronica/factura_mercado/schema_resp.zip) | Respuesta SII a envíos automáticos | Validar XML de respuestas del SII |
| [`schema_resp_libros.zip`](https://www.sii.cl/factura_electronica/factura_mercado/schema_resp_libros.zip) | Respuesta SII a libros | Validar respuestas a libros |
| [`ConsumoFolio_v10.xsd`](https://www.sii.cl/factura_electronica/factura_mercado/ConsumoFolio_v10.xsd) | XSD directo (sin ZIP) | RCOF / RVD |

## Descargar todos con un script

Guarda esto como `xsd/download.sh` o ejecuta directo:

```bash
#!/bin/bash
# Descarga todos los XSDs oficiales del SII en xsd/
set -e
cd "$(dirname "$0")"
BASE="https://www.sii.cl/factura_electronica/factura_mercado"

for z in schema_dte schema_iecv schema_lgd schema_ic schema19983 schema_resp schema_resp_libros schema_envio_bol schema_libro_bol; do
  echo "→ $z.zip"
  curl -sLO "$BASE/$z.zip"
  unzip -oq "$z.zip"
  rm "$z.zip"
done

curl -sLO "$BASE/ConsumoFolio_v10.xsd"

echo "→ Listado de XSDs descargados:"
ls *.xsd | sort
```

```bash
chmod +x xsd/download.sh && bash xsd/download.sh
```

## ¿Por qué no committeamos los XSDs al repo?

1. **Pueden quedar desactualizados** — el SII a veces actualiza versiones (ej. nuevos campos en facturas 2026).
2. **Son archivos públicos** del SII — el repo solo debe agregar valor docs/scripts, no duplicar lo que ya está en sii.cl.
3. **Quien clona el repo siempre obtiene la versión vigente** ejecutando `download.sh`.

## Validar tu XML contra un XSD oficial

Con Python + `lxml`:

```python
from lxml import etree

xml_doc = etree.parse("mi_envio.xml")
xsd_doc = etree.parse("xsd/EnvioBOLETA_v11.xsd")
xmlschema = etree.XMLSchema(xsd_doc)

if xmlschema.validate(xml_doc):
    print("Válido")
else:
    for error in xmlschema.error_log:
        print(error.message, error.line)
```

Con `xmllint`:

```bash
xmllint --schema xsd/EnvioBOLETA_v11.xsd mi_envio.xml --noout
```

## Diferencias con XSDs de librerías open-source

Las librerías populares (dansanti, LibreDTE) incluyen sus propios XSDs locales. **Algunos están modificados o desactualizados** respecto a los oficiales del SII:

- dansanti `EnvioBOLETA_v11.xsd` agrega elementos `<TpoDocRef>`, `<FolioRef>`, `<FchRef>`, `<CodVndor>`, `<CodCaja>` en `<Referencia>` que NO están en el XSD oficial actual.

Si validas tu XML contra el XSD de una librería y queda OK, **valida también contra el oficial bajado de sii.cl** antes de enviar. Ver [`../docs/xsd-oficial-vs-dansanti.md`](../docs/xsd-oficial-vs-dansanti.md).
