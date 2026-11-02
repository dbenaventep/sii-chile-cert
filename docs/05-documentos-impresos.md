# 5. Documentos Impresos (PDF con timbre PDF417)

Cuarta etapa: el SII te pide los PDFs impresos de:

- Todos los DTE del Set de Pruebas (etapa 2)
- Una muestra de cada tipo de DTE de la Simulación (etapa 3)

Para los tipos que admiten cedible (T33, T34, T46, T52), debes generar **dos PDFs**: el tributario y el cedible.

Los PDFs se suben al portal SII y se revisan manualmente (no automático). Puede tardar 24-72 horas.

## Lo que el SII exige

El SII revisa la representación impresa y sus elementos electrónicos, incluidos TED, CAF y timbre. Las instrucciones concretas de revisión del portal prevalecen para cada proceso. La página oficial de esquemas XML no es por sí sola una especificación completa del diseño de PDF ni prueba la aprobación de una muestra.

### Recuadro SII (esquina superior derecha)

```
R.U.T.: 76123456-0
FACTURA ELECTRONICA
N° 32
```

- **Todo en rojo** (no negro)
- En recuadro con borde
- Debajo del recuadro (fuera): `S.I.I. - SANTIAGO ORIENTE` también en rojo (la unidad SII corresponde al domicilio del contribuyente)

### Cuadro de totales

- Neto, Exento, IVA, MONTO TOTAL — apilados verticalmente con borde
- Esquina inferior derecha
- NO en 2 columnas

### Datos receptor visibles

- Razón social, RUT, giro, dirección, comuna, ciudad
- Fecha de emisión visible
- Forma de pago

### Timbre PDF417

- Centrado horizontalmente
- Ancho ~60mm
- NO tapar leyenda inferior "Timbre electrónico S.I.I."

### Acuse de recibo (solo en cedible)

Bloque con campos para llenar a mano: Nombre, RUT, Firma, Fecha, Recinto. Más una declaración legal estándar (Ley 19.983).

### Leyenda cedible

- **T33, T34, T46**: `CEDIBLE` (mayúsculas, esquina inferior derecha, rojo, sin recuadro, fuente pequeña)
- **T52 (guía despacho)**: `CEDIBLE CON SU FACTURA` (mayúsculas)

## PDF417 técnico — el detalle más doloroso

El timbre PDF417 codifica el TED (Timbre Electrónico DTE) — un XML con datos del DTE + firma RSA del SII. Si el código de barras no se escanea correctamente, el SII rechaza con "Timbre ilegible" o "Firma TED inválida".

### Reglas absolutas

```python
codes = pdf417_encode(
    ted_clean,
    columns=14,
    security_level=5,           # ⚠️ máximo, no probar otros
    encoding="iso-8859-1",      # ⚠️ NO utf-8 (rompe firma)
    numeric_compaction=False    # ⚠️ forzar byte compaction
)
img = render_image(codes, scale=4, ratio=3, padding=10)
# ⚠️ PNG raster, NO SVG
buf = io.BytesIO()
img.save(buf, format="PNG")
b64 = base64.b64encode(buf.getvalue()).decode()
html = f'<img src="data:image/png;base64,{b64}" style="width:60mm; margin:0 auto 3mm" />'
```

### Por qué cada regla

1. **`encoding="iso-8859-1"`**: el TED contiene caracteres como `Ó` (0xD3 en ISO-8859-1). Si se codifica UTF-8 (0xC3 0x93), los bytes son distintos y la firma RSA falla al escanear. El SII espera ISO-8859-1 estricto.

2. **`security_level=5`**: máximo nivel de corrección de errores. Manual SII lo exige.

3. **`numeric_compaction=False`**: fuerza byte compaction. La numeric compaction es más eficiente pero rompe los bytes del TED.

4. **PNG raster vs SVG**: WeasyPrint pierde resolución al embeber SVG. El escáner del SII ve líneas borrosas y falla.

## Template HTML/CSS recomendado

Estructura básica:

