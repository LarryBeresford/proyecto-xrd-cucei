"""
Configuración global: rutas, constantes físicas y paleta institucional.
"""
import os

# --- RUTAS BASE ---
# BASE_DIR = raíz del proyecto (padre de src/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR_RAW = os.path.join(BASE_DIR, 'data', 'raw')
DIR_PROCESSED = os.path.join(BASE_DIR, 'data', 'processed')
DIR_FIGURAS = os.path.join(BASE_DIR, 'reports', 'figures')
DIR_REPORTES = os.path.join(BASE_DIR, 'reports')
ARCHIVO_EXCEL_DEFAULT = os.path.join(DIR_RAW, 'datos_cucei.xlsx')
ARCHIVO_EXCEL_FTIR_DEFAULT = os.path.join(DIR_RAW, 'datos_ftir_degradacion.xlsx')

for _d in (DIR_PROCESSED, DIR_FIGURAS, DIR_REPORTES):
    os.makedirs(_d, exist_ok=True)

# --- CONSTANTES FÍSICAS ---
# Longitud de onda Cu-K-alpha (angstroms), fuente estándar en difractómetros
# de laboratorio (Bruker D2 Phaser, PANalytical X'Pert, etc.). Si el equipo
# usado en el laboratorio emplea otra fuente (p.ej. Co-K-alpha = 1.7902 A),
# este valor debe actualizarse y documentarse en el protocolo.
LONGITUD_ONDA_CU_KALPHA_ANGSTROM = 1.5406

# Tiempos de muestreo cristalográfico (horas). Deben coincidir exactamente
# con las columnas 'HDL {t}H' de la hoja 'XRD diferentes tiempos'.
TIEMPOS_XRD_HORAS = [0, 24, 48, 72, 96]

# Ventana por defecto del pico basal principal del HDL (grados 2theta).
LIMITE_INF_DEFAULT = 8.0
LIMITE_SUP_DEFAULT = 15.0

# --- FTIR ---
# Ventana por defecto de la banda característica a analizar (cm-1).
# 1000-1200 cm-1 fue elegida por ser la región con el pico más prominente
# y mejor resuelto en el espectro de HDL 0h (no está en el borde del
# espectro, a diferencia de la región >3700 cm-1 o la banda ~2165 cm-1,
# que coincide con la zona típica de interferencia atmosférica de CO2).
# IMPORTANTE: la asignación química de esta banda (a qué modo vibracional
# corresponde) debe confirmarse con el asesor/director antes de
# presentarla como evidencia en el protocolo o documento final.
FTIR_BANDA_INF_DEFAULT = 1000.0
FTIR_BANDA_SUP_DEFAULT = 1200.0
FTIR_MATERIAL_DEFAULT = "HDL"

# --- PALETA INSTITUCIONAL UDEG / CUCEI ---
C_AZUL = '#002D62'
C_AZUL_RGB = (0, 45, 98)
C_DORADO = '#F0A800'
C_DORADO_RGB = (240, 168, 0)
C_GRIS_TEXTO = '#3A3A3A'
C_FONDO_TARJETA = '#F5F7FA'
