import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import simpson

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Analizador XRD - CUCEI", layout="wide", page_icon="🔬")

# --- ENCABEZADO ---
st.title("🔬 Plataforma de Análisis: Degradación de HDL")
st.markdown("Sube tu archivo Excel o CSV del difractómetro para calcular matemáticamente la pérdida de cristalinidad.")

# --- BARRA LATERAL (CONTROLES INTERACTIVOS) ---
st.sidebar.header("⚙️ Parámetros de Integración")
st.sidebar.markdown("Ajusta los límites del plano basal para calcular el Área Bajo la Curva (AUC):")
limite_inf = st.sidebar.slider("Límite Inferior (Ángulo 2θ)", min_value=5.0, max_value=12.0, value=8.0, step=0.1)
limite_sup = st.sidebar.slider("Límite Superior (Ángulo 2θ)", min_value=12.0, max_value=20.0, value=15.0, step=0.1)

# --- CARGADOR DE ARCHIVOS ---
archivo_subido = st.file_uploader("Arrastra tu archivo Excel aquí", type=["xlsx", "xls", "csv"])

if archivo_subido is not None:
    # 1. Leer los datos
    try:
        if archivo_subido.name.endswith('.csv'):
            df = pd.read_csv(archivo_subido)
        else:
            df = pd.read_excel(archivo_subido, sheet_name='XRD diferentes tiempos')
            
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        st.success("¡Archivo procesado con éxito!")
        
        # 2. Filtrar y Aislar Datos según los sliders
        mask_0h = (df['Angulo 2tetha'] >= limite_inf) & (df['Angulo 2tetha'] <= limite_sup)
        x_0h = df.loc[mask_0h, 'Angulo 2tetha'].values
        y_0h = df.loc[mask_0h, 'HDL 0H'].fillna(0).values

        mask_96h = (df['Angulo 2tetha.1'] >= limite_inf) & (df['Angulo 2tetha.1'] <= limite_sup)
        x_96h = df.loc[mask_96h, 'Angulo 2tetha.1'].values
        y_96h = df.loc[mask_96h, 'HDL 96H'].fillna(0).values

        # 3. Calcular Degradación
        area_0h = simpson(y=y_0h, x=x_0h)
        area_96h = simpson(y=y_96h, x=x_96h)
        perdida_porcentaje = ((area_0h - area_96h) / area_0h) * 100

        # 4. Mostrar Resultados (Métricas tipo Dashboard)
        col1, col2, col3 = st.columns(3)
        col1.metric("Área Intacta (0h)", f"{area_0h:.2f} U.A.")
        col2.metric("Área Degradada (96h)", f"{area_96h:.2f} U.A.")
        col3.metric("Pérdida de Cristalinidad", f"{perdida_porcentaje:.1f}%", "- Degradación", delta_color="inverse")

        # 5. Generar Gráfica Interactiva
        st.markdown("### Visualización del Desgaste Estructural")
        fig, ax = plt.subplots(figsize=(10, 4))
        
        ax.fill_between(x_0h, y_0h, color='#002D62', alpha=0.3, label='Intacto (0h)')
        ax.fill_between(x_96h, y_96h, color='#F0A800', alpha=0.6, label='Degradado (96h)')
        ax.plot(x_0h, y_0h, color='#002D62', linewidth=2)
        ax.plot(x_96h, y_96h, color='#F0A800', linewidth=2)
        
        ax.set_xlabel('Ángulo 2θ')
        ax.set_ylabel('Intensidad')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.4)
        
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Error al leer el archivo. Asegúrate de que tenga el formato correcto. Detalles: {e}")
else:
    st.info("Esperando archivo... Sube el documento Excel proporcionado por el laboratorio.")