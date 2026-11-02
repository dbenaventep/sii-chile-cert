# Gotchas, errores raros y sus causas reales

Esta es la lista que hubiera ahorrado días si la hubiera tenido antes de empezar.

## "RUT No Autorizado a Firmar Documentos Electrónicos" al enviar el set

**Síntoma:** envías el set y a los minutos llega un correo del SII con asunto similar a _"RUT No Autorizado a Firmar Documentos Electrónicos"_. El envío no queda asociado al set.

**Causa real:** el RUT de la persona dueña del certificado digital (el firmante) no está habilitado en el portal del SII como "usuario autorizado a firmar DTE" para esa empresa. Tener el `.pfx` no es suficiente: el SII mantiene una lista por empresa de RUTs habilitados como firmantes.

**Solución:** el representante legal de la empresa entra a `sii.cl` y va a `Mi SII → Servicios online → Factura electrónica → Sistema de facturación gratuito del SII → Administración de usuarios → Agregar usuario autorizado` y agrega el RUT de la persona dueña del certificado con permiso "Firmar Documentos Tributarios Electrónicos". Ver [`docs/01-setup-emisor.md` §1.3](01-setup-emisor.md#13-autorizar-al-rut-del-firmante-ante-el-sii).

**Casos típicos donde se olvida:**

- El cert lo emitió un contador o integrador externo, y nunca lo registraron como firmante.
- La empresa tiene varios RUTs (holding) y se habilitó al firmante en uno solo.
- El firmante es el mismo representante legal y se asume que está habilitado por defecto — a veces no lo está y hay que activarlo explícitamente.

## "El Documento no esta en el envio" en revisión del set (boletas T39)

**Síntoma:** envías el set, recibes `EPR` (envío aceptado), pero al ingresar el track en la pantalla de revisión del set en el portal del SII te aparece:

```
Estado del Set: SRH - SET DE PRUEBA RECHAZADO

CASO-1     00     0     El Documento no esta en el envio
CASO-2     00     0     El Documento no esta en el envio
...
```

**Causa más común:** estás enviando el set por el endpoint REST nuevo (`pangal.sii.cl`) en lugar del SOAP clásico (`maullin.sii.cl`). El endpoint REST es solo para producción operativa, no para certificación.

**Solución:** envía el mismo `<EnvioBOLETA>` por SOAP a `maullin.sii.cl/cgi_dte/UPL/DTEUpload`. Es el mismo endpoint que se usa para facturas y libros.

**Otras causas posibles (descartar en orden):**

- Tu XML incluye campos no oficiales (`<FchRef>` en boletas). Quítalos.
- La referencia tiene campos extra. Para boletas debe ser solo `<NroLinRef> + <CodRef>SET</CodRef> + <RazonRef>CASO-N</RazonRef>`.
- El set ID quedó congelado tras varios rechazos. En este caso, la pantalla siempre devuelve el primer rechazo. Solo se libera reiniciando el proceso de cert de boletas (no pidiendo CAFs nuevos — eso no resetea el set).

## "SCH-00001: Invalid Schema Name" al enviar RCOF / RVD

**Síntoma:** mandas un ConsumoFolios y el SII responde HTTP 400 con `<STATUS>7</STATUS>` y `<ERROR>SCH-00001: Invalid Schema Name</ERROR>`. La primera vez en el día sí pasó, ahora rechaza.

**Causa real:** el SII usa el filename del multipart como clave de deduplicación. Si ya hay un envío aceptado con ese filename (ej. `CF_2026-05-27`), el siguiente con el mismo nombre se rechaza. El mensaje sobre "Schema Name" es engañoso.

**Solución:** varía el filename. Ej. copia el XML a `/tmp/CF_<rut>_<fecha>_v2.xml` y manda con ese nombre.

## "HED-3-211: ERROR Dato invalido" al enviar boletas por maullin SOAP

**Síntoma:** intentas mandar un `<EnvioBOLETA>` por maullin SOAP y el SII rechaza con `HED-3-211: Dato invalido` para cada DTE.

**Causa real:** tu XML incluye campos que no están en el XSD oficial de boletas. Los más comunes son:

-  `<FchRef>` dentro de `<Referencia>`

**Solución:** quitar esos campos del XML. Las librerías como dansanti los agregan automáticamente porque tienen un XSD local extendido con campos no oficiales. Hay que parchar la librería.

## Folios consumidos sin uso real

**Síntoma:** mandas un set, el SII lo rechaza, intentas reenviar la misma boleta con el mismo folio y rechaza con "folio duplicado".

**Causa:** el SII considera consumido cualquier folio que llegó en un envío aceptado, incluso si el set fue rechazado en una etapa posterior. **No se reciclan folios**.

**Solución:** usar siempre el siguiente folio libre del CAF. Si te quedas sin folios, pide CAF nuevo (no es lo mismo que pedir set nuevo — son trámites distintos).

## PDF417 ilegible cuando el SII lo escanea

**Síntomas:**

- "El Timbre es ilegible"
- "Ha habido alguna alteración en el CAF entregado por el SII"
- "TED - Firma invalida"

**Causas y sus soluciones:**

1. **TED codificado en UTF-8 en lugar de ISO-8859-1.** El TED contiene caracteres no-ASCII (`Ó`, `Ñ`, etc.) que el SII espera en ISO-8859-1. Si lo codificas UTF-8, los bytes cambian y la firma falla al escanear.

   ```python
   codes = pdf417_encode(ted_clean, encoding="iso-8859-1", ...)
   ```

2. **PDF417 renderizado como SVG en vez de PNG raster.** WeasyPrint y otros renderers pierden resolución al embebir SVG; el escáner del SII ve líneas borrosas y falla.

   ```python
   img = render_image(codes, scale=4, ratio=3, padding=10)  # PNG raster
   ```

3. **Byte compaction roto.** Si la librería pdf417 usa numeric compaction por defecto, los bytes binarios del TED se interpretan mal.

   ```python
   pdf417_encode(..., numeric_compaction=False)
   ```

4. **Security level bajo.** El SII requiere security_level=5 (máximo).

## PDF417 visualmente descentrado o tapando el texto

**Síntomas:** el SII rechaza con observación sobre el timbre tapando la leyenda.

**Solución CSS:**

```css
#barcode_block {
  align-items: center;
}
#imagen-svg {
  width: 60mm;
  margin: 0 auto 3mm;
}
```

## "CEDIBLE" en minúsculas o "Cedible con su factura" mal puesto

**Síntomas:** documento impreso aprobado pero observado por texto del cedible.

**Solución:**

- Para T33, T34, T46: leyenda `CEDIBLE` (mayúsculas, sin recuadro, esquina inferior derecha, rojo)
- Para T52 (guía de despacho): leyenda `CEDIBLE CON SU FACTURA` (mayúsculas)

## Intercambio: RUTRecep en recibo de mercaderías

**Síntoma:** rechazado el archivo de recepción de mercaderías.

**Causa común:** se puso el RUT propio en `<Receptor><RUTRecep>` del recibo. Debe ser el **RUT del emisor original** (el de quien te mandó el DTE, no tuyo).

## Intercambio: MntTotal = 0

**Síntoma:** rechazado con observación de monto incorrecto.

**Causa:** dansanti por defecto pone `<MntTotal>0</MntTotal>` en algunos casos. Forzar el valor real:

```python
"Encabezado": {"Totales": {"MntTotal": 31294}}
```

## "El Item 1 es servicio afecto, item 2 es servicio exento" en boleta mixta

**Causa de confusión:** este texto va en una `<Observacion>` del set como guía, NO va al XML. En el XML, la diferencia se marca con `<IndExe>1</IndExe>` en la línea exenta.

## Carátula con dansanti tiene whitespace raro

**Síntoma:** XML generado tiene `<Caratula  version="1.0" >` con espacios sobrantes.

**Impacto:** generalmente ninguno (XML normalizado al firmar/c14n). Pero si tu validador es estricto puede quejarse. No tocar — dansanti lo hace así y el SII lo acepta.

## Boletas no llevan `<TpoImpresion>`

A diferencia de facturas/NC/ND, las boletas T39 no llevan campo `<TpoImpresion>T|N` en `<IdDoc>`. dansanti lo agrega por error en algunos casos — verifica en tu XML que NO esté.

## "RVD no es obligatorio desde agosto 2022" como reparo

**Síntoma:** mandas el RCOF/RVD y el SII responde con REPARO (1 reparo, 0 errores) con texto `Envio de RVD no es obligatorio desde 2022-08-01`.

**Interpretación:** el SII te avisa que en **producción** ya no exige el RVD. Pero **en certificación SÍ se exige**. El REPARO es solo informativo, NO bloquea la certificación. Tu RCOF cuenta como enviado correctamente.

## El portal SII no responde teléfono ni correo

La mesa de ayuda telefónica del SII rara vez contesta en horario hábil. Alternativas:

- **Formulario "Contáctenos"** en `sii.cl` — SLA real de 24-72h pero responden por escrito.
- **Foros chilenos**: r/chileIT en Reddit, foros de OpenFactura, dansanti GitLab issues.
- **WhatsApp comunidad técnica** — algunos integradores tienen grupos donde se resuelve rápido.
