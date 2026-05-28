# SII Chile - Certificación DTE y Boletas Electrónicas

Guía técnica completa para certificar emisores de documentos tributarios electrónicos ante el SII de Chile, basada en experiencia real de proceso completo (Facturas T33, Notas Crédito T61, Notas Débito T56, Guías Despacho T52, Facturas Exentas T34, Facturas Compra T46, Boletas Electrónicas T39).

**Objetivo:** que nadie más pierda días buscando información dispersa, mal documentada o desactualizada.

## ¿Qué hay aquí?

- 📖 **`docs/`** - Manuales paso a paso por etapa del proceso de certificación. Lo más valioso del repo.
- 📋 **`examples/`** - Ejemplos JSON anonimizados de cada tipo de documento.
- 🔧 **`patches/`** - Parches a librerías open-source populares (ej. dansanti `facturacion_electronica`) que tienen bugs conocidos en certificación.
- 📐 **`xsd/`** - Schemas XSD oficiales vigentes del SII (descargados de sii.cl), para validación local.

## ¿Por qué este repo existe?

Certificarse ante el SII de Chile como emisor electrónico es un proceso documentado a medias, donde:

- La documentación oficial mezcla versiones de 2009, 2018, 2023 y posteriores sin marcar cuál aplica.
- Las librerías open-source disponibles tienen XSDs locales modificados que **no coinciden con los XSDs oficiales del SII**.
- El SII responde con mensajes de error engañosos (`SCH-00001`, `HED-3-211`, `El Documento no esta en el envio`) que no apuntan al problema real.
- Boletas electrónicas (T39) post-2023 tienen un flujo completamente distinto a facturas, y la documentación pública no lo separa claramente.

## Mapa rápido por etapa del proceso

| # | Etapa | Doc |
|---|---|---|
| 1 | Setup inicial del emisor en cert SII | [`docs/01-setup-emisor.md`](docs/01-setup-emisor.md) |
| 2 | Set de Pruebas Facturas (T33, T34, T46, T52, T61, T56) | [`docs/02-set-pruebas-facturas.md`](docs/02-set-pruebas-facturas.md) |
| 3 | Simulación operativa | [`docs/03-simulacion.md`](docs/03-simulacion.md) |
| 4 | Intercambio de Información | [`docs/04-intercambio.md`](docs/04-intercambio.md) |
| 5 | Documentos Impresos (PDF + PDF417) | [`docs/05-documentos-impresos.md`](docs/05-documentos-impresos.md) |
| 6 | **Set de Pruebas Boletas (T39)** ⭐ el más sub-documentado | [`docs/06-set-pruebas-boletas.md`](docs/06-set-pruebas-boletas.md) |
| 7 | Resolución y paso a producción | [`docs/07-resolucion-produccion.md`](docs/07-resolucion-produccion.md) |

## Referencias técnicas

| Tema | Doc |
|---|---|
| Mapa completo de endpoints SII (cert/prod, SOAP/REST) | [`docs/endpoints-sii.md`](docs/endpoints-sii.md) |
| Diferencias XSD oficial vs XSDs de librerías open-source | [`docs/xsd-oficial-vs-dansanti.md`](docs/xsd-oficial-vs-dansanti.md) |
| Bugs conocidos en dansanti y sus parches | [`docs/bugs-dansanti-patches.md`](docs/bugs-dansanti-patches.md) |
| Lista de "gotchas" - errores comunes y sus causas reales | [`docs/gotchas.md`](docs/gotchas.md) |

## Aprendizajes clave (TL;DR)

1. **Boletas T39 en certificación se envían por `maullin.sii.cl/cgi_dte/UPL/DTEUpload` (SOAP)**, NO por el endpoint REST de pangal. REST es solo para producción operativa post-2023.
2. **La referencia al SET en boletas es minimal**: solo `<NroLinRef> + <CodRef>SET</CodRef> + <RazonRef>CASO-N</RazonRef>`. Sin `<TpoDocRef>`, sin `<FolioRef>`, sin `<FchRef>` (esos son del flujo de facturas).
3. **dansanti `facturacion_electronica` v0.21.x** tiene 3 bugs que rompen certificación de boletas y un XSD local con campos no oficiales (`TpoDocRef`, `FolioRef`, `FchRef` en boletas). Patches en `patches/`.
4. **El XSD oficial del SII** (`https://www.sii.cl/factura_electronica/`) es la fuente de verdad, no los XSDs empaquetados en librerías.
5. **Antes de cada envío al SII, leer el XML generado** y verificar contra el XSD oficial. La validación `--validate` de las librerías chequea matemáticas y XSD local, pero no garantiza que el SII vaya a aceptarlo.
6. **Folios quemados no se recuperan** — un envío rechazado consume folios igual. Verificar exhaustivamente antes de enviar.

## Estado del proyecto

- ✅ Documentación de las 7 etapas del proceso
- ✅ Ejemplos JSON anonimizados
- ✅ Patches dansanti documentados
- ⏳ Módulos Python autosuficientes (sin dependencia de librerías de terceros) — en desarrollo

## Contribuciones

Si certificaste un emisor y encontraste algo no documentado aquí, abre un PR. Si una sección está obsoleta porque el SII cambió algo, también.

## Licencia

MIT. Ver [`LICENSE`](LICENSE).

## Disclaimer

Este repo es de uso comunitario. No tiene afiliación con el SII de Chile. La información acá puede quedar obsoleta si el SII cambia procesos. Antes de operar en producción real verifica contra la documentación oficial vigente de [sii.cl](https://www.sii.cl).
