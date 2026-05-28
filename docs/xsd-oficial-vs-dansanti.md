# XSD oficial del SII vs XSDs de librerías open-source

Las librerías open-source (dansanti `facturacion_electronica`, LibreDTE, etc.) incluyen sus propios archivos XSD locales. **No siempre coinciden con los XSDs oficiales del SII**. Esto puede causar:

- Tu XML pasa validación local pero el SII lo rechaza
- Tu XML falla validación local pero el SII lo aceptaría
- Campos que la librería genera silenciosamente no son aceptados por el SII

Este doc resume las diferencias detectadas durante un proceso de certificación real en 2026, contra `dansanti/facturacion_electronica` v0.21.2.

## Cómo identificar el XSD que usa tu librería

```bash
# dansanti
.venv/bin/python -c "import facturacion_electronica; import os; print(os.path.dirname(facturacion_electronica.__file__) + '/xsd/')"
# → /path/to/.venv/lib/python3.x/site-packages/facturacion_electronica/xsd/
```

## Cómo comparar contra el oficial

```bash
# Bajar el oficial
curl -L -o /tmp/EnvioBOLETA_oficial.xsd \
  "https://www.sii.cl/factura_electronica/EnvioBOLETA_v11.xsd"

# Diff
diff /tmp/EnvioBOLETA_oficial.xsd \
     .venv/lib/python3.x/site-packages/facturacion_electronica/xsd/EnvioBOLETA_v11.xsd
```

## Diferencias detectadas

### `EnvioBOLETA_v11.xsd` — Boletas T39 / T41

**XSD oficial (sii.cl):** define en `<Referencia>` solo:
```xml
<element name="NroLinRef">
<element name="CodRef" minOccurs="0">  <!-- xs:string maxLength 18 -->
<element name="RazonRef" minOccurs="0"> <!-- xs:string maxLength 90 -->
```

**XSD de dansanti** agrega elementos que NO están en el oficial:
- `<TpoDocRef>` (string maxLength 3)
- `<FolioRef>` (string maxLength 18)
- `<FchRef>` (date)
- `<CodVndor>` (string maxLength 9)
- `<CodCaja>` (string maxLength 5)

**Consecuencia:** dansanti permite (y a veces fuerza) que la `<Referencia>` lleve estos campos en boletas. **El SII los rechaza al recibir el envío** con error `HED-3-211 Dato invalido`.

**Otro hallazgo:** el XSD oficial **NO tiene** elemento `<RUTProvSW>` en boletas (sí en facturas T33 desde 2026). dansanti tiene código (en docstring, ver bug 1 en [`bugs-dansanti-patches.md`](bugs-dansanti-patches.md)) que lo agregaría — bueno que esté desactivado, mantenerlo así para boletas.

### Diferencias `ConsumoFolio_v10.xsd` — RCOF / RVD

El oficial y el de dansanti coinciden en este caso. No hay diferencias significativas.

### Diferencias `EnvioDTE_v10.xsd` — Facturas

Este archivo se distribuye en `schema_dte.zip` del SII (no como URL directa). Comparar requiere bajar el ZIP y extraerlo. En general, dansanti está alineado con el oficial para facturas (más antiguas, más maduras), pero verificar si certificas con campos nuevos de 2026 (Transporte, GeoRefEmision, ManejoMadera, etc.) — esos pueden estar en el oficial vigente pero no en versiones antiguas de dansanti.

## Validación dual recomendada

Antes de cada envío:

```python
from lxml import etree

def validar(xml_path, xsd_oficial, xsd_libreria):
    xml = etree.parse(xml_path)
    for nombre, xsd_path in [("oficial", xsd_oficial), ("librería", xsd_libreria)]:
        xsd = etree.XMLSchema(etree.parse(xsd_path))
        ok = xsd.validate(xml)
        print(f"{nombre}: {'OK' if ok else 'FALLA'}")
        if not ok:
            for e in xsd.error_log:
                print(f"  {e.message} (línea {e.line})")
```

- Si pasa OFICIAL pero falla LIBRERIA: tu librería tiene restricciones inventadas. Patchea o usa `verify=False`.
- Si pasa LIBRERIA pero falla OFICIAL: estás agregando campos que el SII no espera. Quitar.
- Pasa ambos: enviar.

## Cómo reportar discrepancias upstream

Si encontrás un XSD de tu librería desactualizado respecto al oficial:

1. Bajá el oficial de `sii.cl`.
2. Hacé el diff.
3. Abrí un issue en el repo de la librería con el diff.
4. Si tenés tiempo, PR con los XSDs actualizados.

Es el tipo de aporte que beneficia a toda la comunidad chilena.
