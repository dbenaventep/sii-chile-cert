# Bugs conocidos en dansanti `facturacion_electronica` y sus parches

La librería [`dansanti/facturacion_electronica`](https://gitlab.com/dansanti/facturacion_electronica) es la opción Python open-source más usada en Chile para emitir DTE al SII. Resuelve el 90% del trabajo: firma digital, timbre TED, envío SOAP/REST, validación XSD local.

Pero tiene bugs que rompen específicamente el flujo de certificación de boletas T39. Esta página documenta los bugs encontrados en la versión **0.21.2** y cómo parcharlos localmente.

> ⚠️ Estos bugs pueden estar resueltos en versiones posteriores. Verificá tu versión con `pip show facturacion_electronica`. Si encuentran que ya están arreglados upstream, abrí un PR para actualizar este doc.

## Bug 1: `<RUTProvSW>` dentro de docstring

**Archivo:** `facturacion_electronica/documento.py` (función `Encabezado`, ~líneas 460-475).

**Síntoma:** aunque pases `"RutProvSW"` en el JSON de la boleta, el XML generado **NO incluye** `<RUTProvSW>`. dansanti se traga el campo silenciosamente.

**Causa:** el código para insertar `RUTProvSW` está dentro de un docstring de Python (comillas triples), no se ejecuta:

```python
@property
def Encabezado(self):
    ...
    encabezado['Receptor'] = self.Receptor
    '''
    if self.es_boleta() and self.RutProvSW:
        encabezado['RUTProvSW'] = self.RutProvSW
    '''
    ...
```

**Nota:** para **boletas T39** este bug **no necesita parche** porque `<RUTProvSW>` no está en el XSD oficial de boletas. Pero para facturas T33 (desde 2026) sí es obligatorio y entonces sí hace falta descomentar.

**Parche (solo si certificas facturas T33 con campos 2026):**

```python
encabezado['Receptor'] = self.Receptor
if self.es_boleta() and self.RutProvSW:
    encabezado['RUTProvSW'] = self.RutProvSW
```

## Bug 2: Referencia en boletas pierde campos del SET

**Archivo:** `facturacion_electronica/documento.py` (función `Referencia`, ~líneas 1180-1212).

**Síntoma:** cuando pasas `"TpoDocRef": "SET"` en el JSON de una boleta, dansanti **lo descarta**. El XML generado queda con `<Referencia>` sin la marca al SET.

**Causa:** dansanti tiene una rama explícita que omite `TpoDocRef`, `FolioRef`, `FchRef` para boletas:

```python
if not self.es_boleta():
    if ref.TpoDocRef:
        ref_line['TpoDocRef'] = ref.TpoDocRef
        ref_line['FolioRef'] = ref.FolioRef
    ref_line['FchRef'] = ref.FchRef or datetime.strftime(...)
```

Para boletas debería incluir el `CodRef` con valor string (oficial soporta `xs:string` maxLength 18), pero dansanti no maneja string en CodRef.

**Decisión técnica:** para boletas, el XSD oficial solo permite `<NroLinRef> + <CodRef> + <RazonRef>`. No requiere parche siempre que pases el JSON correctamente:

```python
# Correcto para boletas:
"Referencia": [{
    "NroLinRef": 1,
    "CodRef": "SET",        # dansanti lo respeta como string
    "RazonRef": "CASO-1",
}]
```

**Verificá visualmente el XML generado** — si dansanti convierte tu "SET" string a número, ahí sí hace falta parchar.

## Bug 3: RCOF/RVD por endpoint incorrecto si `api=True`

**Archivo:** `facturacion_electronica/envio.py` (función `do_consumo_folios_send`).

**Síntoma:** si llamas `fe.consumo_folios(vals)` con `vals["api"] = True`, dansanti manda el RCOF al endpoint REST de pangal/apicert, que NO acepta `<ConsumoFolios>`. Recibes HTTP 400 con `Acceso Denegado` o `SCH-00001 Invalid Schema Name`.

**Causa:** dansanti expone el flag `api` que ruteo entre SOAP y REST. Para boletas operativas en producción (REST) está bien, pero para RCOF en certificación tiene que ir por SOAP.

**Solución:** mantener `api=False` (default) en el JSON del RCOF. NO setear `api=True` para RCOF aunque sea de boletas. El endpoint correcto es `maullin.sii.cl/cgi_dte/UPL/DTEUpload`.

```python
vals = {
    # "api": True,  ← NO setear esto para RCOF
    "Emisor": EMISOR,
    "firma_electronica": _firma_dict(),
    "ConsumoFolios": [...]
}
```

## Bug 4: Filename hardcoded `CF_<fecha>.xml` causa "SCH-00001" en reintentos

**Archivo:** `facturacion_electronica/envio.py` (función `do_consumo_folios_send`, ~línea 662).

**Síntoma:** primer envío del RCOF del día funciona OK (track aceptado). Segundo intento del mismo día (corregido, con SecEnvio=2) rechaza con `SCH-00001 Invalid Schema Name` aunque el XML sea válido.

**Causa:** maullin SOAP usa el **filename del multipart como clave de deduplicación**. dansanti construye `self.filename = 'CF_' + _cf.FchInicio` que da el mismo nombre para todos los envíos del mismo día. El SII rechaza al ver filename duplicado.

**Workaround:** generar el XML del RCOF con dansanti en modo test, copiarlo a un filename distinto, y enviarlo manualmente con `sii_upload.py`:

```python
# 1. Generar XML con dansanti en modo test (no envía):
vals = build_rcof()
vals["test"] = True
res = fe.consumo_folios(vals)
# El XML queda en res[0]["sii_xml_request"]

# 2. Guardarlo con filename único:
xml_path = "/tmp/CF_<rut_emisor>_2026-05-27_v2.xml"
with open(xml_path, "w", encoding="ISO-8859-1") as f:
    f.write(res[0]["sii_xml_request"])

# 3. Enviar con el helper SOAP estándar (ver scripts/send_dte_soap.py):
from sii_upload import enviar
res = enviar(xml_path, "76123456-0", "11111111-1", "cert.pfx", "pwd", "cert")
```

**Parche upstream propuesto:**

```python
def do_consumo_folios_send(self, sec_envio=None):
    ...
    filename = 'CF_' + _cf.FchInicio
    if sec_envio and sec_envio > 1:
        filename += f"_v{sec_envio}"
    self.filename = filename
    ...
```

## Bug 5: XSDs locales desincronizados con los oficiales del SII

**Archivos:** `facturacion_electronica/xsd/*.xsd`

**Síntoma:** dansanti valida tu XML contra su XSD local antes de enviar. Si el XSD local es más estricto (o más laxo) que el oficial vigente del SII, tu XML puede:
- **Pasar localmente y rechazar en el SII** (XSD oficial cambió)
- **Fallar localmente y ser aceptado por el SII** (XSD local agrega restricciones inventadas)

**Caso real:** dansanti tiene un `EnvioBOLETA_v11.xsd` con campos `<TpoDocRef>`, `<FolioRef>`, `<FchRef>`, `<CodVndor>`, `<CodCaja>` en `<Referencia>` que **no están en el oficial**. Si pasas esos campos al JSON, dansanti los valida OK pero el SII no los reconoce.

**Solución:** descargar siempre el XSD oficial del SII para validación final:

```bash
curl -L -o EnvioBOLETA_v11.xsd "https://www.sii.cl/factura_electronica/EnvioBOLETA_v11.xsd"
```

Ver [`xsd-oficial-vs-dansanti.md`](xsd-oficial-vs-dansanti.md) para el diff completo.

## Cómo aplicar los parches

### Opción A: editar el venv directamente

```bash
# Identificar la ruta del paquete instalado
.venv/bin/python -c "import facturacion_electronica; print(facturacion_electronica.__file__)"
# Aplicar parches manualmente con tu editor
```

### Opción B: usar el archivo .patch del repo

```bash
patch -d .venv/lib/python3.12/site-packages/facturacion_electronica/ < patches/dansanti-fe-0.21.2-boletas.patch
```

### Opción C: fork de dansanti

Para uso a largo plazo, considerá un fork (ejemplo: [bluemindsspa/facturacion_electronica](https://github.com/bluemindsspa/facturacion_electronica)) y mantené tus correcciones ahí.

## Reportar upstream

Los bugs 1, 2 y 4 deberían reportarse al repo de dansanti como issues. Si la comunidad chilena se coordina, los próximos certificantes no tendrán que parchar.
