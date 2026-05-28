# Set de Pruebas de Boletas Electrónicas (T39)

Esta es la etapa más sub-documentada y donde más gente se atasca. La documentación oficial del SII para "Set de Pruebas" está orientada a facturas (T33) y aplica solo parcialmente a boletas.

## Resumen ultra-rápido

1. **Endpoint:** `maullin.sii.cl/cgi_dte/UPL/DTEUpload` por SOAP. **NO** `pangal.sii.cl`.
2. **Wrapper XML:** `<EnvioBOLETA>` con schema `EnvioBOLETA_v11.xsd`.
3. **Referencia al set:** SOLO `<NroLinRef> + <CodRef>SET</CodRef> + <RazonRef>CASO-N</RazonRef>`.
4. **No incluir:** `<RUTProvSW>` (no existe en XSD oficial boletas), ni `<TpoDocRef>`, `<FolioRef>`, `<FchRef>` en `<Referencia>`.
5. **`IndServicio>3</IndServicio>`** obligatorio dentro de `<IdDoc>`.
6. **RCOF (Resumen Ventas Diarias)** debe enviarse también, por el mismo endpoint, con folios alineados al envío de boletas.

## Diferencias clave Boletas T39 vs Facturas T33

Este es el cuadro que NADIE me había mostrado claramente:

| Aspecto | Facturas T33 | Boletas T39 |
|---|---|---|
| Endpoint cert | `maullin.sii.cl/cgi_dte/UPL/DTEUpload` | igual |
| Endpoint prod | `palena.sii.cl/cgi_dte/UPL/DTEUpload` | **`pangal.sii.cl/recursos/v1/boleta.electronica.envio`** (REST) |
| Wrapper XML | `<EnvioDTE>` | `<EnvioBOLETA>` |
| Schema | `EnvioDTE_v10.xsd` | `EnvioBOLETA_v11.xsd` |
| RutReceptor en carátula | `60803000-K` | `60803000-K` (igual) |
| Campo `<TpoImpresion>` | Sí | No |
| Campo `<IndServicio>` | No | **Sí**, valores 1/2/3 |
| Campo `<RUTProvSW>` (desde 2026) | Sí | **No** (no está en XSD oficial) |
| Ref. al SET | `<TpoDocRef>SET</TpoDocRef><FolioRef>F</FolioRef><FchRef>...</FchRef><RazonRef>CASO {ID}-{N}</RazonRef>` | **`<CodRef>SET</CodRef><RazonRef>CASO-{N}</RazonRef>`** (mucho más minimal) |

## Estructura del SET DE PRUEBAS BOLETAS

El SII envía un texto plano (no Excel) con esta estructura típica:

```
SII SET DE PRUEBA DE BOLETA ELECTRONICA DE VENTAS Y SERVICIOS

CASO-1
==========
Item                    Cantidad    Precio Unitario con IVA
Cambio de aceite        1           19900
Alineacion y balanceo   1           9900

CASO-2
=========
Item                    Cantidad    Precio Unitario con IVA
Papel de regalo         17          120

(...)

OBSERVACIONES GENERALES
-----------------------
Debe referenciar el caso correspondiente a cada boleta en el XML. Ejemplo:
<CodRef> SET
<RazonRef> CASO-1
```

Notas importantes del set:

- **Precio con IVA incluido**: el set entrega precios brutos. En el XML, los precios van con IVA incluido y `IndServicio=3` activa el cálculo automático del SII.
- **Caracteres exactos**: si dice "Sandwic" sin "h", se escribe así. Si dice "Alineacion" sin acento, así.
- **Sin líneas adicionales**: solo los ítems del set, nada más.
- **CASO-4 mixto**: ítem 1 servicio afecto, ítem 2 servicio exento → en XML el ítem 2 lleva `<IndExe>1</IndExe>`.
- **CASO-5 con Kg**: ítem Arroz lleva `<UnmdItem>Kg</UnmdItem>`.

## Estructura XML del DTE (estricto al XSD oficial)

