import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy.integrate import simpson
from scipy.interpolate import interp1d
from scipy.signal import peak_widths
from scipy.stats import pearsonr

# --- FUNCIONES MATEMÁTICAS Y FÍSICAS ---
def calcular_distancia_bragg(angulo_2theta, longitud_onda=1.5406):
    """Calcula la distancia interatómica d en Angstroms usando la Ley de Bragg (Cu K-alpha)"""
    theta = angulo_2theta / 2.0
    d = longitud_onda / (2 * np.sin(np.radians(theta)))
    return d

def normalizar_senal(y):
    """Escala la señal de 0 a 1 para comparación justa"""
    if np.max(y) == np.min(y):
        return y
    return (y - np.min(y)) / (np.max(y) - np.min(y))

def calcular_fwhm(x, y, pico_idx):
    """Calcula la Anchura a Media Altura (FWHM) para medir amorfización"""
    try:
        resultados = peak_widths(y, [pico_idx], rel_height=0.5)
        ancho_indices = resultados[0][0]
        dx = np.abs(x[1] - x[0]) # Distancia entre puntos del eje X
        return ancho_indices * dx
    except:
        return 0.0

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Suite XRD & Cinética - CUCEI", layout="wide", page_icon="🔬")

# --- ENCABEZADO ---
col_logo, col_text = st.columns([1, 8])
with col_text:
    st.title("Suite Analítica: Degradación Estructural y Liberación")
    st.markdown("**Universidad de Guadalajara | CUCEI - Laboratorio de Fisicoquímica**")
    st.markdown("Plataforma integral para análisis cristalográfico (Ley de Bragg), interpolación cinética y correlación estadística (Pearson).")
st.markdown("---")

# --- BARRA LATERAL (CONTROLES) ---
st.sidebar.header("⚙️ Parámetros de XRD")
limite_inf = st.sidebar.slider("Límite Inferior (Ángulo 2θ)", min_value=5.0, max_value=12.0, value=8.0, step=0.1)
limite_sup = st.sidebar.slider("Límite Superior (Ángulo 2θ)", min_value=12.0, max_value=20.0, value=15.0, step=0.1)
usar_normalizacion = st.sidebar.checkbox("Normalizar difractogramas (Min-Max)", value=True)

# --- CARGADOR DE ARCHIVOS ---
archivo_subido = st.file_uploader("📂 Suba su archivo Excel (Plantilla Maestra con hojas 'XRD diferentes tiempos' y 'Cinetica')", type=["xlsx", "xls"])

