# 4. Intercambio de Información

Tercera etapa: el SII te envía un XML con 2 DTEs (uno tiene tu RUT como receptor, otro NO) y tienes que responder con 3 archivos XML que demuestren que sabes procesar intercambio.

## Lo que el SII envía

Un único XML `EnvioDTE` con 2 facturas T33:

- **DTE A:** `RUTRecep = TU_RUT` → te corresponde a ti, debes aceptarlo (con o sin reclamo) y emitir acuse de mercaderías.
- **DTE B:** `RUTRecep = OTRO_RUT` → NO te corresponde, debes rechazarlo en el intercambio.

El correo del SII trae el XML adjunto (típicamente `ENVIO_DTE_<num>.xml`).

## Lo que tienes que responder

**3 archivos XML separados**, todos enviados al portal SII en el formulario de "Subir archivos del Intercambio":

### Archivo 1: Respuesta de Intercambio

Wrapper `<RespuestaDTE>` con schema `RespuestaEnvioDTE_v10.xsd`. Indica al SII si aceptaste o rechazaste cada DTE del envío.

```xml
<RespuestaDTE xmlns="http://www.sii.cl/SiiDte" version="1.0">
  <Resultado ID="Resp123">
    <Caratula version="1.0">
      <RutResponde>76123456-7</RutResponde>      <!-- tu RUT -->
      <RutRecibe>EMISOR_ORIGINAL-K</RutRecibe>   <!-- del DTE -->
      <IdRespuesta>1</IdRespuesta>
      <NroDetalles>2</NroDetalles>
      <TmstFirmaResp>2026-05-27T12:34:56</TmstFirmaResp>
    </Caratula>
    <RecepcionEnvio>
      <NmbEnvio>ENVIO_DTE_NUM.xml</NmbEnvio>
      <FchRecep>2026-05-27T12:34:56</FchRecep>
      <CodEnvio>1</CodEnvio>
      <EnvioDTEID>...</EnvioDTEID>
      <Digest>...</Digest>
      <RutEmisor>EMISOR_RUT</RutEmisor>
      <RutReceptor>76123456-7</RutReceptor>
      <EstadoRecepEnv>0</EstadoRecepEnv>
      <RecepEnvGlosa>Envio Recibido Conforme</RecepEnvGlosa>
      <NroDTE>2</NroDTE>
      <RecepcionDTE>
        <TpoDTE>33</TpoDTE>
        <NroDTE>FOLIO_DTE_A</NroDTE>
        <RutEmisor>EMISOR_RUT</RutEmisor>
        <RutRecep>76123456-7</RutRecep>          <!-- tu RUT, dirigido a ti -->
        <MntTotal>31294</MntTotal>
        <EstadoRecepDTE>0</EstadoRecepDTE>
        <RecepDTEGlosa>DTE Recibido OK</RecepDTEGlosa>
      </RecepcionDTE>
      <RecepcionDTE>
        <TpoDTE>33</TpoDTE>
        <NroDTE>FOLIO_DTE_B</NroDTE>
        <RutEmisor>EMISOR_RUT</RutEmisor>
        <RutRecep>OTRO_RUT-K</RutRecep>          <!-- NO eres tú -->
        <MntTotal>VALOR_DTE_B</MntTotal>
        <EstadoRecepDTE>3</EstadoRecepDTE>       <!-- 3 = rechazado por receptor distinto -->
        <RecepDTEGlosa>RUT receptor no corresponde</RecepDTEGlosa>
      </RecepcionDTE>
    </RecepcionEnvio>
  </Resultado>
  <Signature>...</Signature>
</RespuestaDTE>
```

### Archivo 2: Recibo de Mercaderías

Wrapper `<EnvioRecibos>` con schema `EnvioRecibos_v10.xsd`. Solo para el DTE que te corresponde (el A).

```xml
<EnvioRecibos xmlns="http://www.sii.cl/SiiDte" version="1.0">
  <SetRecibos ID="SetRecibos1">
    <Caratula version="1.0">
      <RutResponde>76123456-7</RutResponde>
      <RutRecibe>EMISOR_RUT-K</RutRecibe>          <!-- ⚠️ el del emisor original -->
      <NroDetalles>1</NroDetalles>
      <TmstFirmaEnv>2026-05-27T12:34:56</TmstFirmaEnv>
    </Caratula>
    <Recibo version="1.0">
      <DocumentoRecibo ID="Recibo1">
        <TipoDoc>33</TipoDoc>
        <Folio>FOLIO_DTE_A</Folio>
        <FchEmis>FECHA_DTE_A</FchEmis>
        <RUTEmisor>EMISOR_RUT-K</RUTEmisor>
        <RUTRecep>76123456-7</RUTRecep>
        <MntTotal>31294</MntTotal>                  <!-- ⚠️ valor real, NO 0 -->
        <Recinto>OFICINA</Recinto>
        <RutFirma>11111111-1</RutFirma>            <!-- tu RUT firmante -->
        <Declaracion>El acuse de recibo...</Declaracion>
        <TmstFirmaRecibo>2026-05-27T12:34:56</TmstFirmaRecibo>
      </DocumentoRecibo>
      <Signature>...</Signature>
    </Recibo>
  </SetRecibos>
  <Signature>...</Signature>
</EnvioRecibos>
```

⚠️ **Atención**:
- `RutRecibe` en la Carátula debe ser el **RUT del emisor original** (a quien le respondes), NO tu RUT.
- `MntTotal` debe ser el valor real del DTE, NO 0.

### Archivo 3: Resultado Aprobación Comercial

Wrapper `<RespuestaDTE>` (otra vez) con bloque `<ResultadoDTE>` esta vez. Indica si comercialmente aceptas o reclamas el DTE.

```xml
<RespuestaDTE xmlns="http://www.sii.cl/SiiDte" version="1.0">
  <Resultado ID="Resp2">
    <Caratula version="1.0">
      <RutResponde>76123456-7</RutResponde>
      <RutRecibe>EMISOR_RUT-K</RutRecibe>
      <IdRespuesta>2</IdRespuesta>
      <NroDetalles>1</NroDetalles>
      <TmstFirmaResp>2026-05-27T12:34:56</TmstFirmaResp>
    </Caratula>
    <ResultadoDTE>
      <TpoDTE>33</TpoDTE>
      <Folio>FOLIO_DTE_A</Folio>
      <FchEmis>FECHA_DTE_A</FchEmis>
      <RUTEmisor>EMISOR_RUT-K</RUTEmisor>
      <RUTRecep>76123456-7</RUTRecep>
      <MntTotal>31294</MntTotal>
      <EstadoDTE>0</EstadoDTE>                 <!-- 0 = aceptado, 2 = reclamado -->
      <EstadoDTEGlosa>DTE Aceptado OK</EstadoDTEGlosa>
    </ResultadoDTE>
  </Resultado>
  <Signature>...</Signature>
</RespuestaDTE>
```

## Cómo subir al SII

Portal SII → Certificación → "Subir archivos de Intercambio". Hay 3 botones, uno por cada archivo. Suba en orden.

## Errores típicos

- ❌ Poner tu RUT como `RutRecibe` en el recibo de mercaderías. Debe ser el emisor original.
- ❌ Dejar `MntTotal=0` en el recibo. Debe ser el valor real del DTE.
- ❌ Olvidar firmar el `DocumentoRecibo` individualmente (lleva firma propia, además de la del sobre).
- ❌ Usar esquema `EnvioBoleta_v11.xsd` en lugar de `EnvioRecibos_v10.xsd` en el archivo 2.
