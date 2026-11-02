# 1. Setup del emisor en ambiente de certificación

Pasos previos a generar el primer DTE.

## 1.1. Tener cuenta de empresa en el SII

- El representante legal debe estar registrado en `sii.cl` con clave única o clave tributaria.
- La empresa debe tener **giros declarados** que correspondan al tipo de documento que va a emitir.
- Si emite boletas: debe estar autorizada como "primera categoría" (típicamente).

## 1.2. Obtener certificado digital

Necesitas un certificado digital `.pfx` (PKCS#12) emitido por una autoridad reconocida por el SII:

- e-CertChile (más común)
- e-Sign
- Acepta
- otras autoridades certificadoras

El certificado lo emite la persona natural autorizada por la empresa (RUT firmante). Costo: ~$30.000 CLP/año aprox.

El archivo `.pfx` contiene la clave privada protegida con password. **Nunca lo subas a un repo**.

## 1.3. Autorizar al RUT del firmante ante el SII

**Este paso se olvida con frecuencia y produce el error "RUT No Autorizado a Firmar Documentos Electrónicos" al enviar los sets.**

El RUT de la persona dueña del certificado digital (el firmante) debe estar **explícitamente autorizado** por la empresa para firmar DTEs en su nombre. No basta con que tenga el `.pfx`; el SII mantiene una lista por empresa de RUTs habilitados como firmantes, y el envío se rechaza si el firmante no está en esa lista.

### Cómo autorizarlo

El representante legal de la empresa entra a `sii.cl` con su clave y va a:

`Mi SII → Servicios online → Factura electrónica → Sistema de facturación gratuito del SII → "Inscríbase aquí" / "Administración de usuarios" → Agregar usuario autorizado`

(El nombre exacto del menú varía según el año; busca cualquier opción que mencione "usuario autorizado", "habilitar firmante" o "delegar firma electrónica".)

Pasos:

1. Ingresa el RUT de la persona (el dueño del certificado).
2. Asigna el permiso **"Firmar Documentos Tributarios Electrónicos"** (o equivalente).
3. Si corresponde, asigna también permisos para emitir/anular/ceder.
4. Guarda.

El firmante puede ser el mismo representante legal o un tercero (contador, integrador, empleado). Es por **RUT persona**, no por certificado.

### Verificar que quedó habilitado

- Desde el portal del SII, sección de administración de usuarios, debería aparecer en la lista.
- Si al enviar el set llega un correo del SII con asunto similar a _"RUT No Autorizado a Firmar Documentos Electrónicos"_, el paso anterior no se hizo (o se hizo para una empresa distinta).

### En empresas con holding / múltiples RUTs

Cada empresa (RUT emisor) mantiene su propia lista de firmantes autorizados. Si un mismo contador firma para 5 empresas, debe estar habilitado en las 5 por separado.

### Caso especial: el firmante es el mismo representante legal

Aun así conviene revisarlo en el portal: en algunos casos el SII pide hacer click explícitamente en "habilitar como firmante" aunque sea la misma persona que administra la empresa.

## 1.4. Postular a ambiente de certificación

En `sii.cl`:

`Mi SII → Servicios online → Factura electrónica → Sistema de facturación gratuito del SII → Postulación`

Llenas el formulario. El SII responde por correo con:

- Confirmación de inicio del proceso
- Set de pruebas inicial (texto con casos)
- Acceso al ambiente de certificación (`maullin.sii.cl` para SOAP / `apicert.sii.cl` para REST de boletas)

## 1.5. Solicitar CAFs (timbraje de folios)

Antes de emitir, necesitas un CAF por cada tipo de documento que vas a usar.

`Servicios online → Factura electrónica → Sistema de facturación gratuito → Solicitar timbraje (folios)`

Selecciona el tipo de documento (T33, T34, T46, T52, T56, T61, T39, T41) y la cantidad de folios. El SII te devuelve un XML firmado con un rango.

Guárdalos en una carpeta `caf/` (fuera del repo, ver `.gitignore`).

En nuestra experiencia, el ambiente de certificación permite solicitar inicialmente hasta 100 folios por tipo de DTE. Posteriormente, la cantidad autorizada depende del uso registrado por el SII.

### Recomendación de planificación:

| Tipo DTE                 | SET de prueba | Simulación | Solicitud inicial sugerida |
| ------------------------ | ------------- | ---------- | -------------------------- |
| Factura electrónica (33) | 4             | 10–26      | 14–30                      |
| Nota de crédito (61)     | 3             | ≥1         | 10                         |
| Nota de débito (56)      | 1             | ≥1         | 10                         |

Las cantidades sugeridas son recomendaciones operativas basadas en la experiencia, no cuotas garantizadas por el SII. Conviene verificar la cantidad exacta de documentos exigida por el SET asignado.

### Observaciones pendientes de confirmación:

- No se ha confirmado si los CAF tienen vencimiento aplicable en este entorno.
- Anular un rango aparentemente no restituye los folios disponibles para nuevas solicitudes.
- La emisión de documentos parece aumentar la cantidad de folios que el SII permite solicitar posteriormente. Por ejemplo, emitir 10 podría permitir solicitar 20, pero esto no está demostrado como regla general.

**Importante:** pedir un CAF no equivale a pedir un Set nuevo. En el proceso observado, pedir otro CAF no reinició el Set activo; solicitar un Set nuevo reinició solo parte de la certificación, pero no elimina los archivos o libros registrados anteriormente.

| Problema                                            | Causa observada                                             | Solución o prevención                                                            |
| --------------------------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Error al subir archivos                             | Se reutiliza un nombre de archivo anterior                  | Generar nombres únicos para cada carga                                           |
| `LNC – Tipo de Envío de Libro No Corresponde`       | Reutilización de un período que ya tiene libros registrados | Revisar el período y el historial de libros antes de reiniciar                   |
| `LRH – Envío de Libro Rechazado – Descuadrado`      | Libros de un período futuro con DTE de otro período         | Mantener consistencia entre períodos y documentos                                |
| `(TED-1-647) Fecha Timbre Fuera de Rango Permitido` | Se cambian fechas de DTE para ajustarlas a otros períodos   | No alterar arbitrariamente fechas tributarias para resolver conflictos de libros |

Advertencia: No debe asumirse que solicitar un nuevo SET deja el ambiente completamente limpio.

## 1.6. Datos del emisor que se inyectan en cada DTE

Los siguientes campos del emisor van en cada documento (no cambian entre DTEs):

```python
EMISOR = {
    "RUTEmisor": "76123456-0",
    "RznSoc": "EMPRESA EJEMPLO SPA",
    "GiroEmis": "GIRO EJEMPLO DECLARADO",
    "Actecos": [123456, 789012],        # códigos de actividad económica
    "DirOrigen": "CALLE EJEMPLO 123",
    "Telefono": "+56912345678",
    "CmnaOrigen": "PROVIDENCIA",
    "CiudadOrigen": "SANTIAGO",
    "CorreoEmisor": "sii@empresa.cl",
    "Modo": "certificacion",            # o "produccion" para prod
    "NroResol": 0,                      # 0 en cert; número real en prod
    "FchResol": "2026-04-28",           # fecha de habilitación cert
    "ValorIva": 19,
    "CdgSIISucur": "",                  # código sucursal si aplica
}
```

**`FchResol` y `NroResol`**: informar los datos que el SII reconoce para el emisor. En el caso de certificación, `NroResol=0` junto con la fecha consultada en “Consultar Empresas Autorizadas”. Esa misma fecha va en todos los envíos (set, simulación, intercambio, etc.).

**Receptor obligatorio en envíos al SII:** siempre `<RutReceptor>60803000-K</RutReceptor>` en la Carátula (el RUT del SII).

## 1.7. Resumen de credenciales necesarias

| Credencial                    | Dónde se obtiene        | Dónde se usa                 |
| ----------------------------- | ----------------------- | ---------------------------- |
| Certificado `.pfx` + password | autoridad certificadora | firmar DTEs y envíos         |
| RUT firmante (persona)        | el del cert digital     | campo `RutEnvia` en Carátula |
| RUT empresa                   | el SII                  | campo `RutEmisor`            |
| FchResol / NroResol cert      | correo del SII          | Carátula de cada envío       |
| CAFs por tipo de doc          | portal SII              | timbrar TED de cada DTE      |
| Clave tributaria empresa      | el SII                  | acceder al portal cert       |