```xml
<DTE xmlns="http://www.sii.cl/SiiDte" version="1.0">
  <Documento ID="T39F71">
    <Encabezado>
      <IdDoc>
        <TipoDTE>39</TipoDTE>
        <Folio>71</Folio>
        <FchEmis>2026-05-27</FchEmis>
        <IndServicio>3</IndServicio>   <!-- 3 = Boleta de Ventas y Servicio -->
      </IdDoc>
      <Emisor>
        <RUTEmisor>76123456-7</RUTEmisor>
        <RznSocEmisor>EMPRESA EJEMPLO SPA</RznSocEmisor>
        <GiroEmisor>SERVICIOS DE EJEMPLO</GiroEmisor>
        <DirOrigen>DIRECCION 123</DirOrigen>
        <CmnaOrigen>PROVIDENCIA</CmnaOrigen>
        <CiudadOrigen>SANTIAGO</CiudadOrigen>
      </Emisor>
      <Receptor>
        <RUTRecep>66666666-6</RUTRecep>      <!-- consumidor final -->
        <RznSocRecep>Sin RUT</RznSocRecep>   <!-- literal "Sin RUT" -->
        <DirRecep>Santiago</DirRecep>
        <CmnaRecep>Santiago</CmnaRecep>
      </Receptor>
      <Totales>
        <MntNeto>25042</MntNeto>
        <IVA>4758</IVA>
        <MntTotal>29800</MntTotal>
        <VlrPagar>29800</VlrPagar>
      </Totales>
    </Encabezado>

    <Detalle>
      <NroLinDet>1</NroLinDet>
      <NmbItem>Cambio de aceite</NmbItem>
      <QtyItem>1.0</QtyItem>
      <PrcItem>19900</PrcItem>
      <MontoItem>19900</MontoItem>
    </Detalle>
    <Detalle>
      <NroLinDet>2</NroLinDet>
      <NmbItem>Alineacion y balanceo</NmbItem>
      <QtyItem>1.0</QtyItem>
      <PrcItem>9900</PrcItem>
      <MontoItem>9900</MontoItem>
    </Detalle>

    <Referencia>
      <NroLinRef>1</NroLinRef>
      <CodRef>SET</CodRef>
      <RazonRef>CASO-1</RazonRef>
    </Referencia>

    <TED version="1.0">...</TED>
    <TmstFirma>2026-05-27T12:34:56</TmstFirma>
  </Documento>
  <Signature>...</Signature>
</DTE>
```

**Lo que NO debe estar:**
- `<RUTProvSW>` en `<Encabezado>` — no existe en el XSD oficial de boletas (aunque tu librería lo genere por bug, hay que parchar)
- `<TpoDocRef>`, `<FolioRef>`, `<FchRef>` dentro de `<Referencia>` — no existen en el XSD oficial de boletas
- `<TpoImpresion>` en `<IdDoc>` — campo de facturas, no boletas

## Flujo completo

### 1. Pedir folios

Portal SII → `Factura electrónica → Sistema de facturación gratuito del SII → Solicitar timbraje (folios)` → Boleta Electrónica (Tipo 39).

El SII te entrega un CAF en formato XML con un rango de folios autorizados (ej. 1-50). Guárdalo en `caf/`.

### 2. Recibir el set de pruebas

Llega por correo. Es texto plano con CASO-1, CASO-2... CASO-5.

### 3. Generar 5 boletas T39 con los datos del set

Aplicando todas las reglas anteriores. **Antes de enviar, lee el XML y verifica que no tenga campos espurios.**

### 4. Generar el RCOF/RVD del día

Wrapper `<ConsumoFolios>` con resumen de los 5 folios usados y montos totales. El RCOF de boletas para certificación SÍ se exige (en producción ya no, pero el SII te lo aclara con un REPARO informativo: "RVD no es obligatorio desde 2022").

### 5. Enviar boletas + RCOF al SII

Ambos al mismo endpoint:

```
POST https://maullin.sii.cl/cgi_dte/UPL/DTEUpload
```

Multipart con campos `rutSender`, `dvSender`, `rutCompany`, `dvCompany`, `archivo`. Token tomado de `maullin.sii.cl/DTEWS/CrSeed.jws` + `GetTokenFromSeed.jws`.

Recibes 2 track IDs (uno por archivo).

### 6. Solicitar revisión del set

Portal SII → Certificación de Boletas → "Solicitud de revisión del set de pruebas". Ingresas el track ID del envío de boletas.

### 7. Esperar respuesta

El SII responde por correo (puede demorar minutos a horas). Posibles resultados:

- **V°B°** → procedes a "Declaración de Cumplimiento" en el portal, y luego habilitas producción.
- **SRH - Set de Prueba Rechazado** → analizar el motivo, corregir, reenviar.

## Casos típicos del set y cómo se reflejan en XML

### CASO-1: Servicios mixtos sin IVA explícito

```
Cambio de aceite        1    19900
Alineacion y balanceo   1    9900
```

