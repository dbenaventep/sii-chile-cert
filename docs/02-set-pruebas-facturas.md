# 2. Set de Pruebas de Facturas (T33, T34, T46, T52, T56, T61)

Primera etapa del proceso de certificación. El SII envía un set con varios casos y debes generar los DTE correspondientes, enviarlos en un único `<EnvioDTE>` y solicitar revisión.

## Visión general

El "Set de Pruebas" en realidad son **varios sets** según los tipos de documento que vas a emitir:

- **Set Básico** (T33 facturas + T61 NC + T56 ND): obligatorio si emites facturas afectas
- **Set Guías de Despacho** (T52): obligatorio si emites guías
- **Set Exentas** (T34 + T61 + T56): obligatorio si emites facturas exentas
- **Set Compras** (T46): obligatorio si emites facturas de compra con retención

Cada set tiene un ID único asignado por el SII (ej. `XXXXXXX`). El ID aparece en el correo del SII y en el rechazo si falla.

## Endpoint

`https://maullin.sii.cl/cgi_dte/UPL/DTEUpload` por SOAP.

Token obtenido de `https://maullin.sii.cl/DTEWS/CrSeed.jws?WSDL` + `GetTokenFromSeed.jws`.

## Wrapper XML

```xml
<EnvioDTE xmlns="http://www.sii.cl/SiiDte" version="1.0">
  <SetDTE ID="SetBasicoCASA">
    <Caratula version="1.0">
      <RutEmisor>76123456-0</RutEmisor>
      <RutEnvia>11111111-1</RutEnvia>
      <RutReceptor>60803000-K</RutReceptor>
      <FchResol>2026-04-28</FchResol>
      <NroResol>0</NroResol>
      <TmstFirmaEnv>2026-05-27T12:34:56</TmstFirmaEnv>
      <SubTotDTE><TpoDTE>33</TpoDTE><NroDTE>4</NroDTE></SubTotDTE>
      <SubTotDTE><TpoDTE>61</TpoDTE><NroDTE>3</NroDTE></SubTotDTE>
      <SubTotDTE><TpoDTE>56</TpoDTE><NroDTE>1</NroDTE></SubTotDTE>
    </Caratula>
    <DTE>...</DTE>
    <DTE>...</DTE>
    ...
  </SetDTE>
  <Signature>...</Signature>
</EnvioDTE>
```

## Referencia obligatoria al SET en cada DTE

```xml
<Referencia>
  <NroLinRef>1</NroLinRef>
  <TpoDocRef>SET</TpoDocRef>
  <FolioRef>32</FolioRef>                <!-- folio del DTE propio -->
  <FchRef>2026-04-29</FchRef>            <!-- fecha del DTE -->
  <RazonRef>CASO XXXXXXX-1</RazonRef>    <!-- ID del set + número del caso -->
</Referencia>
```

**Diferencia con boletas:** facturas usan `<TpoDocRef>SET</TpoDocRef>` + `<FolioRef>` + `<FchRef>` + RazonRef con el ID del set. Boletas usan solo `<CodRef>SET</CodRef> + <RazonRef>CASO-N</RazonRef>`.

## Para Notas de Crédito y Notas de Débito

Llevan **dos referencias**: la al SET (línea 1) y la al documento original que corrigen (línea 2):

```xml
<Referencia>
  <NroLinRef>1</NroLinRef>
  <TpoDocRef>SET</TpoDocRef>
  <FolioRef>46</FolioRef>
  <FchRef>2026-04-29</FchRef>
  <RazonRef>CASO XXXXXXX-5</RazonRef>
</Referencia>
<Referencia>
  <NroLinRef>2</NroLinRef>
  <TpoDocRef>33</TpoDocRef>                    <!-- factura referenciada -->
  <FolioRef>32</FolioRef>                       <!-- folio de la factura original -->
  <FchRef>2026-04-29</FchRef>
  <CodRef>2</CodRef>                            <!-- 1 anula, 2 corrige texto, 3 corrige monto -->
  <RazonRef>Dice: GIRO PRUEBAS y debe decir: NUEVO GIRO PRUEBAS</RazonRef>
</Referencia>
```

