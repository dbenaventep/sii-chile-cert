# 7. Resolución y paso a producción

Última etapa. El SII emite la resolución oficial que autoriza al contribuyente como emisor electrónico, y tú habilitas tu sistema para producción.

## Trigger

Una vez aprobadas TODAS las etapas anteriores:

- ✅ Set de Pruebas (todos los sets que aplican: básico, guías, exentas, compras)
- ✅ Simulación
- ✅ Intercambio
- ✅ Documentos Impresos
- ✅ Set de Pruebas Boletas (si emites boletas)
- ✅ Declaración de Cumplimiento boletas

El SII emite una **Resolución Exenta** que te autoriza como emisor electrónico. Te llega por correo y queda en el ambiente del contribuyente en el portal SII.

## Datos que cambian al pasar a producción

| Campo | Cert | Prod |
|---|---|---|
| `Modo` (en config emisor) | `certificacion` | `produccion` |
| `NroResol` | `0` | número de la resolución oficial (ej. `80`) |
| `FchResol` | fecha de habilitación cert | fecha de la resolución oficial |
| Endpoint SOAP | `maullin.sii.cl/...` | `palena.sii.cl/...` |
| Endpoint REST boletas | `apicert.sii.cl/...` (semilla/token) + `pangal.sii.cl/...` (envío) | `api.sii.cl/...` + `rahue.sii.cl/...` |
| Certificado digital | el mismo `.pfx` (no cambia) | mismo `.pfx` |
| RUTs receptores | RUTs ficticios OK | **RUTs reales de clientes** |

## Paso a paso

### 1. Esperar la resolución por correo

Llega como adjunto PDF con el número de resolución y fecha. Guárdalo.

### 2. Actualizar configuración del emisor

```python
EMISOR_PROD = {
    "RUTEmisor": "76123456-7",
    "RznSoc": "EMPRESA EJEMPLO SPA",
    # ... resto igual ...
    "Modo": "produccion",           # ← cambio clave
    "NroResol": 80,                 # ← número real
    "FchResol": "2026-06-15",       # ← fecha de la resolución
}
```

### 3. Solicitar CAFs de producción

Los CAFs de certificación NO sirven en producción. Tienes que pedir CAFs nuevos para producción en el portal SII.

`Portal SII → Factura electrónica → Sistema de facturación gratuito → Solicitar timbraje`

Selecciona "Producción" y el tipo de documento.

### 4. Cambiar endpoints en tu código

Los hosts de cert (maullin, apicert, pangal) no funcionan para producción. Cambia todo a:
- `palena.sii.cl` para SOAP
- `api.sii.cl` para semilla/token boletas REST
- `rahue.sii.cl` para envío boletas REST

### 5. Emitir un documento de prueba en producción

Antes de operar comercialmente, emite **1 DTE real** a una empresa amigable (ej. una empresa relacionada o tu propia empresa como receptor) para validar el flujo completo end-to-end.

### 6. Habilitar el sistema en producción

Ya estás en operación. Cada DTE emitido:
- Se firma con tu certificado
- Se timbra con folio del CAF de producción
- Se envía al SII en producción
- Si es operación con tercero, el receptor te puede aceptar/reclamar en 8 días

## Verificación en el portal SII

Una vez en producción, podés verificar el estado de un DTE específico:

`Portal SII → Servicios online → Factura electrónica → Consulta DTE`

Ingresa RUT emisor, tipo, folio. El SII te muestra el estado actual.

## Backup importante antes del cambio

Si emitiste DTEs en certificación (sandbox), normalmente NO se conservan después del paso a producción. Si quieres respaldar:

- Todos los XML firmados están en tu sistema local — guarda copia.
- Si usaste el sistema gratuito MiPyme del SII para emitir DTEs en certificación, los DTEs **se borran del portal** al pasar a producción. Descargalos antes desde `Historial DTE → Documentos Emitidos → Obtener Envío` (hasta 20 por archivo).

## Mantención periódica

- **Renovar el certificado digital antes que expire** (típicamente 1 año). Sin cert válido no puedes firmar.
- **Pedir CAFs cuando se agoten** los folios disponibles.
- **Actualizar Libro de Compras y Ventas** mensualmente si todavía se exige (depende del régimen tributario).
- **Estar atento a comunicados del SII** sobre cambios en el formato (ej. campo `<RUTProvSW>` desde 2026 en facturas).
