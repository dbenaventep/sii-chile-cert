#!/bin/bash
# Descarga todos los XSDs oficiales del SII Chile en esta carpeta.
# Uso: bash xsd/download.sh   (desde la raíz del repo)
set -e

cd "$(dirname "$0")"
BASE="https://www.sii.cl/factura_electronica/factura_mercado"

ZIPS=(schema_dte schema_iecv schema_lgd schema_ic schema19983
      schema_resp schema_resp_libros schema_envio_bol schema_libro_bol)

for z in "${ZIPS[@]}"; do
  echo "→ $z.zip"
  curl -sLO "$BASE/$z.zip"
  unzip -oq "$z.zip"
  rm "$z.zip"
done

echo "→ ConsumoFolio_v10.xsd (directo)"
curl -sLO "$BASE/ConsumoFolio_v10.xsd"

echo ""
echo "XSDs descargados:"
ls *.xsd | sort
echo ""
echo "Total: $(ls *.xsd | wc -l) archivos"
