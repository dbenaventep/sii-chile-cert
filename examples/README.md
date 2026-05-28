# Ejemplos JSON anonimizados

Estos JSONs son ejemplos genéricos para alimentar funciones como `fe.timbrar_y_enviar()` de la librería dansanti `facturacion_electronica`, o como referencia para construir tu propia implementación.

**Todos los datos son ficticios**: RUT, razón social, dirección, ítems. Reemplazar con datos reales antes de usar.

## Convenciones

| Campo | Valor en ejemplos | Reemplazar por |
|---|---|---|
| `RUTEmisor` | `76123456-0` | RUT real de la empresa emisora |
| `RUTRecep` (receptor real) | `77234567-4` | RUT real del cliente |
| `RUTRecep` (consumidor final boleta) | `66666666-6` | mantener (RUT genérico para boletas) |
| `RUTReceptor` (Carátula al SII) | `60803000-K` | mantener (RUT del SII) |
| `rut_firmante` (firma electrónica) | `11111111-1` | RUT real del firmante autorizado |
| `string_firma` (cert .pfx base64) | `"<BASE64_DEL_PFX_AQUI>"` | base64 real del certificado |
| `string_password` (cert pwd) | `"<PASSWORD_PFX>"` | password real |
| `caf_file` (CAF base64) | `"<CAF_BASE64_AQUI>"` | base64 real del CAF descargado del SII |

## Ejemplos disponibles

### Facturas (T33, T34, T46, T52, T56, T61)

| Archivo | Caso |
|---|---|
| [`factura_basica.json`](factura_basica.json) | T33 con 2 ítems afectos, sin descuentos |
| [`factura_descuento_linea.json`](factura_descuento_linea.json) | T33 con descuento por línea (`DescuentoPct`) |
| [`factura_mixta.json`](factura_mixta.json) | T33 con ítems afectos + 1 ítem exento (`IndExe=1`) |
| [`factura_descuento_global.json`](factura_descuento_global.json) | T33 con `DscRcgGlobal` |
| [`factura_exenta.json`](factura_exenta.json) | T34 sin IVA |
| [`factura_compra_retencion.json`](factura_compra_retencion.json) | T46 con retención total IVA (cambio sujeto) |
| [`guia_traslado_interno.json`](guia_traslado_interno.json) | T52 `IndTraslado=5`, receptor = emisor |
| [`guia_venta_entrega.json`](guia_venta_entrega.json) | T52 venta con `TipoDespacho=2 IndTraslado=1` |
| [`nc_corrige_giro.json`](nc_corrige_giro.json) | T61 corrige texto, 1 línea genérica con `CdgItem=NO_PRODUCT` |
| [`nc_devolucion.json`](nc_devolucion.json) | T61 devolución de mercaderías (replica items factura) |
| [`nc_anula_factura.json`](nc_anula_factura.json) | T61 anula factura completa |
| [`nd_anula_nc.json`](nd_anula_nc.json) | T56 anula nota de crédito |
| [`nd_corrige_montos.json`](nd_corrige_montos.json) | T56 recargo por intereses (suma al original) |

### Boletas (T39, T41)

| Archivo | Caso |
|---|---|
| [`boleta_t39_basica.json`](boleta_t39_basica.json) | T39 con 2 ítems (set de pruebas caso 1) |
| [`boleta_t39_mixta.json`](boleta_t39_mixta.json) | T39 mixta (set caso 4: afecto + exento) |
| [`boleta_t39_unmdItem.json`](boleta_t39_unmdItem.json) | T39 con unidad de medida (set caso 5: Arroz en Kg) |

### Set de Pruebas completos

| Archivo | Tipo |
|---|---|
| [`set_basico_facturas.json`](set_basico_facturas.json) | Set Básico Facturas (4 T33 + 3 T61 + 1 T56) |
| [`set_boletas_t39.json`](set_boletas_t39.json) | Set Boletas (5 T39 - los 5 casos típicos del set) |

### RCOF / RVD

| Archivo | Tipo |
|---|---|
| [`rcof_boletas.json`](rcof_boletas.json) | Reporte Consumo Folios para boletas T39 |

### Intercambio

| Archivo | Tipo |
|---|---|
| [`intercambio_respuesta_dte.json`](intercambio_respuesta_dte.json) | RespuestaDTE con RecepcionEnvio (archivo 1) |
| [`intercambio_recibo_mercaderias.json`](intercambio_recibo_mercaderias.json) | EnvioRecibos (archivo 2) |
| [`intercambio_resultado_comercial.json`](intercambio_resultado_comercial.json) | RespuestaDTE con ResultadoDTE (archivo 3) |

## Patrones importantes que se repiten

### Bloque Emisor

```json
{
  "RUTEmisor": "76123456-0",
  "RznSoc": "EMPRESA EJEMPLO SPA",
  "GiroEmis": "SERVICIOS DE EJEMPLO",
  "Actecos": [123456],
  "DirOrigen": "CALLE EJEMPLO 123 OF 456",
  "Telefono": "+56912345678",
  "CmnaOrigen": "PROVIDENCIA",
  "CiudadOrigen": "SANTIAGO",
  "CorreoEmisor": "facturacion@empresa.cl",
  "Modo": "certificacion",
  "NroResol": 0,
  "FchResol": "2026-04-28",
  "ValorIva": 19,
  "CdgSIISucur": ""
}
```

### Bloque firma electrónica

```json
{
  "init_signature": true,
  "string_firma": "<BASE64_DEL_PFX>",
  "string_password": "<PASSWORD_PFX>",
  "rut_firmante": "11111111-1"
}
```

### IVA afecto (CodImp=14)

```json
{"CodImp": 14, "price_include": false, "TasaImp": 19.0}
```

Para boletas usar `"price_include": true` (los precios vienen con IVA incluido).

### Retención IVA total (CodImp=15)

```json
{"CodImp": 15, "Retencion": 19.0, "price_include": false, "TasaImp": 19.0}
```

### Referencia al SET para facturas

```json
{
  "NroLinRef": 1,
  "TpoDocRef": "SET",
  "FolioRef": 32,
  "RazonRef": "CASO XXXXXXX-1",
  "FchRef": "2026-04-29"
}
```

### Referencia al SET para boletas (¡distinto!)

```json
{
  "NroLinRef": 1,
  "CodRef": "SET",
  "RazonRef": "CASO-1"
}
```
