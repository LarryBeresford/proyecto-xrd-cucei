import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.integrate import simpson
from scipy.interpolate import interp1d
from scipy.signal import peak_widths
from scipy.stats import pearsonr
from fpdf import FPDF
from datetime import datetime
import tempfile
import os

# ==========================================
# FUNCIONES FÍSICAS Y MATEMÁTICAS
# ==========================================
def calcular_distancia_bragg(angulo_2theta, longitud_onda=1.5406):
    theta = angulo_2theta / 2.0
    d = longitud_onda / (2 * np.sin(np.radians(theta)))
    return d

def normalizar_senal(y):
    if len(y) == 0 or np.max(y) == np.min(y):
        return y
    return (y - np.min(y)) / (np.max(y) - np.min(y))

def calcular_fwhm(x, y, pico_idx):
    try:
        resultados = peak_widths(y, [pico_idx], rel_height=0.5)
        ancho_indices = resultados[0][0]
        dx = np.abs(x[1] - x[0]) 
        return ancho_indices * dx
    except:
        return 0.0

# ==========================================
# GENERADOR DE PDF INSTITUCIONAL CON GRÁFICOS
# ==========================================
C_AZUL_RGB = (0, 45, 98)
class ReportePDF(FPDF):
    def header(self):
        self.set_fill_color(*C_AZUL_RGB)
        self.rect(0, 0, 210, 30, 'F')
        self.set_y(10)
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, 'REPORTE EJECUTIVO: ANALISIS HDL - CUCEI', 0, 1, 'C')
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generar_pdf(stats, datos_cin, fig_xrd, fig_cin, fig_sca):
    pdf = ReportePDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- SECCIÓN 1: XRD ---
    pdf.add_page()
    pdf.set_y(40)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(*C_AZUL_RGB)
    pdf.cell(0, 10, '1. Analisis Estructural (XRD)', 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 7, f"Perdida de Cristalinidad: {stats['perdida']:.2f}%\n"
                         f"Area Intacta 0h: {stats['a0']:.2f} | Area Degradada 96h: {stats['a96']:.2f}\n"
                         f"Desplazamiento interatómico d (Bragg): {stats['delta_d']:.4f} Angstroms")
    
    # Guardar gráfico XRD temporalmente e insertarlo
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_xrd:
        fig_xrd.write_image(tmp_xrd.name, width=800, height=400, scale=2)
        pdf.ln(5)
        pdf.image(tmp_xrd.name, x=15, w=180)
    os.remove(tmp_xrd.name)

    # --- SECCIÓN 2: CINÉTICA ---
    pdf.add_page()
    pdf.set_y(40)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(*C_AZUL_RGB)
    pdf.cell(0, 10, '2. Cinetica de Liberacion (Interpolada)', 0, 1)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(40, 8, 'Hora', 1, 0, 'C', True)
    pdf.cell(70, 8, '% GSH Liberado', 1, 0, 'C', True)
    pdf.cell(70, 8, '% NAC Liberado', 1, 1, 'C', True)
    
    pdf.set_font('Arial', '', 10)
    for i in range(len(datos_cin['horas'])):
        pdf.cell(40, 8, str(datos_cin['horas'][i]), 1, 0, 'C')
        pdf.cell(70, 8, f"{datos_cin['gsh'][i]:.2f}%", 1, 0, 'C')
        pdf.cell(70, 8, f"{datos_cin['nac'][i]:.2f}%", 1, 1, 'C')
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_cin:
        fig_cin.write_image(tmp_cin.name, width=800, height=400, scale=2)
        pdf.ln(5)
        pdf.image(tmp_cin.name, x=15, w=180)
    os.remove(tmp_cin.name)

    # --- SECCIÓN 3: ESTADÍSTICA ---
    pdf.add_page()
    pdf.set_y(40)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(*C_AZUL_RGB)
    pdf.cell(0, 10, '3. Correlacion Estadistica (Pearson)', 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 7, f"Coeficiente r (GSH): {stats['r_gsh']:.4f} (Valor p={stats['p_gsh']:.4f})\n"
                         f"Coeficiente r (NAC): {stats['r_nac']:.4f} (Valor p={stats['p_nac']:.4f})")
                         
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_sca:
        fig_sca.write_image(tmp_sca.name, width=800, height=400, scale=2)
        pdf.ln(5)
        pdf.image(tmp_sca.name, x=15, w=180)
    os.remove(tmp_sca.name)

    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# INTERFAZ WEB (STREAMLIT)
# ==========================================
st.set_page_config(page_title="Suite XRD & Cinética", layout="wide", page_icon="🔬")

col_logo, col_text = st.columns([1, 8])
with col_text:
    st.title("Suite Analítica: Degradación Estructural y Liberación")
    st.markdown("**Universidad de Guadalajara | CUCEI - Laboratorio de Fisicoquímica**")
st.markdown("---")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Parámetros de XRD")
limite_inf = st.sidebar.slider("Límite Inferior (Ángulo 2θ)", 2.0, 25.0, 8.0, 0.1)
limite_sup = st.sidebar.slider("Límite Superior (Ángulo 2θ)", 5.0, 35.0, 15.0, 0.1)
usar_normalizacion = st.sidebar.checkbox("Normalizar difractogramas", value=True)

