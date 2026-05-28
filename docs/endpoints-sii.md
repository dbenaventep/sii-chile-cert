# Mapa completo de endpoints del SII Chile

El SII tiene **dos ecosistemas paralelos** para DTE, lo que genera mucha confusión: el clásico SOAP (vigente desde 2003) y el REST nuevo (introducido en 2022-2023 para boletas).

## Ambientes

| Ambiente | DTE clásico (SOAP) | Boletas REST | Boletas REST envío |
|---|---|---|---|
| **Certificación** | `maullin.sii.cl` | `apicert.sii.cl` (semilla/token) | `pangal.sii.cl` (envío archivo) |
| **Producción** | `palena.sii.cl` | `api.sii.cl` | `rahue.sii.cl` |

## Cuándo usar cada uno

| Operación | Endpoint | Wrapper XML | Schema |
|---|---|---|---|
| Set de pruebas de facturas (T33, T34, T46, T52, T61, T56) — cert | `maullin.sii.cl/cgi_dte/UPL/DTEUpload` | `<EnvioDTE>` | `EnvioDTE_v10.xsd` |
| **Set de pruebas de boletas (T39, T41) — cert** ⭐ | **`maullin.sii.cl/cgi_dte/UPL/DTEUpload`** | `<EnvioBOLETA>` | `EnvioBOLETA_v11.xsd` |
| RCOF / Resumen Ventas Diarias (RVD) — cert | `maullin.sii.cl/cgi_dte/UPL/DTEUpload` | `<ConsumoFolios>` | `ConsumoFolio_v10.xsd` |
| Libro de Compras / Ventas (LCV) — cert | `maullin.sii.cl/cgi_dte/UPL/DTEUpload` | `<LibroCompraVenta>` | `LibroCV_v10.xsd` |
| Libro de Boletas — cert | `maullin.sii.cl/cgi_dte/UPL/DTEUpload` | `<LibroBoleta>` | `LibroBOLETA_v10.xsd` |
| Facturas operativas en producción | `palena.sii.cl/cgi_dte/UPL/DTEUpload` | `<EnvioDTE>` | igual |
| **Boletas operativas en producción** | **`pangal.sii.cl/recursos/v1/boleta.electronica.envio`** (REST multipart) | `<EnvioBOLETA>` | igual |
| Boletas operativas en cert (prueba REST antes de prod) | `pangal.sii.cl/recursos/v1/boleta.electronica.envio` | `<EnvioBOLETA>` | igual |

## ⚠️ Trampa común con boletas

Existe el mito (alimentado por documentación parcial post-2023) de que **TODO lo de boletas va por REST de pangal**. Es falso:

- **Producción operativa de boletas:** sí, va por pangal REST (`/recursos/v1/boleta.electronica.envio`).
- **Set de pruebas de certificación de boletas:** NO. Va por el SOAP clásico de maullin (`/cgi_dte/UPL/DTEUpload`).

Si mandas el set de pruebas por pangal REST, el SII lo acepta con estado `EPR` (Envío Procesado) — pero el set de pruebas **nunca se evalúa contra ese envío**. La pantalla de revisión del set siempre va a responder `SRH - SET DE PRUEBA RECHAZADO` con `El Documento no esta en el envio` en todos los casos, sin importar cómo armes el XML.

## Tokens / semilla

### SOAP clásico (maullin / palena)

```
GET  https://maullin.sii.cl/DTEWS/CrSeed.jws?WSDL          → semilla
POST https://maullin.sii.cl/DTEWS/GetTokenFromSeed.jws?WSDL → token (firmando semilla con cert)
```

Token va en cookie `TOKEN=<valor>` en los siguientes POST a `/cgi_dte/UPL/DTEUpload`.

### REST nuevo (apicert / api)

```
GET  https://apicert.sii.cl/recursos/v1/boleta.electronica.semilla   → semilla XML
POST https://apicert.sii.cl/recursos/v1/boleta.electronica.token     → token XML
```

Token también en cookie. **Importante**: el host del envío (pangal) es distinto al host de semilla/token (apicert) — pero el token es el mismo.

## Consulta de estado

| Operación | Endpoint cert |
|---|---|
| Estado envío SOAP por trackid | Consulta `QueryEstUp` en `maullin.sii.cl/DTEWS/QueryEstUp.jws?WSDL` |
| Estado envío boleta REST por trackid | `GET https://apicert.sii.cl/recursos/v1/boleta.electronica.envio/{rut}-{dv}-{trackid}` |
| Estado de un DTE individual por folio | `GET https://apicert.sii.cl/recursos/v1/boleta.electronica/{rut}-{dv}-{tipo}-{folio}/estado?...` |

## Carátula obligatoria

Todos los envíos (sea EnvioDTE, EnvioBOLETA, LibroCV, ConsumoFolios) llevan una Carátula con:

```xml
<RutEmisor>...</RutEmisor>          <!-- RUT empresa -->
<RutEnvia>...</RutEnvia>            <!-- RUT firmante autorizado, persona natural -->
<RutReceptor>60803000-K</RutReceptor>  <!-- RUT del SII (siempre) -->
<FchResol>...</FchResol>            <!-- fecha resolución cert/prod del emisor -->
<NroResol>0</NroResol>              <!-- 0 en cert; número real en prod -->
<TmstFirmaEnv>...</TmstFirmaEnv>    <!-- ISO 8601 sin TZ: 2026-05-27T12:34:56 -->
```

## Multipart POST (envío SOAP/REST)

Campos del multipart en TODOS los envíos a `/cgi_dte/UPL/DTEUpload` y `/recursos/v1/boleta.electronica.envio`:

| Campo | Valor |
|---|---|
| `rutSender` | parte numérica del RUT firmante |
| `dvSender` | dígito verificador del RUT firmante |
| `rutCompany` | parte numérica del RUT empresa |
| `dvCompany` | dígito verificador del RUT empresa |
| `archivo` | nombre del archivo + contenido XML ISO-8859-1 |

**Gotcha del filename:** el SII usa el filename como clave de deduplicación. Si reintentas un envío del mismo período/día con mismo filename, el SII rechaza con `SCH-00001: Invalid Schema Name` (mensaje confuso, pero el problema real es el filename duplicado). Workaround: variar el filename, ej. `CF_2026-05-27_v2.xml` en lugar de `CF_2026-05-27.xml`.

## Códigos de respuesta del SII

### SOAP clásico

```xml
<RECEPCIONDTE>
  <STATUS>0</STATUS>           <!-- 0 = OK, otro número = error -->
  <TRACKID>0249800000</TRACKID>
</RECEPCIONDTE>
```

| STATUS | Significado |
|---|---|
| 0 | Upload OK |
| 1 | Sender no tiene permiso |
| 2 | Tamaño archivo incorrecto |
| 3 | Archivo cortado |
| 5 | No autenticado |
| 6 | Empresa no autorizada |
| 7 | Schema/contenido inválido |
| 99 | Otro error |

### REST nuevo

```json
{
  "estado": "EPR",          // Envío Procesado
  "trackid": 27000000,
  "estadistica": [{"tipo": 39, "informados": 5, "aceptados": 5}]
}
```

| estado | Significado |
|---|---|
| `EPR` | Envío Procesado |
| `RPR` | Reparos |
| `RCH` | Rechazado |
| `RFR` | Rechazo en formato |
| `RPT` | Rechazo en pruebas |
| `RSC` | Rechazo en schema |
