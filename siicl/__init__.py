"""siicl - Cliente Python autosuficiente para SII Chile.

Paquete para emisión de Documentos Tributarios Electrónicos (DTE) y
Boletas Electrónicas en el Servicio de Impuestos Internos de Chile.

Módulos principales:
    types      Tipos básicos (RUT, fechas, montos).
    firma      Firma XML con certificado PFX. Semilla y token.
    caf        Lectura y parseo de archivos CAF.
    timbre     Generación de TED y código de barras PDF417.
    dte        Construcción de DTE (factura, boleta, NC, ND, guía, etc).
    envio      Wrappers EnvioDTE / EnvioBOLETA / ConsumoFolios.
    cliente    Cliente HTTP para SOAP (maullin/palena) y REST (pangal/rahue).
    pdf        Renderizado de DTE a PDF con timbre PDF417 incrustado.
    validacion Validación contra XSD oficial del SII.

Los módulos se importan bajo demanda con `from siicl import <módulo>` para
evitar dependencias circulares y carga eager de subdependencias pesadas.
"""

__version__ = "0.1.0"