```html
<div class="content">
  <div class="header">
    <div id="info_proveedor">
      <dt class="strong">{{ razon_social }}</dt>
      <dt>{{ giro }}</dt>
      <dt>{{ direccion }}, {{ comuna }} - {{ ciudad }}</dt>
    </div>
    <div class="info_sii_wrap">
      <dl class="recuadro_sii">
        <dt class="rojo strong">R.U.T.: {{ rut }}</dt>
        <dt class="rojo strong">{{ tipo_dte_palabras }}</dt>
        <dt class="rojo strong">Nº {{ folio }}</dt>
      </dl>
      <div class="unidad_sii">S.I.I. - {{ unidad_sii }}</div>
    </div>
  </div>

  <!-- bloque receptor -->
  <!-- bloque ítems -->
</div>

<div id="total">
  <div id="total_bar">SON <span>{{ monto_total_palabras }}</span></div>
  <div id="bottom_area">
    <div id="barcode_block">
      <div id="imagen-svg">{{ pdf417_img | safe }}</div>
      <div class="barcode-legend">
        <div>Timbre electrónico S.I.I.</div>
        <div>Verifique documento en: {{ verificacion_url }}</div>
      </div>
    </div>
    <div id="totals_block">
      <div class="row"><span>Neto:</span><span>{{ neto | clp }}</span></div>
      <div class="row"><span>Exento:</span><span>{{ exento | clp }}</span></div>
      <div class="row">
        <span>19% I.V.A.:</span><span>{{ iva | clp }}</span>
      </div>
      <div class="row total-final">
        <span>MONTO TOTAL:</span><span>{{ total | clp }}</span>
      </div>
    </div>
  </div>
</div>

{% if cedible %}
<div class="acuse_recibo">
  <div class="acuse_titulo">ACUSE DE RECIBO</div>
  <table>
    <tr>
      <td>Nombre:</td>
      <td></td>
      <td>RUT:</td>
      <td></td>
    </tr>
    <tr>
      <td>Firma:</td>
      <td></td>
      <td>Fecha:</td>
      <td></td>
    </tr>
    <tr>
      <td>Recinto:</td>
      <td colspan="3"></td>
    </tr>
  </table>
  <div class="acuse_legal">
    El acuse de recibo que se declara en este acto, de acuerdo a lo dispuesto en
    la letra b) del Art. 4°, y la letra c) del Art. 5° de la Ley 19.983,
    acredita que la entrega de mercaderías o servicio(s) prestado(s) ha(n) sido
    recibido(s).
  </div>
</div>
<div class="cedible_label">
  {% if tipo_dte == 52 %}CEDIBLE CON SU FACTURA{% else %}CEDIBLE{% endif %}
</div>
{% endif %}
```

CSS clave:

```css
.rojo {
  color: #d32f2f !important;
}
.recuadro_sii {
  border: 2px solid #d32f2f;
  padding: 5mm;
}
.unidad_sii {
  color: #d32f2f;
  text-align: center;
  margin-top: 2mm;
}

#barcode_block {
  display: flex;
  flex-direction: column;
  align-items: center;
}
#imagen-svg {
  width: 60mm;
  margin: 0 auto 3mm;
}

#totals_block {
  width: 50%;
}
#totals_block .row {
  display: flex;
  justify-content: space-between;
}
.total-final {
  border-top: 1px solid #000;
  padding-top: 1mm;
  font-weight: bold;
}

.cedible_label {
  position: fixed;
  bottom: 4mm;
  right: 6mm;
  font-size: 9pt;
  color: #d32f2f;
  /* sin recuadro, sin background */
}

@page {
  size: letter;
  margin: 10mm;
}
```

## Boletas T39

A diferencia de facturas, las boletas:

- **NO llevan cedible** (no se ceden por Ley 19.983)
- **NO llevan acuse de recibo**
- Solo se genera **un PDF tributario por boleta**

El resto de las reglas (PDF417, recuadro SII, totales) son idénticas.

## Subida al portal SII

Portal SII → Certificación → "Subir Documentos Impresos". Selecciona la opción correspondiente:

- "Set de Pruebas" — sube los PDFs del set (T33, T61, T56, T34, T52, T46)
- "Simulación" — sube los PDFs de muestra
- "Boletas" — sube las boletas

El SII revisa manualmente y responde por correo: "Aprobada las muestras impresas RUT:... REVISION:N Aprobada".

## Errores típicos

- ❌ PDF417 codificado como UTF-8 → "TED Firma inválida"
- ❌ PDF417 como SVG → "Timbre ilegible"
- ❌ PDF417 con `security_level` bajo → "Timbre ilegible"
- ❌ PDF417 con numeric compaction → "RR must be terminated"
- ❌ Cedible en minúsculas ("Cedible con su factura") → rechazado, debe ser mayúsculas
- ❌ Acuse de recibo en página separada del documento → rechazado, debe ser 1 página total
- ❌ T52 con "CEDIBLE" en vez de "CEDIBLE CON SU FACTURA" → rechazado
- ❌ Boletas con cedible/acuse → rechazado, las boletas NO llevan eso
