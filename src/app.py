import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import simpson

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Análisis XRD - Universidad de Guadalajara", layout="wide")

# --- ESTÉTICA INSTITUCIONAL (CSS) ---
estetica_css = """
<style>
    /* Diseño del Encabezado Principal */
    .encabezado-institucional {
        background-color: #002D62;
        color: white;
        padding: 25px;
        text-align: center;
        border-bottom: 5px solid #F0A800;
        margin-bottom: 35px;
        border-radius: 5px;
    }
    .titulo-principal {
        font-size: 26px;
        font-weight: bold;
        margin: 0;
        letter-spacing: 1px;
    }
    .subtitulo {
        font-size: 18px;
        color: #F0A800;
        margin-top: 5px;
        font-weight: normal;
    }
    .autor-info {
        font-size: 14px;
        margin-top: 15px;
        color: #E0E0E0;
    }
    /* Estilización de las Métricas */
    div[data-testid="stMetricValue"] {
        color: #002D62;
    }
    /* Estilización de la Barra Lateral */
    section[data-testid="stSidebar"] {
        background-color: #F8F9FA;
        border-right: 2px solid #002D62;
    }
</style>
"""
st.markdown(estetica_css, unsafe_allow_html=True)

# --- ENCABEZADO HTML ---
st.markdown("""
    <div class="encabezado-institucional">
        <p class="titulo-principal">UNIVERSIDAD DE GUADALAJARA | CUCEI</p>
        <p class="subtitulo">Plataforma de Análisis Computacional: Degradación de Matrices HDL</p>
        <p class="autor-info">Proyecto de Titulación | Licenciatura en Química</p>
    </div>
""", unsafe_allow_html=True)

st.markdown("Cargue el archivo de datos proveniente del difractómetro (XRD) para ejecutar la cuantificación de pérdida de cristalinidad mediante integración numérica.")
st.markdown("---")

# --- BARRA LATERAL ---
st.sidebar.markdown("### Parámetros de Integración")
st.sidebar.markdown("Defina los límites del plano basal para el cálculo del Área Bajo la Curva (AUC):")
limite_inf = st.sidebar.slider("Límite Inferior (Ángulo 2θ)", min_value=5.0, max_value=12.0, value=8.0, step=0.1)
limite_sup = st.sidebar.slider("Límite Superior (Ángulo 2θ)", min_value=12.0, max_value=20.0, value=15.0, step=0.1)

# --- CARGADOR DE ARCHIVOS ---
archivo_subido = st.file_uploader("Seleccione o arrastre el archivo de datos (Excel/CSV)", type=["xlsx", "xls", "csv"])

if archivo_subido is not None:
    try:
        # 1. Carga de datos
        if archivo_subido.name.endswith('.csv'):
            df = pd.read_csv(archivo_subido)
        else:
            df = pd.read_excel(archivo_subido, sheet_name='XRD diferentes tiempos')
            
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        # 2. Filtrado y Aislamiento
        mask_0h = (df['Angulo 2tetha'] >= limite_inf) & (df['Angulo 2tetha'] <= limite_sup)
        x_0h = df.loc[mask_0h, 'Angulo 2tetha'].values
        y_0h = df.loc[mask_0h, 'HDL 0H'].fillna(0).values

        mask_96h = (df['Angulo 2tetha.1'] >= limite_inf) & (df['Angulo 2tetha.1'] <= limite_sup)
        x_96h = df.loc[mask_96h, 'Angulo 2tetha.1'].values
        y_96h = df.loc[mask_96h, 'HDL 96H'].fillna(0).values

        # 3. Cálculo de Integrales (Área Bajo la Curva)
        area_0h = simpson(y=y_0h, x=x_0h)
        area_96h = simpson(y=y_96h, x=x_96h)
        perdida_porcentaje = ((area_0h - area_96h) / area_0h) * 100

        # 4. Panel de Métricas
        st.markdown("### Resultados de la Cuantificación")
        col1, col2, col3 = st.columns(3)
        col1.metric("Área Intacta (0h)", f"{area_0h:.2f} U.A.")
        col2.metric("Área Degradada (96h)", f"{area_96h:.2f} U.A.")
        col3.metric("Índice de Degradación", f"{perdida_porcentaje:.2f}%", "- Pérdida de Cristalinidad", delta_color="inverse")
        st.markdown("---")

        # 5. Visualización Gráfica
        st.markdown("### Visualización del Desgaste Estructural")
        fig, ax = plt.subplots(figsize=(10, 4))
        
        ax.fill_between(x_0h, y_0h, color='#002D62', alpha=0.3, label='Material Intacto (0h)')
        ax.fill_between(x_96h, y_96h, color='#F0A800', alpha=0.6, label='Material Degradado (96h)')
        ax.plot(x_0h, y_0h, color='#002D62', linewidth=1.5)
        ax.plot(x_96h, y_96h, color='#F0A800', linewidth=1.5)
        
        ax.set_xlabel('Ángulo 2θ')
        ax.set_ylabel('Intensidad de Difracción (U.A.)')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.4)
        
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Error de procesamiento. Verifique la estructura del archivo suministrado. Detalle técnico: {e}")