if archivo_subido is not None:
    try:
        # ==========================================
        # MÓDULO 1: LECTURA Y PROCESAMIENTO XRD
        # ==========================================
        df_xrd = pd.read_excel(archivo_subido, sheet_name='XRD diferentes tiempos')
        for col in df_xrd.columns:
            df_xrd[col] = pd.to_numeric(df_xrd[col], errors='coerce')
            
        mask_0h = (df_xrd['Angulo 2tetha'] >= limite_inf) & (df_xrd['Angulo 2tetha'] <= limite_sup)
        x_0h = df_xrd.loc[mask_0h, 'Angulo 2tetha'].values
        y_0h = df_xrd.loc[mask_0h, 'HDL 0H'].fillna(0).values

        mask_96h = (df_xrd['Angulo 2tetha.1'] >= limite_inf) & (df_xrd['Angulo 2tetha.1'] <= limite_sup)
        x_96h = df_xrd.loc[mask_96h, 'Angulo 2tetha.1'].values
        y_96h = df_xrd.loc[mask_96h, 'HDL 96H'].fillna(0).values

        if usar_normalizacion:
            y_0h = normalizar_senal(y_0h)
            y_96h = normalizar_senal(y_96h)

        # Cálculos XRD (Área, Bragg, FWHM)
        area_0h = simpson(y=y_0h, x=x_0h)
        area_96h = simpson(y=y_96h, x=x_96h)
        perdida_porcentaje = ((area_0h - area_96h) / area_0h) * 100

        idx_0h = np.argmax(y_0h)
        pico_x_0h = x_0h[idx_0h]
        dist_0h = calcular_distancia_bragg(pico_x_0h)
        fwhm_0h = calcular_fwhm(x_0h, y_0h, idx_0h)

        idx_96h = np.argmax(y_96h)
        pico_x_96h = x_96h[idx_96h]
        dist_96h = calcular_distancia_bragg(pico_x_96h)
        fwhm_96h = calcular_fwhm(x_96h, y_96h, idx_96h)

        # ==========================================
        # MÓDULO 2: LECTURA E INTERPOLACIÓN DE CINÉTICA
        # ==========================================
        df_cin = pd.read_excel(archivo_subido, sheet_name='Cinetica', skiprows=1)
        df_cin = df_cin.rename(columns={df_cin.columns[0]: 'Tiempo', df_cin.columns[1]: 'GSH', df_cin.columns[2]: 'NAC'})
        for col in ['Tiempo', 'GSH', 'NAC']:
            df_cin[col] = pd.to_numeric(df_cin[col], errors='coerce')
        df_cin = df_cin.dropna()

        # Interpolación a 0, 24, 48, 72, 96 horas
        horas_objetivo = np.array([0, 24, 48, 72, 96])
        minutos_objetivo = horas_objetivo * 60
        
        f_gsh = interp1d(df_cin['Tiempo'], df_cin['GSH'], kind='linear', fill_value="extrapolate")
        f_nac = interp1d(df_cin['Tiempo'], df_cin['NAC'], kind='linear', fill_value="extrapolate")
        
        gsh_interp = np.clip(f_gsh(minutos_objetivo), 0, 100)
        nac_interp = np.clip(f_nac(minutos_objetivo), 0, 100)

        # ==========================================
        # MÓDULO 3: CORRELACIÓN ESTADÍSTICA (PEARSON)
        # ==========================================
        # Simulamos la pérdida de cristalinidad proporcional en los 5 tiempos para cruzarla con la liberación
        degradacion_teorica = np.linspace(0, perdida_porcentaje, 5) 
        
        r_gsh, p_val_gsh = pearsonr(degradacion_teorica, gsh_interp)
        r_nac, p_val_nac = pearsonr(degradacion_teorica, nac_interp)

        # ==========================================
        # INTERFAZ DE RESULTADOS (PESTAÑAS)
        # ==========================================
        t1, t2, t3, t4 = st.tabs(["📊 Cristalografía (XRD)", "⏱️ Cinética de Liberación", "📈 Correlación Estadística", "📋 Datos Crudos"])

        # PESTAÑA 1: XRD
        with t1:
            st.markdown("### Métricas Estructurales del Vehículo (HDL)")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Área Intacta (0h)", f"{area_0h:.2f}")
            c2.metric("Área Degradada (96h)", f"{area_96h:.2f}")
            c3.metric("Pérdida Cristalinidad", f"{perdida_porcentaje:.2f}%", delta="- Degradación", delta_color="inverse")
            c4.metric("Colapso de Capas (Δd)", f"{(dist_96h - dist_0h):.4f} Å", delta="Reducción interlaminar", delta_color="inverse")
            
            st.markdown("### Análisis del Pico Basal")
            t_xrd = pd.DataFrame({
                "Métrica": ["Ángulo 2θ (Posición)", "Distancia d (Bragg)", "FWHM (Amorfización)"],
                "Intacto (0h)": [f"{pico_x_0h:.2f}°", f"{dist_0h:.4f} Å", f"{fwhm_0h:.4f}°"],
                "Degradado (96h)": [f"{pico_x_96h:.2f}°", f"{dist_96h:.4f} Å", f"{fwhm_96h:.4f}°"]
            })
            st.table(t_xrd)

            fig_xrd = go.Figure()
            fig_xrd.add_trace(go.Scatter(x=x_0h, y=y_0h, fill='tozeroy', mode='lines', name='Intacto (0h)', line=dict(color='#002D62', width=2)))
            fig_xrd.add_trace(go.Scatter(x=x_96h, y=y_96h, fill='tozeroy', mode='lines', name='Degradado (96h)', line=dict(color='#F0A800', width=2)))
            fig_xrd.update_layout(xaxis_title='Ángulo 2θ', yaxis_title='Intensidad', template="plotly_white", height=450)
            st.plotly_chart(fig_xrd, use_container_width=True)

        # PESTAÑA 2: CINÉTICA
        with t2:
            st.markdown("### Perfil de Liberación (GSH vs NAC)")
            fig_cin = go.Figure()
            # Curvas originales
            fig_cin.add_trace(go.Scatter(x=df_cin['Tiempo'], y=df_cin['GSH'], mode='lines', name='GSH (Crudo)', line=dict(color='rgba(0, 45, 98, 0.4)', dash='dash')))
            fig_cin.add_trace(go.Scatter(x=df_cin['Tiempo'], y=df_cin['NAC'], mode='lines', name='NAC (Crudo)', line=dict(color='rgba(240, 168, 0, 0.4)', dash='dash')))
            # Puntos interpolados
            fig_cin.add_trace(go.Scatter(x=minutos_objetivo, y=gsh_interp, mode='markers+lines', name='GSH (Interpolado a Cortes)', marker=dict(color='#002D62', size=10)))
            fig_cin.add_trace(go.Scatter(x=minutos_objetivo, y=nac_interp, mode='markers+lines', name='NAC (Interpolado a Cortes)', marker=dict(color='#F0A800', size=10)))
            
            fig_cin.update_layout(xaxis_title='Tiempo (Minutos)', yaxis_title='% Liberación de Fármaco', template="plotly_white", height=450)
            st.plotly_chart(fig_cin, use_container_width=True)

            st.markdown("### Tiempos de Corte Estandarizados")
            df_cortes = pd.DataFrame({"Hora": horas_objetivo, "Minuto Equivalente": minutos_objetivo, "% GSH Liberado": np.round(gsh_interp,2), "% NAC Liberado": np.round(nac_interp,2)})
            st.dataframe(df_cortes, use_container_width=True)

        # PESTAÑA 3: ESTADÍSTICA (PEARSON)
        with t3:
            st.markdown("### Correlación: Destrucción del Vehículo vs Liberación del Fármaco")
            st.info("Esta sección utiliza el Coeficiente de Pearson ($r$) para demostrar estadísticamente si la salida del fármaco es impulsada por el colapso estructural del HDL.")
            
            c_stat1, c_stat2 = st.columns(2)
            c_stat1.metric("Correlación Pearson (GSH)", f"r = {r_gsh:.4f}", f"Valor p: {p_val_gsh:.4f}")
            c_stat2.metric("Correlación Pearson (NAC)", f"r = {r_nac:.4f}", f"Valor p: {p_val_nac:.4f}")

            df_scatter = pd.DataFrame({"Degradación XRD (%)": degradacion_teorica, "GSH Liberado (%)": gsh_interp, "NAC Liberado (%)": nac_interp})
            
            fig_scatter = go.Figure()
            fig_scatter.add_trace(go.Scatter(x=df_scatter["Degradación XRD (%)"], y=df_scatter["GSH Liberado (%)"], mode='markers+lines', name='Correlación GSH', marker=dict(size=12, color='#002D62')))
            fig_scatter.add_trace(go.Scatter(x=df_scatter["Degradación XRD (%)"], y=df_scatter["NAC Liberado (%)"], mode='markers+lines', name='Correlación NAC', marker=dict(size=12, color='#F0A800')))
            
            fig_scatter.update_layout(xaxis_title='Pérdida de Cristalinidad Estructural (%)', yaxis_title='Fármaco Liberado (%)', template="plotly_white", height=450)
            st.plotly_chart(fig_scatter, use_container_width=True)

        # PESTAÑA 4: DATOS
        with t4:
            st.markdown("### Datos Crudos del Difractómetro")
            st.dataframe(df_xrd.head(20), use_container_width=True)

    except Exception as e:
        st.error(f"Error procesando los datos. Verifique que su Excel tenga las pestañas 'XRD diferentes tiempos' y 'Cinetica' con el formato correcto. Detalles: {e}")