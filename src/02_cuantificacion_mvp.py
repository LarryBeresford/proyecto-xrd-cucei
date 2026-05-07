import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import simpson
import os
import warnings

warnings.filterwarnings('ignore')

# --- 1. CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_EXCEL = os.path.join(BASE_DIR, 'data', 'raw', 'datos_cucei.xlsx')
DIR_FIGURAS = os.path.join(BASE_DIR, 'reports', 'figures')

# --- 2. CARGA DE DATOS ---
df = pd.read_excel(ARCHIVO_EXCEL, sheet_name='XRD diferentes tiempos')
for col in df.columns:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# --- 3. AISLAMIENTO DEL PICO PRINCIPAL (Plano basal del HDL) ---
# El pico principal está aproximadamente entre los 8 y 15 grados 2-theta
limite_inf = 8.0
limite_sup = 15.0

# Datos 0 Horas (Intacto)
mask_0h = (df['Angulo 2tetha'] >= limite_inf) & (df['Angulo 2tetha'] <= limite_sup)
x_0h = df.loc[mask_0h, 'Angulo 2tetha'].values
y_0h = df.loc[mask_0h, 'HDL 0H'].fillna(0).values

# Datos 96 Horas (Degradado)
mask_96h = (df['Angulo 2tetha.1'] >= limite_inf) & (df['Angulo 2tetha.1'] <= limite_sup)
x_96h = df.loc[mask_96h, 'Angulo 2tetha.1'].values
y_96h = df.loc[mask_96h, 'HDL 96H'].fillna(0).values

# --- 4. CÁLCULO MATEMÁTICO (Área Bajo la Curva) ---
area_0h = simpson(y=y_0h, x=x_0h)
area_96h = simpson(y=y_96h, x=x_96h)
perdida_porcentaje = ((area_0h - area_96h) / area_0h) * 100

# --- 5. VISUALIZACIÓN DE ALTO IMPACTO ---
plt.figure(figsize=(9, 5))

# Sombrear las áreas calculadas
plt.fill_between(x_0h, y_0h, color='#002D62', alpha=0.3, label=f'Área Intacta (0h): {area_0h:.2f} U.A.')
plt.fill_between(x_96h, y_96h, color='#F0A800', alpha=0.6, label=f'Área Degradada (96h): {area_96h:.2f} U.A.')

# Líneas de los picos
plt.plot(x_0h, y_0h, color='#002D62', linewidth=2)
plt.plot(x_96h, y_96h, color='#F0A800', linewidth=2)

# Textos y diseño
plt.title('MVP: Cuantificación del Desgaste Estructural (HDL)', fontsize=14, fontweight='bold')
plt.xlabel('Ángulo 2θ', fontsize=12)
plt.ylabel('Intensidad de Difracción', fontsize=12)

# Añadir el KPI central como texto en la gráfica
texto_kpi = f"PÉRDIDA DE CRISTALINIDAD:\n{perdida_porcentaje:.1f}%"
plt.text(13, max(y_0h)*0.8, texto_kpi, fontsize=12, fontweight='bold', 
         bbox=dict(facecolor='#f8d7da', edgecolor='#dc3545', boxstyle='round,pad=0.5'))

plt.legend(loc='upper left')
plt.grid(True, linestyle='--', alpha=0.4)
plt.tight_layout()

# Guardar
ruta_salida = os.path.join(DIR_FIGURAS, 'MVP_Cuantificacion.png')
plt.savefig(ruta_salida, dpi=300)
print(f"¡MVP generado con éxito!\nRevisa la imagen en: {ruta_salida}")