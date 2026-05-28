# 3. Simulación operativa

Segunda etapa: emitir un volumen de DTEs simulando operación real, no datos predefinidos del SII.

## Qué pide el SII

Generar N documentos (típicamente 20-25) con datos **paralelos a la operación real**:
- RUTs receptores ficticios pero con dígito verificador válido
- Glosas variadas (acordes al giro de la empresa)
- Cantidades y precios diversos
- Mix de tipos: facturas, NC, ND (no es obligatorio incluir todos los tipos, pero al menos T33, una NC y una ND es lo recomendable)

## Mix sugerido (basado en proceso aprobado)

| Cantidad | Tipo | Notas |
|---|---|---|
| ~18 | T33 facturas afectas | Variedad de glosas y montos |
| 1 | T61 NC | `CodRef=2` corrige texto, 1 línea genérica |
| 1 | T56 ND | `CodRef=3` corrige montos, recargo con monto fijo |

Si tu empresa emite también guías o exentas, agrega 2-3 de cada uno.

## Reglas técnicas

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

### NC "corrige texto" — 1 línea genérica

```python
{
    "NroLinDet": 1,
    "CdgItem": {"VlrCodigo": "NO_PRODUCT"},  # para saltar validación dansanti
    "NmbItem": "IMP. CORRIGE TEXTO",
    "QtyItem": 1,
    "PrcItem": 0
}
```

## Envío y revisión

Mismo endpoint que set de pruebas (`maullin.sii.cl/cgi_dte/UPL/DTEUpload`).

- Enviar **todos los DTEs en un solo `<EnvioDTE>`**.
- Obtener track ID.
- Solicitar revisión en el portal SII → "Solicitud de revisión de simulación".
- El SII responde por correo.

## Importante: guardar los XMLs individuales

**Después del envío exitoso de la simulación, guarda cada DTE individual** (extraído del `<EnvioDTE>` consolidado). Los necesitarás en la etapa siguiente de **Documentos Impresos** — el SII te pedirá los PDFs de algunos de la simulación.

## Errores típicos

- ❌ Usar RUTs ficticios con DV inválido — rechazo por DV.
- ❌ ND corrige montos resta en vez de sumar — rechazo de monto.
- ❌ NC corrige giro intenta usar `IndExe=1` cuando la factura original era afecta — rechazo de SRH.
- ❌ Olvidar agregar la referencia al documento original en NC/ND.