XML:
```xml
<Detalle>
  <NroLinDet>1</NroLinDet>
  <NmbItem>Cambio de aceite</NmbItem>
  <QtyItem>1</QtyItem>
  <PrcItem>19900</PrcItem>
  <MontoItem>19900</MontoItem>
</Detalle>
<Detalle>
  <NroLinDet>2</NroLinDet>
  <NmbItem>Alineacion y balanceo</NmbItem>
  <QtyItem>1</QtyItem>
  <PrcItem>9900</PrcItem>
  <MontoItem>9900</MontoItem>
</Detalle>
```

Totales: 29.800 con IVA incluido. Neto = round(29800/1.19) = 25.042. IVA = 4.758.

### CASO-4: Boleta mixta (afecto + exento)

```
item afecto 1    8    1590
item exento 2    2    1000
OBSERVACION: "El item 1 es un servicio afecto. El item 2 es un servicio exento."
```

XML:
```xml
<Detalle>
  <NroLinDet>1</NroLinDet>
  <NmbItem>item afecto 1</NmbItem>
  <QtyItem>8</QtyItem>
  <PrcItem>1590</PrcItem>
  <MontoItem>12720</MontoItem>
</Detalle>
<Detalle>
  <NroLinDet>2</NroLinDet>
  <IndExe>1</IndExe>                      <!-- exento -->
  <NmbItem>item exento 2</NmbItem>
  <QtyItem>2</QtyItem>
  <PrcItem>1000</PrcItem>
  <MontoItem>2000</MontoItem>
</Detalle>
```

Totales: Neto=10689, IVA=2031, MntExe=2000, MntTotal=14720.

### CASO-5: Producto con unidad de medida

```
Arroz    5    700
OBSERVACION: "Se debe informar en el XML Unidad de medida en Kg."
```

XML:
```xml
<Detalle>
  <NroLinDet>1</NroLinDet>
  <NmbItem>Arroz</NmbItem>
  <QtyItem>5</QtyItem>
  <UnmdItem>Kg</UnmdItem>           <!-- unidad de medida -->
  <PrcItem>700</PrcItem>
  <MontoItem>3500</MontoItem>
</Detalle>
```

## RCOF / RVD - formato del XML

```xml
<?xml version="1.0" encoding="ISO-8859-1"?>
<ConsumoFolios xmlns="http://www.sii.cl/SiiDte"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xsi:schemaLocation="http://www.sii.cl/SiiDte ConsumoFolio_v10.xsd"
               version="1.0">
  <DocumentoConsumoFolios ID="SetDoc">
    <Caratula version="1.0">
      <RutEmisor>76123456-7</RutEmisor>
      <RutEnvia>11111111-1</RutEnvia>
      <FchResol>2026-04-28</FchResol>
      <NroResol>0</NroResol>
      <FchInicio>2026-05-27</FchInicio>
      <FchFinal>2026-05-27</FchFinal>
      <Correlativo>1</Correlativo>
      <SecEnvio>1</SecEnvio>
      <TmstFirmaEnv>2026-05-27T12:34:56</TmstFirmaEnv>
    </Caratula>
    <Resumen>
      <TipoDocumento>39</TipoDocumento>
      <MntNeto>43831</MntNeto>
      <MntIva>8329</MntIva>
      <TasaIVA>19</TasaIVA>
      <MntExento>2000</MntExento>
      <MntTotal>54160</MntTotal>
      <FoliosEmitidos>5</FoliosEmitidos>
      <FoliosAnulados>0</FoliosAnulados>
      <FoliosUtilizados>5</FoliosUtilizados>
      <RangoUtilizados>
        <Inicial>71</Inicial>
        <Final>75</Final>
      </RangoUtilizados>
    </Resumen>
  </DocumentoConsumoFolios>
  <Signature>...</Signature>
</ConsumoFolios>
```

## Errores típicos en este paso (ver [`gotchas.md`](gotchas.md) para detalle)

- ❌ Mandar el set por pangal REST → `EPR` aceptado pero set siempre rechaza.
- ❌ Mandar el set por maullin SOAP con `<RUTProvSW>` o referencia con campos extra → `HED-3-211 Dato invalido`.
- ❌ Reenviar el RCOF con mismo filename → `SCH-00001 Invalid Schema Name` (mensaje engañoso, es deduplicación por filename).
- ❌ Asumir que pedir CAF nuevo = pedir set nuevo. Son trámites distintos. Un set rechazado solo se libera reiniciando el proceso de cert, no descargando más folios.

## Después del V°B°

1. **Declaración de Cumplimiento** en el portal SII (formulario). Una vez declarada → emisor habilitado para emitir boletas en producción.
2. **A partir de aquí, las boletas operativas se envían por REST a `pangal.sii.cl/recursos/v1/boleta.electronica.envio`** — el endpoint clásico (SOAP) NO se usa para producción de boletas, solo se usó para el set de prueba.