`CodRef`:

- `1` anula documento de referencia
- `2` corrige texto del documento de referencia
- `3` corrige montos

### Mito sobre `RazonRef` y «Donde dice: debe decir:»

Según nuestra investigación, existen diferentes implementaciones sobre "Dice:" y "debe decir:" y aparentemente SII no valida esta frase. La librería dansanti usada en algunos proyectos puede validar el texto de `RazonRef` con más restricciones que el SII.

Según [la respuesta actualizada el octubre de 2022 del SII](https://www.sii.cl/preguntas_frecuentes/factura_electronica/001_003_3731.htm), la frase literal «Dice: debe decir:» debería estar presente en el detalle del DTE.

En nuestra experiencia con `CodRef=2`: El SII aceptó la nota sin exigir que `RazonRef` tuviera literalmente la expresión «Dice: debe decir:». La explicación se incluyó en el detalle mediante `DscItem`:

```
<DscItem>Donde dice: VENTA AL POR MENOR DE ALIMENTOS EN COMER debe decir: ACTIVIDADES DE RESTAURANTES</DscItem>
```

Esta ubicación permitió aprovechar el espacio disponible en `DscItem`, cuyo límite utilizado fue de 1.000 caracteres.

## Casos típicos por set

### Set Básico (T33)

Típicamente 8 casos:

| #   | Caso                               | Tipo DTE | Notas                                                      |
| --- | ---------------------------------- | -------- | ---------------------------------------------------------- |
| 1   | Factura simple con 2 ítems afectos | T33      | —                                                          |
| 2   | Factura con descuento por línea    | T33      | `DescuentoPct` en cada línea                               |
| 3   | Factura mixta (afecto + exento)    | T33      | `IndExe=1` en línea exenta                                 |
| 4   | Factura con descuento global       | T33      | `<DscRcgGlobal>` separado                                  |
| 5   | NC corrige giro de factura caso 1  | T61      | 1 línea, monto=0                                           |
| 6   | NC devolución mercaderías          | T61      | replica items de factura original con cantidades devueltas |
| 7   | NC anula factura caso 3            | T61      | replica items completos de la factura                      |
| 8   | ND anula NC caso 5                 | T56      | replica items de la factura original                       |

### Set Guías (T52)

- Traslado interno: `IndTraslado=5`, receptor = emisor
- Venta con entrega: `IndTraslado=1`, `TipoDespacho=2`
- Venta retiro cliente: `IndTraslado=1`, `TipoDespacho=1`

### Set Exentas (T34)

Igual estructura que set básico, pero los ítems van con `IndExe=1`, sin IVA.

### Set Compra (T46)

Factura de compra electrónica con retención total de IVA. Caso clásico:

- `<OtrosImp><CodImp>15</CodImp>` (cambio sujeto IVA)
- `<MntTotal>` = Neto (no Neto+IVA, porque hay retención total)
- En libro de compras del mes: `<TpoImp>1</TpoImp>`

## Recomendaciones operativas

1. **Genera todos los DTEs del set en un solo envío** (un solo `<EnvioDTE>` con todos los `<DTE>` adentro). El SII espera esto.
2. **Antes de enviar al SII, valida el XML contra el XSD oficial localmente** (ver [`endpoints-sii.md`](endpoints-sii.md)).
3. **Si falla un set y querés intentar de nuevo**: usar **folios distintos** para los nuevos DTEs. Los anteriores quedaron consumidos.
4. **Si el set queda SRH irrecuperable**: pedir un nuevo set al SII (no confundir con pedir más folios).

## Errores típicos en este paso

- ❌ Usar `<TpoDocRef>SET</TpoDocRef>` con `<RazonRef>CASO-1</RazonRef>` (sin ID del set) — rechazo silencioso.
- ❌ Olvidar la segunda referencia en NC/ND al documento original.
- ❌ Mandar el set por pangal REST (eso es solo para boletas en prod).

Para más errores ver [`gotchas.md`](gotchas.md).
