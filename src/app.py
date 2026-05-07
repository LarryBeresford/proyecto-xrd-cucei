import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.integrate import simpson

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Análisis XRD - CUCEI", layout="wide", page_icon="📈")

# --- ENCABEZADO LIMPIO ---
col_logo, col_text = st.columns([1, 6])
with col_text:
    st.title("Plataforma de Análisis: Degradación de HDL")
    st.markdown("**Universidad de Guadalajara | CUCEI**")
    st.markdown("Cargue el archivo de datos del difractómetro (XRD) para calcular la pérdida de cristalinidad.")
st.markdown("---")

# --- BARRA LATERAL (CONTROLES) ---
st.sidebar.header("Parámetros de Integración")
st.sidebar.markdown("Ajusta los límites del plano basal para el cálculo de Área Bajo la Curva:")
limite_inf = st.sidebar.slider("Límite Inferior (Ángulo 2θ)", min_value=5.0, max_value=12.0, value=8.0, step=0.1)
limite_sup = st.sidebar.slider("Límite Superior (Ángulo 2θ)", min_value=12.0, max_value=20.0, value=15.0, step=0.1)

# --- CARGADOR DE ARCHIVOS ---
archivo_subido = st.file_uploader("Seleccione su archivo Excel o CSV", type=["xlsx", "xls", "csv"])

if archivo_subido is not None:
    try:
        # 1. Carga de datos
        if archivo_subido.name.endswith('.csv'):
            df = pd.read_csv(archivo_subido)
        else:
            df = pd.read_excel(archivo_subido, sheet_name='XRD diferentes tiempos')
            
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        # 2. Filtrado de Datos
        mask_0h = (df['Angulo 2tetha'] >= limite_inf) & (df['Angulo 2tetha'] <= limite_sup)
        x_0h = df.loc[mask_0h, 'Angulo 2tetha'].values
        y_0h = df.loc[mask_0h, 'HDL 0H'].fillna(0).values

        mask_96h = (df['Angulo 2tetha.1'] >= limite_inf) & (df['Angulo 2tetha.1'] <= limite_sup)
        x_96h = df.loc[mask_96h, 'Angulo 2tetha.1'].values
        y_96h = df.loc[mask_96h, 'HDL 96H'].fillna(0).values

        # 3. Cálculo de Degradación
        area_0h = simpson(y=y_0h, x=x_0h)
        area_96h = simpson(y=y_96h, x=x_96h)
        perdida_porcentaje = ((area_0h - area_96h) / area_0h) * 100

        # --- ESTRUCTURA DE RESULTADOS ---
        tab_metricas, tab_datos = st.tabs(["📊 Análisis Gráfico", "📋 Datos Crudos"])

        with tab_metricas:
            # Métricas Principales
            st.markdown("### Resultados de la Cuantificación")
            c1, c2, c3 = st.columns(3)
            c1.metric("Área Intacta (0h)", f"{area_0h:.2f} U.A.")
            c2.metric("Área Degradada (96h)", f"{area_96h:.2f} U.A.")
            c3.metric("Pérdida de Cristalinidad", f"{perdida_porcentaje:.2f}%", "- Degradación calculada", delta_color="inverse")
            st.markdown("---")

            # Gráfica Interactiva con Plotly
            st.markdown("### Visualización del Desgaste Estructural")
            fig = go.Figure()
            
            # Curva 0h
            fig.add_trace(go.Scatter(x=x_0h, y=y_0h, fill='tozeroy', mode='lines', 
                                     name='Intacto (0h)', line=dict(color='#002D62', width=2), fillcolor='rgba(0, 45, 98, 0.3)'))
            
            # Curva 96h
            fig.add_trace(go.Scatter(x=x_96h, y=y_96h, fill='tozeroy', mode='lines', 
                                     name='Degradado (96h)', line=dict(color='#F0A800', width=2), fillcolor='rgba(240, 168, 0, 0.5)'))

            fig.update_layout(
                xaxis_title='Ángulo 2θ',
                yaxis_title='Intensidad de Difracción (U.A.)',
                hovermode="x unified",
                template="plotly_white",
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab_datos:
            st.markdown("### Previsualización de Datos")
            st.dataframe(df.head(20), use_container_width=True)

    except Exception as e:
        st.error(f"Error procesando el archivo. Detalles: {e}")