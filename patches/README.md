# Patches a librerías open-source

Esta carpeta contiene parches a librerías de terceros para arreglar bugs conocidos en certificación SII. Ver [`../docs/bugs-dansanti-patches.md`](../docs/bugs-dansanti-patches.md) para el detalle de cada bug.

## Patches disponibles

| Archivo | Librería | Versión | Bugs que arregla |
|---|---|---|---|
| [`dansanti-fe-0.21.2-boletas.patch`](dansanti-fe-0.21.2-boletas.patch) | `dansanti/facturacion_electronica` | 0.21.2 | Referencia de boletas pierde el SET; RUTProvSW dentro de docstring |

## Cómo aplicar

### Aplicar a un venv local

```bash
# Identificar la ruta del paquete
PKG_DIR=$(python -c "import facturacion_electronica, os; print(os.path.dirname(facturacion_electronica.__file__))")
echo "$PKG_DIR"
# Ejemplo: /tu/proyecto/.venv/lib/python3.12/site-packages/facturacion_electronica

# Aplicar el patch
patch -d "$PKG_DIR" -p1 < patches/dansanti-fe-0.21.2-boletas.patch

# Verificar
.venv/bin/python -c "import facturacion_electronica; print('OK')"
```

### Revertir un patch

```bash
patch -R -d "$PKG_DIR" -p1 < patches/dansanti-fe-0.21.2-boletas.patch
```

### Aplicar tras un `pip install --upgrade`

Si actualizas el paquete, los patches se pierden. Tenés que reaplicarlos. Alternativas para evitarlo:

1. **Fork del paquete** con los patches integrados (recomendado para uso intensivo en producción).
2. **`pip install --no-deps facturacion_electronica==0.21.2`** para pinear la versión + script post-install que aplique patches.
3. **Wrapper** que monkey-patche la librería en runtime (no recomendado por mantenibilidad).

## Cómo generar un nuevo patch

Si arreglas un bug y querés contribuir el patch al repo:

```bash
cd "$PKG_DIR"
cp -r . /tmp/before
# editás los archivos
diff -ruN /tmp/before . > /tu/repo/patches/dansanti-fe-VERSION-tubug.patch
```

Subí el `.patch` con un nombre descriptivo y documentalo en [`bugs-dansanti-patches.md`](../docs/bugs-dansanti-patches.md).
