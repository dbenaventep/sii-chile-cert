# 3. Simulación operativa

Segunda etapa: emitir un volumen de DTEs simulando operación real, no datos predefinidos del SII.

## Qué pide el SII

Generar los documentos indicados en las instrucciones vigentes del SII, con datos **paralelos a la operación real**. El [manual de certificación](https://www.sii.cl/servicios_online/docs/manual_certificacion.pdf) indicaba usar 10–100 DTE históricos para la simulación; una simulación de siete DTE fue aceptada en nuestro caso. Esa aceptación observada no modifica el manual ni establece una excepción general.

En el proceso observado, los documentos incluyeron:

- Fechas válidas del mes actual
- RUTs receptores ficticios pero con dígito verificador válido
- Glosas variadas (acordes al giro de la empresa)
- Cantidades y precios diversos

## Mix práctico para prever las Muestras Impresas (basado en proceso aprobado)

| Recomendación práctica | Tipo                 | Notas                       |
| ---------------------- | -------------------- | --------------------------- |
| ~18                    | T33 facturas afectas | Variedad de glosas y montos |
| 1                      | T61 NC               | `CodRef=2` corrige texto    |
| 1                      | T56 ND               | `CodRef=3` corrige montos   |

La cantidad total y los tipos adicionales deben seguir el manual aplicable a la empresa. Si emite también guías o exentas, agrega 2-3 de cada uno.

## Reglas técnicas

### Documentos necesarios para la muestra impresa

Crítico antes de enviar

La etapa posterior de muestra impresa requiere disponer, como mínimo, de:

- Dos facturas electrónicas.
- Una nota de crédito.
- Una nota de débito.

Si la simulación no incluye esos tipos de documentos, puede ser imposible completar la validación posterior.

Planificar la muestra impresa antes de generar y subir la simulación, porque una vez enviada y declarada no se dispone de un mecanismo sencillo para reemplazarla.

### Fechas de los DTE y del CAF

Error observado:

```
Fecha del documento debe ser mayor
o igual a la fecha autorizada por el SII en el CAF
```

**Causa:** Se intentó utilizar una fecha de emisión anterior a la autorización contenida en el CAF.

**Solución:** En el caso probado, generar los documentos con fechas válidas del mes actual y no utilizar fechas anteriores a la autorización del CAF ni fechas futuras arbitrarias.

### NO referenciar el set en la simulación

A diferencia de la etapa anterior, **los DTE de la simulación NO llevan `<Referencia>` al SET**. Son operaciones simuladas, no casos del set.

NC y ND sí llevan referencia al documento que corrigen (línea 1), no al set.

### RUTs receptores válidos

Para generar RUTs ficticios con DV válido:

```python
def _dv(rut_num: int) -> str:
    """Calcula el dígito verificador chileno."""
    s = 0; m = 2
    for d in reversed(str(rut_num)):
        s += int(d) * m
        m = m + 1 if m < 7 else 2
    r = 11 - (s % 11)
    return {10: 'K', 11: '0'}.get(r, str(r))
```

Generar RUTs entre 1.000.000 y 25.000.000 para personas naturales, 50.000.000+ para empresas (rango típico).

### ND "corrige montos" = recargo (no descuento)

Cuando la ND corrige montos, **suma al documento original** (no resta). Item típico:

```python
{
    "NroLinDet": 1,
    "NmbItem": "RECARGO POR INTERESES MORATORIOS",
    "QtyItem": 1,
    "PrcItem": 25000,                    # monto fijo
    "Impuesto": [{"CodImp": 14, "TasaImp": 19.0}]
}
```

### NC "corrige texto"

```python
{
    "NroLinDet": 1,
    "NmbItem": "IMP. CORRIGE TEXTO",
    "QtyItem": 1,
    "PrcItem": 0
}
```

### Uso de operaciones simuladas

Fue posible crear facturas y notas de crédito para las pruebas sin partir necesariamente de operaciones históricas.

## Envío y revisión

Mismo endpoint que set de pruebas (`maullin.sii.cl/cgi_dte/UPL/DTEUpload`).

- Enviar **todos los DTEs en un solo `<EnvioDTE>`**.
- Obtener track ID.
- Solicitar revisión en el portal SII → "Solicitud de revisión de simulación".
- El SII responde por correo.

**Recomendación:** Preparar y validar el lote completo antes de enviarlo, evitando dividirlo en múltiples sobres sin confirmación de que el SII lo permita para esa etapa.

## Importante: guardar los XMLs individuales

**Después del envío exitoso de la simulación, guarda cada DTE individual** (extraído del `<EnvioDTE>` consolidado). Los necesitarás en la etapa siguiente de **Documentos Impresos** — el SII te pedirá las muestras de PDFs de la simulación.

## Errores típicos

- ❌ Usar RUTs ficticios con DV inválido — rechazo por DV.
- ❌ ND corrige montos resta en vez de sumar — rechazo de monto.
- ❌ NC corrige giro intenta usar `IndExe=1` cuando la factura original era afecta — rechazo de SRH.
- ❌ Olvidar agregar la referencia al documento original en NC/ND.
