"""
HDL Analytical Suite — Aplicación web (Streamlit)
====================================================
Suite de análisis estructural y cinético para matrices de Hidróxido Doble
Laminar (HDL) usadas como vehículos de liberación controlada de fármacos
(GSH, NAC).

Este archivo es únicamente la capa de interfaz (UI). Todo el cálculo
físico-matemático (Ley de Bragg, integración de Simpson, FWHM,
interpolación cinética, correlación de Pearson) vive en el paquete
`hdl_suite/`, para que la lógica científica sea auditable, testeada
(ver tests/test_hdl_suite.py) y reutilizable desde los scripts de línea
de comandos sin duplicación de código.
"""
import os
import sys
import tempfile
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from fpdf import FPDF

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hdl_suite import config, pipeline  # noqa: E402

# ==========================================
# GENERADOR DE PDF INSTITUCIONAL CON GRÁFICOS
# ==========================================
class ReportePDF(FPDF):
    def header(self):
        self.set_fill_color(*config.C_AZUL_RGB)
        self.rect(0, 0, 210, 28, 'F')
        self.set_fill_color(*config.C_DORADO_RGB)
        self.rect(0, 28, 210, 2, 'F')
        self.set_y(9)
        self.set_font('Helvetica', 'B', 15)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, 'REPORTE EJECUTIVO: SUITE ANALITICA HDL - CUCEI', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()} | Generado {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 0, 'C')

    def seccion(self, titulo):
        self.set_font('Helvetica', 'B', 13)
        self.set_text_color(*config.C_AZUL_RGB)
        self.cell(0, 9, titulo, 0, 1, 'L')
        self.set_draw_color(*config.C_DORADO_RGB)
        self.set_line_width(0.6)
        self.line(self.get_x(), self.get_y(), 200, self.get_y())
        self.ln(3)


