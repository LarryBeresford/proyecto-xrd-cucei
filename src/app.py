import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.integrate import simpson
from scipy.interpolate import interp1d
from scipy.signal import peak_widths
from scipy.stats import pearsonr
from fpdf import FPDF
import io

# --- CONFIGURACIÓN ESTÉTICA ---
C_AZUL_RGB = (0, 45, 98)
C_DORADO_RGB = (240, 168, 0)

# --- CLASE PARA EL PDF ---
class ReportePDF(FPDF):
    def header(self):
        self.set_fill_color(*C_AZUL_RGB)
        self.rect(0, 0, 210, 30, 'F')
        self.set_y(10)
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, 'REPORTE EJECUTIVO: ANÁLISIS HDL - CUCEI', 0, 1, 'C')
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf(datos_xrd, datos_cin, stats):
    pdf = ReportePDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Sección 1: XRD
    pdf.set_y(40)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(*C_AZUL_RGB)
    pdf.cell(0, 10, '1. Análisis Estructural (XRD)', 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 7, f"Pérdida de Cristalinidad: {stats['perdida']:.2f}%\n"
                         f"Área 0h: {stats['a0']:.2f} | Área 96h: {stats['a96']:.2f}\n"
                         f"Desplazamiento d (Bragg): {stats['delta_d']:.4f} Angstroms")
    
    # Sección 2: Cinética
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(*C_AZUL_RGB)
    pdf.cell(0, 10, '2. Cinética de Liberación (Interpolada)', 0, 1)
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

    # Sección 3: Estadística
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(*C_AZUL_RGB)
    pdf.cell(0, 10, '3. Correlación Estadística (Pearson)', 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 7, f"Coeficiente r (GSH): {stats['r_gsh']:.4f} (p={stats['p_gsh']:.4f})\n"
                         f"Coeficiente r (NAC): {stats['r_nac']:.4f} (p={stats['p_nac']:.4f})")
    
    return pdf.output(dest='S').encode('latin-1')

# --- FUNCIONES DE CÁLCULO ---
def calcular_distancia_bragg(angulo_2theta):
    theta = angulo_2theta / 2.0
    return 1.5406 / (2 * np.sin(np.radians(theta)))

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Suite XRD & Cinética - CUCEI", layout="wide")
st.title("Suite Analítica: Degradación y Liberación")
st.markdown("**Laboratorio de Fisicoquímica | CUCEI**")

st.sidebar.header("Configuración")
l_inf = st.sidebar.slider("Límite Inf", 5.0, 12.0, 8.0)
l_sup = st.sidebar.slider("Límite Sup", 12.0, 20.0, 15.0)

archivo = st.file_uploader("Suba su Excel", type=["xlsx"])

if archivo:
    # --- PROCESAMIENTO (Igual que antes pero guardando stats) ---
    df_xrd = pd.read_excel(archivo, sheet_name='XRD diferentes tiempos')
    mask0 = (df_xrd['Angulo 2tetha'] >= l_inf) & (df_xrd['Angulo 2tetha'] <= l_sup)
    x0, y0 = df_xrd.loc[mask0, 'Angulo 2tetha'].values, df_xrd.loc[mask0, 'HDL 0H'].fillna(0).values
    mask96 = (df_xrd['Angulo 2tetha.1'] >= l_inf) & (df_xrd['Angulo 2tetha.1'] <= l_sup)
    x96, y96 = df_xrd.loc[mask96, 'Angulo 2tetha.1'].values, df_xrd.loc[mask96, 'HDL 96H'].fillna(0).values
    
    a0, a96 = simpson(y=y0, x=x0), simpson(y=y96, x=x96)
    perdida = ((a0 - a96) / a0) * 100
    d0, d96 = calcular_distancia_bragg(x0[np.argmax(y0)]), calcular_distancia_bragg(x96[np.argmax(y96)])
    
    # Cinética (Simplificado para el ejemplo)
    df_cin = pd.read_excel(archivo, sheet_name='Cinetica', skiprows=1)
    h_obj = np.array([0, 24, 48, 72, 96])
    f_gsh = interp1d(df_cin.iloc[:,0], df_cin.iloc[:,1], fill_value="extrapolate")
    f_nac = interp1d(df_cin.iloc[:,0], df_cin.iloc[:,2], fill_value="extrapolate")
    g_int, n_int = f_gsh(h_obj*60), f_nac(h_obj*60)
    
    rg, pg = pearsonr(np.linspace(0, perdida, 5), g_int)
    rn, pn = pearsonr(np.linspace(0, perdida, 5), n_int)

    # --- BOTÓN DE DESCARGA EN SIDEBAR ---
    dict_stats = {
        'perdida': perdida, 'a0': a0, 'a96': a96, 'delta_d': d96-d0,
        'r_gsh': rg, 'p_gsh': pg, 'r_nac': rn, 'p_nac': pn
    }
    dict_cin = {'horas': h_obj, 'gsh': g_int, 'nac': n_int}
    
    pdf_bytes = generar_pdf(None, dict_cin, dict_stats)
    st.sidebar.download_button(
        label="📥 Descargar Reporte PDF",
        data=pdf_bytes,
        file_name=f"Reporte_Analisis_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )

    # --- VISUALIZACIÓN ---
    t1, t2 = st.tabs(["Resultados", "Gráficas"])
    with t1:
        st.metric("Pérdida Estructural", f"{perdida:.2f}%")
        st.write("Estadísticas de Pearson:", dict_stats)
    with t2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x0, y=y0, name="0h"))
        fig.add_trace(go.Scatter(x=x96, y=y96, name="96h"))
        st.plotly_chart(fig)