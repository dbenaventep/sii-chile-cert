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

## 1.3. Postular a ambiente de certificación

En `sii.cl`:

`Mi SII → Servicios online → Factura electrónica → Sistema de facturación gratuito del SII → Postulación`

Llenas el formulario. El SII responde por correo con:
- Confirmación de inicio del proceso
- Set de pruebas inicial (texto con casos)
- Acceso al ambiente de certificación (`maullin.sii.cl` para SOAP / `apicert.sii.cl` para REST de boletas)

## 1.4. Solicitar CAFs (timbraje de folios)

Antes de emitir, necesitas un CAF por cada tipo de documento que vas a usar.

`Servicios online → Factura electrónica → Sistema de facturación gratuito → Solicitar timbraje (folios)`

Selecciona el tipo de documento (T33, T34, T46, T52, T56, T61, T39, T41) y la cantidad de folios. El SII te devuelve un XML firmado con un rango.

Guárdalos en una carpeta `caf/` (fuera del repo, ver `.gitignore`).

**Trampa:** "pedir CAFs" ≠ "pedir set de pruebas". Si el set queda rechazado (SRH) y pides un CAF nuevo, el SII te da más folios pero **el mismo set ID** sigue activo. Para resetear el set, hay que reiniciar el proceso de certificación específicamente.

## 1.5. Datos del emisor que se inyectan en cada DTE

Los siguientes campos del emisor van en cada documento (no cambian entre DTEs):

```python
EMISOR = {
    "RUTEmisor": "76123456-7",
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

**`FchResol`** en cert: es la fecha del correo de habilitación del SII. Esa misma fecha va en todos los envíos (set, simulación, intercambio, etc.).

**Receptor obligatorio en envíos al SII:** siempre `<RutReceptor>60803000-K</RutReceptor>` en la Carátula (el RUT del SII).

## 1.6. Resumen de credenciales necesarias

| Credencial | Dónde se obtiene | Dónde se usa |
|---|---|---|
| Certificado `.pfx` + password | autoridad certificadora | firmar DTEs y envíos |
| RUT firmante (persona) | el del cert digital | campo `RutEnvia` en Carátula |
| RUT empresa | el SII | campo `RutEmisor` |
| FchResol / NroResol cert | correo del SII | Carátula de cada envío |
| CAFs por tipo de doc | portal SII | timbrar TED de cada DTE |
| Clave tributaria empresa | el SII | acceder al portal cert |