def _insertar_grafica(pdf: FPDF, fig, x=15, w=180, width=800, height=400, scale=2):
    """
    Renderiza una figura de Plotly a PNG (vía Kaleido/Chrome) y la inserta
    en el PDF. Si el motor de renderizado headless falla por cualquier
    razón del entorno (Chrome ausente o mal configurado en el servidor),
    el reporte se sigue generando con una nota en vez de abortar por
    completo — un PDF con texto y sin una gráfica es más útil para el
    usuario que ningún PDF.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            fig.write_image(tmp.name, width=width, height=height, scale=scale)
            ruta_tmp = tmp.name
        pdf.ln(3)
        pdf.image(ruta_tmp, x=x, w=w)
        os.remove(ruta_tmp)
    except Exception as e:
        pdf.ln(3)
        pdf.set_font('Helvetica', 'I', 9)
        pdf.set_text_color(180, 0, 0)
        pdf.multi_cell(0, 5, f"[Gráfica no disponible: motor de renderizado no encontrado en el servidor. Detalle: {e}]")
        pdf.set_text_color(0, 0, 0)


def generar_pdf(resultado, gsh_pct, nac_pct, fig_xrd, fig_cin, fig_sca_area, fig_sca_fwhm) -> bytes:
    pdf = ReportePDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # --- 1. XRD Y DEGRADACIÓN ESTRUCTURAL ---
    pdf.add_page()
    pdf.set_y(38)
    pdf.seccion('1. Analisis Estructural (XRD) por Tiempo')
    pdf.set_font('Helvetica', '', 10.5)
    pdf.set_text_color(0, 0, 0)
    tabla_txt = "Tiempo(h) | Area Simpson | FWHM(2t) | d-spacing(A) | % Perdida Cristalinidad\n"
    for i, t in enumerate(resultado.tiempos_h):
        tabla_txt += (
            f"{t:>9} | {resultado.areas[i]:>12.3f} | {resultado.fwhm[i]:>8.3f} | "
            f"{resultado.d_spacing[i]:>12.3f} | {resultado.perdida_cristalinidad[i]:>10.2f}%\n"
        )
    pdf.multi_cell(0, 5.5, tabla_txt)
    _insertar_grafica(pdf, fig_xrd)

    # --- 2. CINÉTICA ---
    pdf.add_page()
    pdf.set_y(38)
    pdf.seccion('2. Cinetica de Liberacion (Interpolada)')
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(40, 8, 'Hora', 1, 0, 'C', True)
    pdf.cell(70, 8, '% GSH Liberado', 1, 0, 'C', True)
    pdf.cell(70, 8, '% NAC Liberado', 1, 1, 'C', True)
    pdf.set_font('Helvetica', '', 10)
    for i in range(len(resultado.tiempos_h)):
        pdf.cell(40, 8, str(resultado.tiempos_h[i]), 1, 0, 'C')
        pdf.cell(70, 8, f"{gsh_pct[i]:.2f}%", 1, 0, 'C')
        pdf.cell(70, 8, f"{nac_pct[i]:.2f}%", 1, 1, 'C')
    _insertar_grafica(pdf, fig_cin)

    # --- 3. ESTADÍSTICA ---
    pdf.add_page()
    pdf.set_y(38)
    pdf.seccion('3. Correlacion Estadistica (Pearson)')
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(
        0, 6.5,
        f"Indice de Perdida de Cristalinidad (Area) vs GSH: r = {resultado.pearson_gsh_area['r']:.4f}  "
        f"(p = {resultado.pearson_gsh_area['p_value']:.4f})\n"
        f"Indice de Perdida de Cristalinidad (Area) vs NAC: r = {resultado.pearson_nac_area['r']:.4f}  "
        f"(p = {resultado.pearson_nac_area['p_value']:.4f})\n"
        f"Indice de Amorfizacion (FWHM) vs GSH: r = {resultado.pearson_gsh_fwhm['r']:.4f}  "
        f"(p = {resultado.pearson_gsh_fwhm['p_value']:.4f})\n"
        f"Indice de Amorfizacion (FWHM) vs NAC: r = {resultado.pearson_nac_fwhm['r']:.4f}  "
        f"(p = {resultado.pearson_nac_fwhm['p_value']:.4f})\n\n"
        f"Nota metodologica: n = {resultado.pearson_gsh_area['n']} puntos de tiempo. Con una muestra de "
        "este tamano el poder estadistico es limitado; un p-value < 0.05 se interpreta como evidencia "
        "cuantitativa que reemplaza la inspeccion visual subjetiva, no como prueba estadistica robusta "
        "en el sentido clasico. Se recomienda aumentar la densidad de muestreo XRD en trabajo futuro."
    )
    _insertar_grafica(pdf, fig_sca_area)

    return pdf.output(dest='S').encode('latin-1')


# ==========================================
# ESTILOS / DISEÑO
# ==========================================
st.set_page_config(page_title="HDL Analytical Suite", layout="wide", page_icon="🔬")

st.markdown(f"""
<style>
    .main {{ background-color: #FAFBFC; }}
    .block-container {{ padding-top: 1.5rem; }}
    div[data-testid="stMetric"] {{
        background-color: white;
        border: 1px solid #E5E9F0;
        border-left: 4px solid {config.C_AZUL};
        border-radius: 10px;
        padding: 14px 16px 8px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    div[data-testid="stMetricLabel"] {{ color: #555; font-weight: 600; }}
    .suite-banner {{
        background: linear-gradient(90deg, {config.C_AZUL} 0%, #01419b 100%);
        padding: 22px 28px;
        border-radius: 12px;
        color: white;
        margin-bottom: 6px;
    }}
    .suite-banner h1 {{ margin: 0; font-size: 1.6rem; }}
    .suite-banner p {{ margin: 4px 0 0 0; color: {config.C_DORADO}; font-weight: 600; }}
    .stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="suite-banner">
    <h1>🔬 HDL Analytical Suite</h1>
    <p>Universidad de Guadalajara · CUCEI — Laboratorio de Fisicoquímica</p>
</div>
""", unsafe_allow_html=True)
st.caption(
    "Cuantificación automatizada de degradación estructural (XRD) y su correlación estadística con la "
    "cinética de liberación de fármaco, eliminando la inspección visual subjetiva."
)

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Parámetros de Análisis")
limite_inf = st.sidebar.slider("Límite Inferior (2θ)", 2.0, 25.0, config.LIMITE_INF_DEFAULT, 0.1)
limite_sup = st.sidebar.slider("Límite Superior (2θ)", 5.0, 35.0, config.LIMITE_SUP_DEFAULT, 0.1)
usar_normalizacion = st.sidebar.checkbox("Normalizar diffractogramas (Min-Max)", value=True)
st.sidebar.caption(
    "El pico basal del HDL se ubica típicamente entre 8°-15° (2θ). Ajusta la ventana si tu material "
    "tiene el plano basal en otra región angular."
)

archivo_subido = st.file_uploader("📂 Suba su archivo Excel (Plantilla Maestra: hojas 'XRD diferentes tiempos' y 'Cinetica')", type=["xlsx"])

if archivo_subido is not None:
    try:
        with st.spinner('Ejecutando pipeline: normalización → Bragg/FWHM/Simpson → interpolación → Pearson...'):
            resultado = pipeline.ejecutar_pipeline(
                ruta_excel=archivo_subido,
                limite_inf=limite_inf,
                limite_sup=limite_sup,
                normalizar=usar_normalizacion,
            )

            if all(len(x) == 0 for x, _ in resultado.series_xrd.values()):
                st.warning(f"⚠️ No se encontraron datos entre {limite_inf}° y {limite_sup}°. Ajusta los sliders.")
                st.stop()

            df_cin = resultado.df_cinetica_interpolada
            gsh_pct = df_cin['Liberacion_GSH_Porcentaje'].to_numpy()
            nac_pct = df_cin['Liberacion_NAC_Porcentaje'].to_numpy()

            # ==========================================
            # GRÁFICOS
            # ==========================================
            # 1. XRD overlay (0h vs 96h, resaltando los extremos)
            fig_xrd = go.Figure()
            paleta_tiempos = ['#002D62', '#3D6CB9', '#8AA9D6', '#F0A800', '#B77900']
            for i, t in enumerate(resultado.tiempos_h):
                x_t, y_t = resultado.series_xrd[t]
                if len(x_t) == 0:
                    continue
                color = paleta_tiempos[i % len(paleta_tiempos)]
                fig_xrd.add_trace(go.Scatter(
                    x=x_t, y=y_t, mode='lines', name=f'HDL {t}H',
                    line=dict(color=color, width=2.5),
                    fill='tozeroy' if t in (0, resultado.tiempos_h[-1]) else None,
                    opacity=1.0 if t in (0, resultado.tiempos_h[-1]) else 0.55,
                ))
            fig_xrd.update_layout(
                xaxis_title='Ángulo 2θ', yaxis_title='Intensidad (normalizada)' if usar_normalizacion else 'Intensidad',
                template="plotly_white", margin=dict(t=30, b=30, l=30, r=30), height=500,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )

            # 2. Índices de degradación vs tiempo (área y FWHM)
            fig_degradacion = go.Figure()
            fig_degradacion.add_trace(go.Scatter(
                x=resultado.tiempos_h, y=resultado.perdida_cristalinidad, mode='lines+markers',
                name='% Pérdida de Cristalinidad (Área)', line=dict(color=config.C_AZUL, width=3), marker=dict(size=10),
            ))
            fig_degradacion.add_trace(go.Scatter(
                x=resultado.tiempos_h, y=resultado.fwhm, mode='lines+markers', name='FWHM (Amorfización)',
                yaxis='y2', line=dict(color=config.C_DORADO, width=3, dash='dot'), marker=dict(size=10, symbol='diamond'),
            ))
            fig_degradacion.update_layout(
                xaxis_title='Tiempo (horas)', yaxis_title='% Pérdida de Cristalinidad',
                yaxis2=dict(title='FWHM (°2θ)', overlaying='y', side='right'),
                template="plotly_white", margin=dict(t=30, b=30, l=30, r=30), height=450,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )

            # 3. Cinética
            fig_cin = go.Figure()
            fig_cin.add_trace(go.Scatter(x=resultado.tiempos_h, y=gsh_pct, mode='markers+lines', name='GSH', marker=dict(color=config.C_AZUL, size=12, symbol='diamond')))
            fig_cin.add_trace(go.Scatter(x=resultado.tiempos_h, y=nac_pct, mode='markers+lines', name='NAC', marker=dict(color=config.C_DORADO, size=12, symbol='diamond')))
            fig_cin.update_layout(xaxis_title='Tiempo (horas)', yaxis_title='% Liberado', template="plotly_white", margin=dict(t=30, b=30, l=30, r=30), height=450)

            # 4. Dispersión / correlación (área)
            fig_sca_area = go.Figure()
            fig_sca_area.add_trace(go.Scatter(x=resultado.perdida_cristalinidad, y=gsh_pct, mode='markers+text', name='GSH', marker=dict(size=14, color=config.C_AZUL), text=[f"{t}h" for t in resultado.tiempos_h], textposition="top center"))
            fig_sca_area.add_trace(go.Scatter(x=resultado.perdida_cristalinidad, y=nac_pct, mode='markers+text', name='NAC', marker=dict(size=14, color=config.C_DORADO), text=[f"{t}h" for t in resultado.tiempos_h], textposition="top center"))
            fig_sca_area.update_layout(xaxis_title='% Pérdida de Cristalinidad (real, por tiempo)', yaxis_title='Fármaco Liberado (%)', template="plotly_white", margin=dict(t=30, b=30, l=30, r=30), height=480)

            # 5. Dispersión / correlación (FWHM)
            fig_sca_fwhm = go.Figure()
            fig_sca_fwhm.add_trace(go.Scatter(x=resultado.fwhm, y=gsh_pct, mode='markers+text', name='GSH', marker=dict(size=14, color=config.C_AZUL), text=[f"{t}h" for t in resultado.tiempos_h], textposition="top center"))
            fig_sca_fwhm.add_trace(go.Scatter(x=resultado.fwhm, y=nac_pct, mode='markers+text', name='NAC', marker=dict(size=14, color=config.C_DORADO), text=[f"{t}h" for t in resultado.tiempos_h], textposition="top center"))
            fig_sca_fwhm.update_layout(xaxis_title='FWHM del pico basal (°2θ)', yaxis_title='Fármaco Liberado (%)', template="plotly_white", margin=dict(t=30, b=30, l=30, r=30), height=480)

            # --- BOTÓN DESCARGA PDF ---
            pdf_bytes = generar_pdf(resultado, gsh_pct, nac_pct, fig_xrd, fig_cin, fig_sca_area, fig_sca_fwhm)
            st.sidebar.markdown("---")
            st.sidebar.download_button(
                label="📥 Descargar Reporte Ejecutivo (PDF)",
                data=pdf_bytes,
                file_name=f"Reporte_HDL_Suite_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
            )

        # ==========================================
        # INTERFAZ VISUAL
        # ==========================================
        t1, t2, t3, t4 = st.tabs(["🧪 Cristalografía (XRD)", "💧 Cinética de Liberación", "📈 Correlación Estadística", "📄 Datos"])

        with t1:
            st.markdown("### Métricas Estructurales del Vehículo (HDL)")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Pérdida Cristalinidad (96h)", f"{resultado.perdida_cristalinidad[-1]:.2f}%", delta="vs 0h", delta_color="inverse")
            c2.metric("FWHM inicial → final", f"{resultado.fwhm[0]:.3f}° → {resultado.fwhm[-1]:.3f}°")
            c3.metric("d-spacing (0h)", f"{resultado.d_spacing[0]:.4f} Å")
            c4.metric("d-spacing (96h)", f"{resultado.d_spacing[-1]:.4f} Å", delta=f"{resultado.d_spacing[-1]-resultado.d_spacing[0]:+.4f} Å", delta_color="inverse")
            st.plotly_chart(fig_xrd, use_container_width=True)
            st.markdown("#### Evolución de los Índices de Degradación (5 tiempos reales de XRD)")
            st.plotly_chart(fig_degradacion, use_container_width=True)

        with t2:
            st.markdown("### Perfil de Liberación Interpolado (GSH vs NAC)")
            st.plotly_chart(fig_cin, use_container_width=True)

        with t3:
            st.markdown("### Correlación: Degradación Estructural Real vs Liberación de Fármaco")
            st.info(
                f"n = {resultado.pearson_gsh_area['n']} tiempos de medición real. Con muestras pequeñas el "
                "poder estadístico es limitado — estos resultados se presentan como evidencia cuantitativa, "
                "no como prueba estadística robusta en sentido clásico.",
                icon="ℹ️",
            )
            cA, cB = st.columns(2)
            with cA:
                st.markdown("**Índice: % Pérdida de Cristalinidad (Área de Simpson)**")
                cs1, cs2 = st.columns(2)
                cs1.metric("Pearson r (GSH)", f"{resultado.pearson_gsh_area['r']:.4f}", f"p = {resultado.pearson_gsh_area['p_value']:.4f}")
                cs2.metric("Pearson r (NAC)", f"{resultado.pearson_nac_area['r']:.4f}", f"p = {resultado.pearson_nac_area['p_value']:.4f}")
                st.plotly_chart(fig_sca_area, use_container_width=True)
            with cB:
                st.markdown("**Índice: FWHM (Amorfización)**")
                cs3, cs4 = st.columns(2)
                cs3.metric("Pearson r (GSH)", f"{resultado.pearson_gsh_fwhm['r']:.4f}", f"p = {resultado.pearson_gsh_fwhm['p_value']:.4f}")
                cs4.metric("Pearson r (NAC)", f"{resultado.pearson_nac_fwhm['r']:.4f}", f"p = {resultado.pearson_nac_fwhm['p_value']:.4f}")
                st.plotly_chart(fig_sca_fwhm, use_container_width=True)

        with t4:
            st.markdown("### Tabla Maestra (5 tiempos reales de XRD sincronizados con cinética)")
            df_maestra = pd.DataFrame({
                'Tiempo (h)': resultado.tiempos_h,
                'Área Simpson': np.round(resultado.areas, 4),
                'FWHM (°2θ)': np.round(resultado.fwhm, 4),
                'd-spacing (Å)': np.round(resultado.d_spacing, 4),
                '% Pérdida Cristalinidad': np.round(resultado.perdida_cristalinidad, 2),
                '% GSH Liberado': gsh_pct,
                '% NAC Liberado': nac_pct,
            })
            st.dataframe(df_maestra, use_container_width=True, hide_index=True)
            st.download_button(
                "📥 Descargar tabla maestra (CSV)",
                data=df_maestra.to_csv(index=False).encode('utf-8'),
                file_name="tabla_maestra_hdl.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error(f"Error procesando los datos. Verifica el formato del Excel o que 'kaleido' esté instalado. Detalle técnico: {e}")
else:
    st.info("⬆️ Sube el archivo Excel maestro para ejecutar el análisis completo.", icon="📄")