archivo_subido = st.file_uploader("📂 Suba su archivo Excel (Plantilla Maestra)", type=["xlsx"])

if archivo_subido is not None:
    try:
        with st.spinner('Procesando datos y generando reporte...'):
            # --- 1. LECTURA Y EXTRACCIÓN QUIRÚRGICA XRD ---
            df_xrd = pd.read_excel(archivo_subido, sheet_name='XRD diferentes tiempos')
            
            df_0h = df_xrd.iloc[:, [0, 1]].copy()
            df_0h.columns = ['Angulo', 'Intensidad']
            df_96h = df_xrd.iloc[:, [4, 8]].copy()
            df_96h.columns = ['Angulo', 'Intensidad']
            
            df_0h = df_0h.apply(pd.to_numeric, errors='coerce').dropna()
            df_96h = df_96h.apply(pd.to_numeric, errors='coerce').dropna()
                
            mask_0h = (df_0h['Angulo'] >= limite_inf) & (df_0h['Angulo'] <= limite_sup)
            x_0h = df_0h.loc[mask_0h, 'Angulo'].values
            y_0h = df_0h.loc[mask_0h, 'Intensidad'].values

            mask_96h = (df_96h['Angulo'] >= limite_inf) & (df_96h['Angulo'] <= limite_sup)
            x_96h = df_96h.loc[mask_96h, 'Angulo'].values
            y_96h = df_96h.loc[mask_96h, 'Intensidad'].values

            if len(x_0h) == 0 or len(x_96h) == 0:
                st.warning(f"⚠️ ¡Atención! No se encontraron datos entre los ángulos {limite_inf}° y {limite_sup}°. Mueva los deslizadores para atrapar el pico.")
                st.stop()

            if usar_normalizacion:
                y_0h = normalizar_senal(y_0h)
                y_96h = normalizar_senal(y_96h)

            area_0h = simpson(y=y_0h, x=x_0h)
            area_96h = simpson(y=y_96h, x=x_96h)
            perdida_porcentaje = ((area_0h - area_96h) / area_0h) * 100

            idx_0h, idx_96h = np.argmax(y_0h), np.argmax(y_96h)
            pico_x_0h, pico_x_96h = x_0h[idx_0h], x_96h[idx_96h]
            dist_0h = calcular_distancia_bragg(pico_x_0h)
            dist_96h = calcular_distancia_bragg(pico_x_96h)

            # --- 2. LECTURA CINÉTICA ---
            df_cin = pd.read_excel(archivo_subido, sheet_name='Cinetica', skiprows=1)
            df_cin = df_cin.iloc[:, :3].copy()
            df_cin.columns = ['Tiempo', 'GSH', 'NAC']
            df_cin = df_cin.apply(pd.to_numeric, errors='coerce').dropna(subset=['Tiempo', 'GSH', 'NAC'])

            horas_objetivo = np.array([0, 24, 48, 72, 96])
            minutos_objetivo = horas_objetivo * 60
            
            f_gsh = interp1d(df_cin['Tiempo'], df_cin['GSH'], kind='linear', fill_value="extrapolate")
            f_nac = interp1d(df_cin['Tiempo'], df_cin['NAC'], kind='linear', fill_value="extrapolate")
            
            gsh_interp = np.clip(f_gsh(minutos_objetivo), 0, 100)
            nac_interp = np.clip(f_nac(minutos_objetivo), 0, 100)

            # --- 3. ESTADÍSTICA (PEARSON) ---
            degradacion_teorica = np.linspace(0, perdida_porcentaje, 5) 
            r_gsh, p_val_gsh = pearsonr(degradacion_teorica, gsh_interp)
            r_nac, p_val_nac = pearsonr(degradacion_teorica, nac_interp)

            # ==========================================
            # CREACIÓN DE GRÁFICOS EN MEMORIA
            # ==========================================
            # Gráfico 1: XRD
            fig_xrd = go.Figure()
            fig_xrd.add_trace(go.Scatter(x=x_0h, y=y_0h, fill='tozeroy', mode='lines', name='Intacto (0h)', line=dict(color='#002D62', width=2.5)))
            fig_xrd.add_trace(go.Scatter(x=x_96h, y=y_96h, fill='tozeroy', mode='lines', name='Degradado (96h)', line=dict(color='#F0A800', width=2.5)))
            fig_xrd.add_annotation(x=pico_x_0h, y=y_0h[idx_0h], text=f"Máx 0h: {pico_x_0h:.2f}°", showarrow=True, arrowhead=2, arrowsize=1, arrowcolor="#002D62", ax=-40, ay=-40)
            fig_xrd.add_annotation(x=pico_x_96h, y=y_96h[idx_96h], text=f"Máx 96h: {pico_x_96h:.2f}°", showarrow=True, arrowhead=2, arrowsize=1, arrowcolor="#B77900", ax=40, ay=-40)
            fig_xrd.update_layout(xaxis_title='Ángulo 2θ', yaxis_title='Intensidad', template="plotly_white", margin=dict(t=30, b=30, l=30, r=30))

            # Gráfico 2: Cinética
            fig_cin = go.Figure()
            fig_cin.add_trace(go.Scatter(x=df_cin['Tiempo'], y=df_cin['GSH'], mode='lines', name='GSH (Crudo)', line=dict(color='rgba(0, 45, 98, 0.3)', dash='dot', width=3)))
            fig_cin.add_trace(go.Scatter(x=df_cin['Tiempo'], y=df_cin['NAC'], mode='lines', name='NAC (Crudo)', line=dict(color='rgba(240, 168, 0, 0.3)', dash='dot', width=3)))
            fig_cin.add_trace(go.Scatter(x=minutos_objetivo, y=gsh_interp, mode='markers+lines', name='GSH (24h)', marker=dict(color='#002D62', size=12, symbol='diamond')))
            fig_cin.add_trace(go.Scatter(x=minutos_objetivo, y=nac_interp, mode='markers+lines', name='NAC (24h)', marker=dict(color='#F0A800', size=12, symbol='diamond')))
            fig_cin.update_layout(xaxis_title='Tiempo (Minutos)', yaxis_title='% Liberado', template="plotly_white", margin=dict(t=30, b=30, l=30, r=30))

            # Gráfico 3: Dispersión
            fig_sca = go.Figure()
            fig_sca.add_trace(go.Scatter(x=degradacion_teorica, y=gsh_interp, mode='markers+lines', name='GSH', marker=dict(size=14, color='#002D62')))
            fig_sca.add_trace(go.Scatter(x=degradacion_teorica, y=nac_interp, mode='markers+lines', name='NAC', marker=dict(size=14, color='#F0A800')))
            fig_sca.update_layout(xaxis_title='Pérdida de Estructura (%)', yaxis_title='Fármaco Liberado (%)', template="plotly_white", margin=dict(t=30, b=30, l=30, r=30))

            # --- 4. BOTÓN DESCARGA PDF ---
            stats_dict = {'perdida': perdida_porcentaje, 'a0': area_0h, 'a96': area_96h, 'delta_d': dist_96h - dist_0h, 'r_gsh': r_gsh, 'p_gsh': p_val_gsh, 'r_nac': r_nac, 'p_nac': p_val_nac}
            cin_dict = {'horas': horas_objetivo, 'gsh': gsh_interp, 'nac': nac_interp}
            
            # Generar el PDF inyectando las gráficas que acabamos de crear
            pdf_bytes = generar_pdf(stats_dict, cin_dict, fig_xrd, fig_cin, fig_sca)
            st.sidebar.markdown("---")
            st.sidebar.download_button(
                label="📥 Descargar Reporte Ejecutivo Visual (PDF)",
                data=pdf_bytes,
                file_name=f"Reporte_Visual_CUCEI_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )

        # --- 5. INTERFAZ VISUAL ---
        t1, t2, t3, t4 = st.tabs(["📊 Cristalografía (XRD)", "⏱️ Cinética de Liberación", "📈 Correlación Estadística", "📋 Datos Crudos"])

        with t1:
            st.markdown("### Métricas Estructurales del Vehículo (HDL)")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Área Intacta (0h)", f"{area_0h:.2f}")
            c2.metric("Área Degradada (96h)", f"{area_96h:.2f}")
            c3.metric("Pérdida Cristalinidad", f"{perdida_porcentaje:.2f}%", delta="- Degradación", delta_color="inverse")
            c4.metric("Colapso Capas (Δd)", f"{(dist_96h - dist_0h):.4f} Å", delta="Reducción interlaminar", delta_color="inverse")
            
            # Volver a poner el slider abajo en web
            fig_xrd.update_layout(height=550, hovermode="x unified", xaxis=dict(rangeslider=dict(visible=True), type="-"))
            st.plotly_chart(fig_xrd, use_container_width=True)

        with t2:
            st.markdown("### Perfil de Liberación Interpolado (GSH vs NAC)")
            fig_cin.update_layout(height=500, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_cin, use_container_width=True)

        with t3:
            st.markdown("### Análisis de Correlación: Desgaste vs Liberación")
            c_stat1, c_stat2 = st.columns(2)
            c_stat1.metric("Correlación Pearson (GSH)", f"r = {r_gsh:.4f}", f"Valor p: {p_val_gsh:.4f}")
            c_stat2.metric("Correlación Pearson (NAC)", f"r = {r_nac:.4f}", f"Valor p: {p_val_nac:.4f}")

            fig_sca.update_layout(height=500, xaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightPink'), yaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightBlue'))
            st.plotly_chart(fig_sca, use_container_width=True)

        with t4:
            st.markdown("### Previsualización de Datos Extraídos")
            st.dataframe(df_xrd.head(20), use_container_width=True)

    except Exception as e:
        st.error(f"Error procesando los datos o instalando dependencias de imagen. Asegúrate de instalar 'kaleido'. Detalles técnicos: {e}")