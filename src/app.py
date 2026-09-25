"""
HDL Analytical Suite — Aplicación web (Streamlit)
====================================================
Suite de análisis estructural (XRD) y químico (FTIR) para matrices de
Hidróxido Doble Laminar (HDL) usadas como vehículos de liberación
controlada de fármacos (GSH, NAC), correlacionados con la cinética de
liberación. Objetivo del proyecto: "desarrollar una plataforma que
permita la correlación de cambios estructurales y/o químicos detectables
por XRD y FTIR con fenómenos de liberación y degradación" (planteamiento
del asesor).

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
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from fpdf import FPDF
from fpdf.enums import XPos, YPos

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hdl_suite import config, pipeline  # noqa: E402

PALETA_TIEMPOS = ['#002D62', '#3D6CB9', '#8AA9D6', '#F0A800', '#B77900']


def _textpos_alternado(n: int, invertido: bool = False) -> list:
    """
    Alterna la posición de las etiquetas de tiempo ('top center' /
    'bottom center') punto a punto, en vez de fijar la misma posición para
    los 5 tiempos.

    Racional: en las gráficas de correlación (dispersión) es común que dos
    tiempos consecutivos caigan muy cerca -o exactamente- en el mismo valor
    de X o Y (p.ej. cuando el FWHM ya colapsó a ~0 en dos tiempos seguidos).
    Con una posición de texto fija, las etiquetas '48h' y '72h' quedan
    literalmente encimadas una sobre otra. Alternar arriba/abajo separa
    visualmente las etiquetas. 'invertido' desfasa la secuencia para que,
    además, la serie GSH y la serie NAC (que comparten la misma X) no se
    encimen entre sí.
    """
    patron = ["bottom center", "top center"] if invertido else ["top center", "bottom center"]
    return [patron[i % 2] for i in range(n)]

# Los fuentes core de FPDF (Helvetica) solo soportan Latin-1. Streamlit/la UI
# web sí soportan UTF-8 completo (emojis, guiones largos, etc.), pero ese
# mismo texto reventaba el PDF si se reutilizaba tal cual (p.ej. el guion
# largo "—" no existe en Latin-1). Esta función normaliza cualquier texto
# antes de mandarlo a FPDF, sustituyendo la puntuación tipográfica más común
# por su equivalente ASCII y, como último recurso, descartando cualquier
# caracter que Latin-1 no pueda representar en vez de tronar la app.
_PDF_REPLACEMENTS = {
    "—": "-",   # em dash —
    "–": "-",   # en dash –
    "…": "...",  # ellipsis …
    "‘": "'", "’": "'",  # comillas simples tipográficas
    "“": '"', "”": '"',  # comillas dobles tipográficas
    "•": "-",   # bullet •
    "−": "-",   # signo menos matemático −
    "θ": "theta",  # Latin-1 no tiene letras griegas -- se deletrean para no perder el simbolo
    "λ": "lambda",
    "Δ": "delta",
    "α": "alfa",
    "β": "beta",
    "≥": ">=",  # operadores de comparacion fuera de Latin-1
    "≤": "<=",
    "≠": "!=",
    "⁻¹": "-1",  # superindice de unidades FTIR: "cm⁻¹" -> "cm-1"
    "⁻": "-",
    "→": "->",  # flecha usada en insights FTIR (posicion banda 0h -> 96h)
}


def _pdf_safe(texto: str) -> str:
    for original, reemplazo in _PDF_REPLACEMENTS.items():
        texto = texto.replace(original, reemplazo)
    return texto.encode('latin-1', errors='replace').decode('latin-1')
NOTA_METODOLOGICA_N_BAJO = (
    "Con muestras de este tamaño (n=5 tiempos reales) el poder estadístico es limitado. "
    "Un p-value < 0.05 se interpreta aquí como evidencia cuantitativa que reemplaza la inspección "
    "visual subjetiva, no como prueba estadística robusta en el sentido clásico."
)


# ==========================================
# TEXTOS INTERPRETATIVOS (compartidos entre HTML y PDF)
# ==========================================
def _interpretar_pearson(nombre_indice: str, molecula: str, res: dict) -> str:
    """Redacta en prosa el resultado de una correlación de Pearson, incluyendo
    si alcanzó o no significancia estadística, para que el snapshot no se
    quede solo en números sueltos."""
    significativa = res['p_value'] < 0.05
    veredicto = (
        "estadísticamente significativa (p < 0.05)" if significativa
        else "no alcanzó significancia estadística (p ≥ 0.05) con este tamaño de muestra"
    )
    return (
        f"{nombre_indice} vs. % {molecula} liberado: r = {res['r']:.3f}, R² = {res['r2']:.3f}, "
        f"p = {res['p_value']:.4f} — {veredicto}."
    )


def construir_insights_xrd(r) -> dict:
    """Genera las explicaciones narrativas del bloque XRD con los números
    reales ya sustituidos, para usarse tanto en el PDF como en el HTML."""
    perdida_96h = r.perdida_cristalinidad[-1]
    fwhm_ini, fwhm_fin = r.fwhm[0], r.fwhm[-1]
    d_ini, d_fin = r.d_spacing[0], r.d_spacing[-1]
    delta_d = d_fin - d_ini
    tendencia_fwhm = "aumentó" if fwhm_fin > fwhm_ini else "disminuyó"

    return {
        "contexto": (
            "El Hidróxido Doble Laminar (HDL) funciona como un 'vehículo' en capas que transporta "
            "moléculas antioxidantes (GSH, NAC) intercaladas entre sus láminas. La Difracción de Rayos X "
            "(XRD) permite ver, de forma indirecta, qué tan ordenado sigue estando ese apilamiento de "
            "capas a medida que pasa el tiempo y el fármaco va saliendo."
        ),
        "bragg": (
            "La Ley de Bragg (n·λ = 2d·sin θ) traduce el ángulo donde aparece el pico de difracción "
            "principal en una distancia física real entre capas consecutivas del HDL (el 'd-spacing', "
            "en angstroms). Si esa distancia cambia con el tiempo, es evidencia directa de que el "
            "apilamiento de capas se está expandiendo o colapsando."
        ),
        "simpson": (
            "El área bajo el pico principal de difracción (calculada por integración numérica, Regla de "
            "Simpson) es proporcional a la cantidad de material que sigue perfectamente ordenado en fase "
            "cristalina. Comparar esa área a lo largo del tiempo contra el valor inicial (0h) da un "
            "'Índice de Pérdida de Cristalinidad' — un número exacto que reemplaza la inspección visual "
            "subjetiva de 'el pico se ve más aplastado'."
        ),
        "fwhm": (
            "El FWHM (ancho del pico a la mitad de su altura máxima) mide qué tan 'desordenado' está el "
            "material: un cristal perfecto da picos angostos y precisos, mientras que la amorfización "
            "(pérdida de orden) los ensancha. Es un segundo índice de degradación, matemáticamente "
            "independiente del área, y no se ve afectado por la elección de normalización de los datos — "
            "por eso es el índice más robusto de este análisis."
        ),
        "resultados_kpi": (
            f"Entre 0h y 96h, la pérdida de cristalinidad (por área) fue de {perdida_96h:.2f}%. "
            f"El FWHM {tendencia_fwhm} de {fwhm_ini:.4f}° a {fwhm_fin:.4f}° (2θ). "
            f"El espaciado interlaminar (d-spacing) pasó de {d_ini:.4f} Å a {d_fin:.4f} Å "
            f"(cambio de {delta_d:+.4f} Å), lo que indica "
            f"{'una expansión' if delta_d > 0 else 'un colapso'} neta del espacio entre capas del HDL."
        ),
        "cinetica": (
            "La liberación del fármaco se midió en minutos con muestreos irregulares, mientras que el XRD "
            "se midió en cortes fijos de horas (0, 24, 48, 72, 96h). Para poder comparar ambas variables en "
            "los mismos instantes, se construyó una función continua a partir de los puntos reales de "
            "cinética (interpolación lineal) y se evaluó exactamente en esos 5 tiempos de XRD."
        ),
        "correlacion": (
            "Con la degradación estructural real (no una aproximación) y la liberación interpolada, ambas "
            "evaluadas en los mismos 5 tiempos, se calculó la correlación de Pearson (r), su bondad de "
            "ajuste (R²) y su significancia estadística (p-value), para dos índices independientes: "
            "pérdida de cristalinidad (área) y amorfización (FWHM)."
        ),
        "correlacion_detalle": [
            _interpretar_pearson("Pérdida de Cristalinidad (Área)", "GSH", r.pearson_gsh_area),
            _interpretar_pearson("Pérdida de Cristalinidad (Área)", "NAC", r.pearson_nac_area),
            _interpretar_pearson("Amorfización (FWHM)", "GSH", r.pearson_gsh_fwhm),
            _interpretar_pearson("Amorfización (FWHM)", "NAC", r.pearson_nac_fwhm),
        ],
        "limitacion": (
            f"Nota metodológica: n = {r.pearson_gsh_area['n']} tiempos de medición real. "
            f"{NOTA_METODOLOGICA_N_BAJO} El índice de área depende de la convención de normalización "
            "elegida (se muestra en los 'Parámetros de este snapshot'); el índice FWHM es invariante a "
            "esa elección y por eso se recomienda como evidencia principal."
        ),
    }


def construir_insights_ftir(rf) -> dict:
    cambio_96h = rf.perdida_banda[-1]
    fwhm_ini, fwhm_fin = rf.fwhm[0], rf.fwhm[-1]
    pos_ini, pos_fin = rf.posicion_banda_cm1[0], rf.posicion_banda_cm1[-1]
    desplazamiento = pos_fin - pos_ini

    return {
        "contexto": (
            "Mientras que el XRD mide el orden de largo alcance del apilamiento laminar, la Espectroscopía "
            "Infrarroja (FTIR) es sensible a los enlaces químicos específicos (vibraciones de tensión y "
            "flexión de grupos funcionales). Rastrear cómo cambia una banda característica en el tiempo "
            "aporta una segunda línea de evidencia -de naturaleza química, no solo estructural."
        ),
        "banda": (
            f"Se analizó la banda entre {rf.banda_inf:.0f} y {rf.banda_sup:.0f} cm⁻¹ del material "
            f"{rf.material}. Importante: la identidad química de esta banda (a qué modo vibracional "
            "corresponde exactamente) debe confirmarse con el asesor/director antes de usarse como "
            "evidencia definitiva en el protocolo o documento final; aquí se reporta como un índice "
            "numérico de cambio, no como una asignación espectroscópica validada."
        ),
        "resultados_kpi": (
            f"Entre 0h y 96h, el área de la banda cambió {cambio_96h:+.2f}% respecto a su valor inicial. "
            f"El FWHM de la banda pasó de {fwhm_ini:.2f} a {fwhm_fin:.2f} cm⁻¹. "
            f"La posición del pico (desplazamiento químico) se movió de {pos_ini:.1f} a {pos_fin:.1f} cm⁻¹ "
            f"({desplazamiento:+.1f} cm⁻¹), lo que sugiere un cambio en el entorno de enlace de ese grupo "
            "funcional a lo largo del experimento."
        ),
        "correlacion_detalle": [
            _interpretar_pearson("Cambio de Banda (Área)", "GSH", rf.pearson_gsh_area),
            _interpretar_pearson("Cambio de Banda (Área)", "NAC", rf.pearson_nac_area),
            _interpretar_pearson("FWHM de Banda", "GSH", rf.pearson_gsh_fwhm),
            _interpretar_pearson("FWHM de Banda", "NAC", rf.pearson_nac_fwhm),
        ],
        "limitacion": (
            f"Nota metodológica: n = {rf.pearson_gsh_area['n']} tiempos de medición real. "
            f"{NOTA_METODOLOGICA_N_BAJO}"
        ),
    }


# ==========================================
# GENERADOR DE SNAPSHOT EN HTML (interactivo, para adjuntar en correo)
# ==========================================
def _fig_a_html(fig, incluir_libreria_js: bool) -> str:
    return fig.to_html(full_html=False, include_plotlyjs='cdn' if incluir_libreria_js else False, config={'displaylogo': False})


def _tarjeta_kpi(etiqueta: str, valor: str) -> str:
    return f"""<div class="kpi-card"><div class="kpi-label">{etiqueta}</div><div class="kpi-value">{valor}</div></div>"""


def _bloque_parrafos(*parrafos: str) -> str:
    return "".join(f"<p>{p}</p>" for p in parrafos)


def _bloque_lista(items: list) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def generar_html_snapshot(xrd_ctx: Optional[dict], ftir_ctx: Optional[dict], params: dict) -> str:
    """
    Genera un snapshot autocontenido en HTML (mismo diseño visual que la
    app: banner azul/dorado, tarjetas de KPI) con gráficas Plotly
    interactivas embebidas (vía CDN) y explicaciones completas de cada
    sección -- pensado para adjuntarse directamente en un correo o abrirse
    en cualquier navegador sin depender de Streamlit.
    """
    primera_grafica = True
    secciones_html = []

    # --- Parámetros de esta captura ---
    filas_params = []
    if params.get('xrd'):
        p = params['xrd']
        filas_params.append(f"<tr><td>Archivo XRD+Cinética</td><td>{p['archivo']}</td></tr>")
        filas_params.append(f"<tr><td>Ventana angular (2θ)</td><td>{p['limite_inf']:.1f}° – {p['limite_sup']:.1f}°</td></tr>")
        filas_params.append(f"<tr><td>Normalización Min-Max (XRD)</td><td>{'Sí' if p['normalizar'] else 'No'}</td></tr>")
    if params.get('ftir'):
        p = params['ftir']
        filas_params.append(f"<tr><td>Archivo espectros FTIR</td><td>{p['archivo_ftir']}</td></tr>")
        filas_params.append(f"<tr><td>Archivo cinética (FTIR)</td><td>{p['archivo_cinetica']}</td></tr>")
        filas_params.append(f"<tr><td>Material analizado (FTIR)</td><td>{p['material']}</td></tr>")
        filas_params.append(f"<tr><td>Banda espectral (cm⁻¹)</td><td>{p['banda_inf']:.0f} – {p['banda_sup']:.0f}</td></tr>")
        filas_params.append(f"<tr><td>Normalización Min-Max (FTIR)</td><td>{'Sí' if p['normalizar'] else 'No'}</td></tr>")

    secciones_html.append(f"""
    <div class="card">
      <h2>Parámetros de este Snapshot</h2>
      <p class="muted">Capturado el {params['timestamp']}. Esta es la configuración exacta con la que se generaron los resultados de abajo -- si cambias los sliders en la app, genera un nuevo snapshot.</p>
      <table class="params-table">{"".join(filas_params)}</table>
    </div>
    """)

    if xrd_ctx is not None:
        r = xrd_ctx['resultado']
        ins = construir_insights_xrd(r)
        graf_xrd = _fig_a_html(xrd_ctx['fig_xrd'], primera_grafica); primera_grafica = False
        graf_degradacion = _fig_a_html(xrd_ctx['fig_degradacion'], primera_grafica)
        graf_cin = _fig_a_html(xrd_ctx['fig_cin'], primera_grafica)
        graf_sca_area = _fig_a_html(xrd_ctx['fig_sca_area'], primera_grafica)
        graf_sca_fwhm = _fig_a_html(xrd_ctx['fig_sca_fwhm'], primera_grafica)

        secciones_html.append(f"""
        <div class="card">
          <h2>1. Análisis Estructural (XRD)</h2>
          {_bloque_parrafos(ins['contexto'], ins['bragg'])}
          <div class="kpi-row">
            {_tarjeta_kpi('Pérdida Cristalinidad (96h)', f"{r.perdida_cristalinidad[-1]:.2f}%")}
            {_tarjeta_kpi('FWHM inicial → final', f"{r.fwhm[0]:.4f}° → {r.fwhm[-1]:.4f}°")}
            {_tarjeta_kpi('d-spacing (0h)', f"{r.d_spacing[0]:.4f} Å")}
            {_tarjeta_kpi('d-spacing (96h)', f"{r.d_spacing[-1]:.4f} Å")}
          </div>
          <h3>¿Qué significa el área bajo el pico?</h3>
          {_bloque_parrafos(ins['simpson'])}
          <h3>¿Qué significa el FWHM?</h3>
          {_bloque_parrafos(ins['fwhm'])}
          <p><strong>Lectura de resultados:</strong> {ins['resultados_kpi']}</p>
          {graf_xrd}
          <h3>Evolución de los índices de degradación (5 tiempos reales)</h3>
          {graf_degradacion}
        </div>

        <div class="card">
          <h2>2. Cinética de Liberación</h2>
          {_bloque_parrafos(ins['cinetica'])}
          {graf_cin}
        </div>

        <div class="card">
          <h2>3. Correlación Estadística (XRD vs. Cinética)</h2>
          {_bloque_parrafos(ins['correlacion'])}
          {_bloque_lista(ins['correlacion_detalle'])}
          <p class="muted">{ins['limitacion']}</p>
          <div class="two-col">
            <div>{graf_sca_area}</div>
            <div>{graf_sca_fwhm}</div>
          </div>
        </div>
        """)

    if ftir_ctx is not None:
        rf = ftir_ctx['resultado']
        ins = construir_insights_ftir(rf)
        graf_ftir = _fig_a_html(ftir_ctx['fig_ftir'], primera_grafica); primera_grafica = False
        graf_evol = _fig_a_html(ftir_ctx['fig_evolucion'], primera_grafica)
        graf_sca_area_f = _fig_a_html(ftir_ctx['fig_sca_area'], primera_grafica)
        graf_sca_fwhm_f = _fig_a_html(ftir_ctx['fig_sca_fwhm'], primera_grafica)

        secciones_html.append(f"""
        <div class="card">
          <h2>4. Análisis Químico (FTIR) — Material: {rf.material}</h2>
          {_bloque_parrafos(ins['contexto'], ins['banda'])}
          <div class="kpi-row">
            {_tarjeta_kpi('% Cambio de Banda (96h)', f"{rf.perdida_banda[-1]:+.2f}%")}
            {_tarjeta_kpi('FWHM inicial → final', f"{rf.fwhm[0]:.2f} → {rf.fwhm[-1]:.2f} cm⁻¹")}
            {_tarjeta_kpi('Posición banda (0h → 96h)', f"{rf.posicion_banda_cm1[0]:.1f} → {rf.posicion_banda_cm1[-1]:.1f} cm⁻¹")}
          </div>
          <p><strong>Lectura de resultados:</strong> {ins['resultados_kpi']}</p>
          {graf_ftir}
          <h3>Evolución de los índices químicos (5 tiempos reales)</h3>
          {graf_evol}
        </div>

        <div class="card">
          <h2>5. Correlación Estadística (FTIR vs. Cinética)</h2>
          {_bloque_lista(ins['correlacion_detalle'])}
          <p class="muted">{ins['limitacion']}</p>
          <div class="two-col">
            <div>{graf_sca_area_f}</div>
            <div>{graf_sca_fwhm_f}</div>
          </div>
        </div>
        """)

    cuerpo = "".join(secciones_html)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Snapshot - HDL Analytical Suite</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#FAFBFC; color:#2A2A2A; margin:0; padding:0 0 30px 0; line-height:1.55; }}
  .banner {{ background: linear-gradient(90deg, {config.C_AZUL} 0%, #01419b 100%); color:white; padding:30px 36px; border-bottom:4px solid {config.C_DORADO}; }}
  .banner h1 {{ margin:0; font-size:1.6rem; font-weight:600; letter-spacing:0.2px; }}
  .banner p {{ margin:8px 0 0 0; color:{config.C_DORADO}; font-weight:600; font-size:0.9rem; letter-spacing:0.3px; }}
  .container {{ max-width: 980px; margin: 24px auto; padding: 0 20px; }}
  .card {{ background:white; border:1px solid #E5E9F0; border-left:4px solid {config.C_AZUL}; border-radius:8px; padding:26px 30px; margin-bottom:22px; box-shadow:0 1px 4px rgba(15,35,70,0.06); }}
  .card h2 {{ color:{config.C_AZUL}; margin:0 0 16px 0; font-size:1.25rem; font-weight:600; padding-bottom:10px; border-bottom:2px solid #EEF1F6; }}
  .card h3 {{ color:{config.C_AZUL}; font-size:1rem; font-weight:600; margin:20px 0 8px 0; }}
  .card p {{ margin:0 0 12px 0; font-size:0.95rem; }}
  .muted {{ color:#6B7280; font-size:0.88rem; }}
  .kpi-row {{ display:flex; flex-wrap:wrap; gap:14px; margin:18px 0; }}
  .kpi-card {{ background:#F5F7FA; border-left:3px solid {config.C_DORADO}; border-radius:6px; padding:12px 16px; min-width:180px; flex:1; }}
  .kpi-label {{ font-size:0.76rem; color:#5A6472; font-weight:700; text-transform:uppercase; letter-spacing:0.4px; }}
  .kpi-value {{ font-size:1.2rem; color:{config.C_AZUL}; font-weight:700; margin-top:2px; }}
  .params-table {{ width:100%; border-collapse:collapse; margin-top:12px; font-size:0.92rem; }}
  .params-table td {{ padding:9px 12px; border-bottom:1px solid #EEF1F6; }}
  .params-table tr:last-child td {{ border-bottom:none; }}
  .params-table td:first-child {{ font-weight:600; color:#444; width:42%; }}
  .two-col {{ display:flex; gap:18px; flex-wrap:wrap; margin-top:10px; }}
  .two-col > div {{ flex:1; min-width:320px; }}
  ul {{ padding-left: 20px; margin:10px 0; }}
  li {{ margin-bottom: 8px; font-size:0.95rem; }}
  .footer-bar {{ text-align:center; color:#9AA3AF; font-size:0.8rem; letter-spacing:0.3px; padding-top:14px; margin-top:6px; border-top:1px solid #E5E9F0; }}
</style>
</head>
<body>
  <div class="banner">
    <h1>HDL Analytical Suite — Snapshot del Análisis</h1>
    <p>Universidad de Guadalajara · CUCEI — Laboratorio de Fisicoquímica</p>
  </div>
  <div class="container">
    {cuerpo}
    <div class="footer-bar">HDL Analytical Suite &middot; CUCEI</div>
  </div>
</body>
</html>"""


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
        self.cell(0, 8, 'SNAPSHOT DEL ANALISIS: SUITE ANALITICA HDL - CUCEI', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_draw_color(225, 225, 225)
        self.set_line_width(0.2)
        self.line(15, self.get_y(), 195, self.get_y())
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 8, f'Pagina {self.page_no()}', 0, 0, 'C')

    def seccion(self, titulo):
        self.set_font('Helvetica', 'B', 13)
        self.set_text_color(*config.C_AZUL_RGB)
        self.cell(0, 9, _pdf_safe(titulo), 0, 1, 'L')
        self.set_draw_color(*config.C_DORADO_RGB)
        self.set_line_width(0.6)
        self.line(self.get_x(), self.get_y(), 200, self.get_y())
        self.ln(3)

    def parrafo(self, texto):
        self.set_font('Helvetica', '', 10.5)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.8, _pdf_safe(texto), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def subtitulo(self, texto):
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(*config.C_AZUL_RGB)
        self.multi_cell(0, 6, _pdf_safe(texto), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(0.5)

    def tabla_datos(self, encabezados: list, filas: list, anchos: list, alturas_fila: float = 7.5, align: str = 'C'):
        """
        Dibuja una tabla con bordes, encabezado en azul institucional y
        renglones alternados (zebra) -- usa pdf.cell() celda por celda en
        vez de texto plano con espacios de relleno, porque Helvetica es una
        fuente proporcional: un padding manual tipo f"{x:>10}" solo alinea
        en fuentes monoespaciadas y en Helvetica termina viéndose
        desalineado/encimado. Con celdas reales cada columna respeta su
        propio ancho sin importar cuántos caracteres tenga el contenido.
        """
        self.set_font('Helvetica', 'B', 9)
        self.set_fill_color(*config.C_AZUL_RGB)
        self.set_text_color(255, 255, 255)
        for encabezado, ancho in zip(encabezados, anchos):
            self.cell(ancho, 8, _pdf_safe(encabezado), 1, 0, 'C', True)
        self.ln()

        self.set_font('Helvetica', '', 9)
        self.set_text_color(30, 30, 30)
        for i, fila in enumerate(filas):
            self.set_fill_color(243, 246, 250) if i % 2 == 0 else self.set_fill_color(255, 255, 255)
            for valor, ancho in zip(fila, anchos):
                self.cell(ancho, alturas_fila, _pdf_safe(str(valor)), 1, 0, align, True)
            self.ln()
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def portada_parametros(self, params: dict):
        self.add_page()
        self.set_y(38)
        self.seccion('Parametros de este Snapshot')
        self.parrafo(
            f"Capturado el {params['timestamp']}. Esta es la configuracion exacta (archivos, ventanas "
            "y opciones de normalizacion) con la que se generaron todos los resultados de este documento. "
            "Si se ajustan los sliders en la aplicacion, debe generarse un nuevo snapshot."
        )
        self.ln(2)

        filas = []
        if params.get('xrd'):
            p = params['xrd']
            filas += [
                ('Archivo XRD + Cinetica', p['archivo']),
                ('Ventana angular (2theta)', f"{p['limite_inf']:.1f} - {p['limite_sup']:.1f} grados"),
                ('Normalizacion Min-Max (XRD)', 'Si' if p['normalizar'] else 'No'),
            ]
        if params.get('ftir'):
            p = params['ftir']
            filas += [
                ('Archivo espectros FTIR', p['archivo_ftir']),
                ('Archivo cinetica (FTIR)', p['archivo_cinetica']),
                ('Material analizado (FTIR)', p['material']),
                ('Banda espectral (cm-1)', f"{p['banda_inf']:.0f} - {p['banda_sup']:.0f}"),
                ('Normalizacion Min-Max (FTIR)', 'Si' if p['normalizar'] else 'No'),
            ]
        self.tabla_datos(['Parametro', 'Valor'], filas, [70, 120], align='L')


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
        pdf.multi_cell(0, 5, f"[Gráfica no disponible: motor de renderizado no encontrado en el servidor. Detalle: {e}]", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)


def generar_pdf(xrd_ctx: Optional[dict], ftir_ctx: Optional[dict], params: dict) -> bytes:
    pdf = ReportePDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.portada_parametros(params)

    if xrd_ctx is not None:
        r = xrd_ctx['resultado']
        ins = construir_insights_xrd(r)

        pdf.add_page()
        pdf.set_y(38)
        pdf.seccion('1. Analisis Estructural (XRD) por Tiempo')
        pdf.parrafo(ins['contexto'])
        pdf.parrafo(ins['bragg'])
        pdf.subtitulo('Que significa el area bajo el pico (Regla de Simpson)?')
        pdf.parrafo(ins['simpson'])
        pdf.subtitulo('Que significa el FWHM (amorfizacion)?')
        pdf.parrafo(ins['fwhm'])
        pdf.subtitulo('Lectura de resultados')
        pdf.parrafo(ins['resultados_kpi'])
        filas_xrd = [
            (t, f"{r.areas[i]:.3f}", f"{r.fwhm[i]:.3f}", f"{r.d_spacing[i]:.3f}", f"{r.perdida_cristalinidad[i]:.2f}%")
            for i, t in enumerate(r.tiempos_h)
        ]
        pdf.tabla_datos(
            ['Tiempo (h)', 'Area Simpson', 'FWHM (2theta)', 'd-spacing (A)', '% Perdida Cristalinidad'],
            filas_xrd, [25, 35, 35, 35, 50],
        )
        _insertar_grafica(pdf, xrd_ctx['fig_xrd'])
        _insertar_grafica(pdf, xrd_ctx['fig_degradacion'])

        pdf.add_page()
        pdf.set_y(38)
        pdf.seccion('2. Cinetica de Liberacion (Interpolada) - XRD')
        pdf.parrafo(ins['cinetica'])
        filas_cin = [
            (r.tiempos_h[i], f"{xrd_ctx['gsh_pct'][i]:.2f}%", f"{xrd_ctx['nac_pct'][i]:.2f}%")
            for i in range(len(r.tiempos_h))
        ]
        pdf.tabla_datos(['Hora', '% GSH Liberado', '% NAC Liberado'], filas_cin, [40, 70, 70])
        _insertar_grafica(pdf, xrd_ctx['fig_cin'])

        pdf.add_page()
        pdf.set_y(38)
        pdf.seccion('3. Correlacion Estadistica XRD (Pearson)')
        pdf.parrafo(ins['correlacion'])
        for linea in ins['correlacion_detalle']:
            pdf.set_font('Helvetica', '', 10.5)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, _pdf_safe('- ' + linea), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)
        pdf.set_font('Helvetica', 'I', 9.5)
        pdf.set_text_color(90, 90, 90)
        pdf.multi_cell(0, 5.5, _pdf_safe(ins['limitacion']), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        _insertar_grafica(pdf, xrd_ctx['fig_sca_area'])
        _insertar_grafica(pdf, xrd_ctx['fig_sca_fwhm'])

    if ftir_ctx is not None:
        rf = ftir_ctx['resultado']
        ins = construir_insights_ftir(rf)

        pdf.add_page()
        pdf.set_y(38)
        pdf.seccion(f'4. Analisis Quimico (FTIR) - Material: {rf.material}')
        pdf.parrafo(ins['contexto'])
        pdf.parrafo(ins['banda'])
        pdf.subtitulo('Lectura de resultados')
        pdf.parrafo(ins['resultados_kpi'])
        filas_ftir = [
            (t, f"{rf.areas[i]:.3f}", f"{rf.fwhm[i]:.3f}", f"{rf.posicion_banda_cm1[i]:.2f}", f"{rf.perdida_banda[i]:+.2f}%")
            for i, t in enumerate(rf.tiempos_h)
        ]
        pdf.tabla_datos(
            ['Tiempo (h)', 'Area Simpson', 'FWHM (cm-1)', 'Posicion Banda (cm-1)', '% Cambio Banda'],
            filas_ftir, [25, 35, 35, 40, 45],
        )
        _insertar_grafica(pdf, ftir_ctx['fig_ftir'])
        _insertar_grafica(pdf, ftir_ctx['fig_evolucion'])

        pdf.add_page()
        pdf.set_y(38)
        pdf.seccion('5. Correlacion Estadistica FTIR (Pearson)')
        for linea in ins['correlacion_detalle']:
            pdf.set_font('Helvetica', '', 10.5)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, _pdf_safe('- ' + linea), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)
        pdf.set_font('Helvetica', 'I', 9.5)
        pdf.set_text_color(90, 90, 90)
        pdf.multi_cell(0, 5.5, _pdf_safe(ins['limitacion']), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        _insertar_grafica(pdf, ftir_ctx['fig_sca_area'])
        _insertar_grafica(pdf, ftir_ctx['fig_sca_fwhm'])

    # fpdf2 >= 2.2 devuelve bytearray directamente desde output() (el
    # parametro dest='S' esta deprecado y en versiones recientes ya no
    # devuelve un str que haya que codificar). bytes(...) normaliza el
    # bytearray a bytes, que es lo que espera st.download_button.
    return bytes(pdf.output())


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
    "Correlación de cambios estructurales (XRD) y químicos (FTIR) con la cinética de liberación de "
    "fármaco, eliminando la inspección visual subjetiva."
)

xrd_ctx = None
ftir_ctx = None
params_xrd = None
params_ftir = None

tab_xrd, tab_ftir = st.tabs(["📊 Estructural (XRD)", "🧪 Químico (FTIR)"])

# ==========================================================================
# PESTAÑA 1: XRD
# ==========================================================================
with tab_xrd:
    st.sidebar.header("⚙️ Parámetros XRD")
    limite_inf = st.sidebar.slider("Límite Inferior (2θ)", 2.0, 25.0, config.LIMITE_INF_DEFAULT, 0.1, key="xrd_inf")
    limite_sup = st.sidebar.slider("Límite Superior (2θ)", 5.0, 35.0, config.LIMITE_SUP_DEFAULT, 0.1, key="xrd_sup")
    usar_normalizacion_xrd = st.sidebar.checkbox("Normalizar diffractogramas (Min-Max)", value=True, key="xrd_norm")
    st.sidebar.caption(
        "El pico basal del HDL se ubica típicamente entre 8°-15° (2θ). Ajusta la ventana si tu material "
        "tiene el plano basal en otra región angular."
    )

    archivo_xrd = st.file_uploader(
        "📂 Excel de XRD + Cinética (hojas 'XRD diferentes tiempos' y 'Cinetica')", type=["xlsx"], key="xrd_file"
    )

    if archivo_xrd is not None:
        try:
            with st.spinner('Ejecutando pipeline XRD: normalización → Bragg/FWHM/Simpson → interpolación → Pearson...'):
                resultado = pipeline.ejecutar_pipeline(
                    ruta_excel=archivo_xrd,
                    limite_inf=limite_inf,
                    limite_sup=limite_sup,
                    normalizar=usar_normalizacion_xrd,
                )

                if all(len(x) == 0 for x, _ in resultado.series_xrd.values()):
                    st.warning(f"⚠️ No se encontraron datos entre {limite_inf}° y {limite_sup}°. Ajusta los sliders.")
                    st.stop()

                df_cin = resultado.df_cinetica_interpolada
                gsh_pct = df_cin['Liberacion_GSH_Porcentaje'].to_numpy()
                nac_pct = df_cin['Liberacion_NAC_Porcentaje'].to_numpy()

                fig_xrd = go.Figure()
                for i, t in enumerate(resultado.tiempos_h):
                    x_t, y_t = resultado.series_xrd[t]
                    if len(x_t) == 0:
                        continue
                    color = PALETA_TIEMPOS[i % len(PALETA_TIEMPOS)]
                    fig_xrd.add_trace(go.Scatter(
                        x=x_t, y=y_t, mode='lines', name=f'HDL {t}H',
                        line=dict(color=color, width=2.5),
                        fill='tozeroy' if t in (0, resultado.tiempos_h[-1]) else None,
                        opacity=1.0 if t in (0, resultado.tiempos_h[-1]) else 0.55,
                    ))
                fig_xrd.update_layout(
                    xaxis_title='Ángulo 2θ', yaxis_title='Intensidad (normalizada)' if usar_normalizacion_xrd else 'Intensidad',
                    template="plotly_white", margin=dict(t=30, b=30, l=30, r=30), height=500,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )

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

                fig_cin = go.Figure()
                fig_cin.add_trace(go.Scatter(x=resultado.tiempos_h, y=gsh_pct, mode='markers+lines', name='GSH', marker=dict(color=config.C_AZUL, size=12, symbol='diamond')))
                fig_cin.add_trace(go.Scatter(x=resultado.tiempos_h, y=nac_pct, mode='markers+lines', name='NAC', marker=dict(color=config.C_DORADO, size=12, symbol='diamond')))
                fig_cin.update_layout(xaxis_title='Tiempo (horas)', yaxis_title='% Liberado', template="plotly_white", margin=dict(t=30, b=30, l=30, r=30), height=450)

                _n_t = len(resultado.tiempos_h)
                fig_sca_area = go.Figure()
                fig_sca_area.add_trace(go.Scatter(x=resultado.perdida_cristalinidad, y=gsh_pct, mode='markers+text', name='GSH', marker=dict(size=14, color=config.C_AZUL), text=[f"{t}h" for t in resultado.tiempos_h], textposition=_textpos_alternado(_n_t), textfont=dict(size=10)))
                fig_sca_area.add_trace(go.Scatter(x=resultado.perdida_cristalinidad, y=nac_pct, mode='markers+text', name='NAC', marker=dict(size=14, color=config.C_DORADO), text=[f"{t}h" for t in resultado.tiempos_h], textposition=_textpos_alternado(_n_t, invertido=True), textfont=dict(size=10)))
                fig_sca_area.update_layout(xaxis_title='% Pérdida de Cristalinidad (real, por tiempo)', yaxis_title='Fármaco Liberado (%)', template="plotly_white", margin=dict(t=30, b=30, l=30, r=30), height=480)

                fig_sca_fwhm = go.Figure()
                fig_sca_fwhm.add_trace(go.Scatter(x=resultado.fwhm, y=gsh_pct, mode='markers+text', name='GSH', marker=dict(size=14, color=config.C_AZUL), text=[f"{t}h" for t in resultado.tiempos_h], textposition=_textpos_alternado(_n_t), textfont=dict(size=10)))
                fig_sca_fwhm.add_trace(go.Scatter(x=resultado.fwhm, y=nac_pct, mode='markers+text', name='NAC', marker=dict(size=14, color=config.C_DORADO), text=[f"{t}h" for t in resultado.tiempos_h], textposition=_textpos_alternado(_n_t, invertido=True), textfont=dict(size=10)))
                fig_sca_fwhm.update_layout(xaxis_title='FWHM del pico basal (°2θ)', yaxis_title='Fármaco Liberado (%)', template="plotly_white", margin=dict(t=30, b=30, l=30, r=30), height=480)

                xrd_ctx = dict(
                    resultado=resultado, gsh_pct=gsh_pct, nac_pct=nac_pct,
                    fig_xrd=fig_xrd, fig_degradacion=fig_degradacion, fig_cin=fig_cin,
                    fig_sca_area=fig_sca_area, fig_sca_fwhm=fig_sca_fwhm,
                )
                params_xrd = dict(
                    archivo=getattr(archivo_xrd, 'name', 'archivo subido'),
                    limite_inf=limite_inf, limite_sup=limite_sup, normalizar=usar_normalizacion_xrd,
                )

            t1, t2, t3, t4 = st.tabs(["🧪 Cristalografía", "💧 Cinética", "📈 Correlación", "📄 Datos"])

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
                st.info(f"n = {resultado.pearson_gsh_area['n']} tiempos de medición real. {NOTA_METODOLOGICA_N_BAJO}", icon="ℹ️")
                cA, cB = st.columns(2)
                with cA:
                    st.markdown("**Índice: % Pérdida de Cristalinidad (Área de Simpson)**")
                    cs1, cs2 = st.columns(2)
                    cs1.metric("Pearson r (GSH)", f"{resultado.pearson_gsh_area['r']:.4f}", f"R²={resultado.pearson_gsh_area['r2']:.3f} · p={resultado.pearson_gsh_area['p_value']:.4f}")
                    cs2.metric("Pearson r (NAC)", f"{resultado.pearson_nac_area['r']:.4f}", f"R²={resultado.pearson_nac_area['r2']:.3f} · p={resultado.pearson_nac_area['p_value']:.4f}")
                    st.plotly_chart(fig_sca_area, use_container_width=True)
                    st.caption("⚠️ Este índice depende de la convención de normalización elegida.")
                with cB:
                    st.markdown("**Índice: FWHM (Amorfización)**")
                    cs3, cs4 = st.columns(2)
                    cs3.metric("Pearson r (GSH)", f"{resultado.pearson_gsh_fwhm['r']:.4f}", f"R²={resultado.pearson_gsh_fwhm['r2']:.3f} · p={resultado.pearson_gsh_fwhm['p_value']:.4f}")
                    cs4.metric("Pearson r (NAC)", f"{resultado.pearson_nac_fwhm['r']:.4f}", f"R²={resultado.pearson_nac_fwhm['r2']:.3f} · p={resultado.pearson_nac_fwhm['p_value']:.4f}")
                    st.plotly_chart(fig_sca_fwhm, use_container_width=True)
                    st.caption("✅ Este índice es matemáticamente invariante a la normalización — el más robusto de los dos.")

            with t4:
                st.markdown("### Tabla Maestra XRD (5 tiempos reales sincronizados con cinética)")
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
                st.download_button("📥 Descargar tabla XRD (CSV)", data=df_maestra.to_csv(index=False).encode('utf-8'), file_name="tabla_maestra_xrd.csv", mime="text/csv")

        except Exception as e:
            st.error(f"Error procesando los datos de XRD. Verifica el formato del Excel. Detalle técnico: {e}")
    else:
        st.info("⬆️ Sube el Excel de XRD + Cinética para ejecutar el análisis estructural.", icon="📄")

# ==========================================================================
# PESTAÑA 2: FTIR
# ==========================================================================
with tab_ftir:
    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Parámetros FTIR")
    material_ftir = st.sidebar.selectbox("Material", ["HDL", "GSH", "NAC"], index=0, key="ftir_material")
    banda_inf = st.sidebar.slider("Banda Inferior (cm⁻¹)", 400.0, 3900.0, config.FTIR_BANDA_INF_DEFAULT, 10.0, key="ftir_inf")
    banda_sup = st.sidebar.slider("Banda Superior (cm⁻¹)", 500.0, 4000.0, config.FTIR_BANDA_SUP_DEFAULT, 10.0, key="ftir_sup")
    usar_normalizacion_ftir = st.sidebar.checkbox("Normalizar espectros (Min-Max)", value=True, key="ftir_norm")
    st.sidebar.caption(
        "⚠️ La asignación química de la banda (a qué modo vibracional corresponde) debe confirmarse "
        "con el asesor/director antes de usarla como evidencia en el protocolo."
    )

    archivo_ftir = st.file_uploader("📂 Excel de espectros FTIR (columna 'número de onda' + HDL/GSH/NAC por tiempo)", type=["xlsx"], key="ftir_file")
    archivo_cinetica_ftir = st.file_uploader(
        "📂 Excel con la hoja 'Cinetica' (puede ser el mismo Excel de XRD+Cinética)", type=["xlsx"], key="ftir_kinetics_file"
    )

    if archivo_ftir is not None and archivo_cinetica_ftir is not None:
        try:
            with st.spinner('Ejecutando pipeline FTIR: normalización → Simpson/FWHM → interpolación → Pearson...'):
                resultado_f = pipeline.ejecutar_pipeline_ftir(
                    ruta_excel_ftir=archivo_ftir,
                    ruta_excel_cinetica=archivo_cinetica_ftir,
                    banda_inf=banda_inf,
                    banda_sup=banda_sup,
                    material=material_ftir,
                    normalizar=usar_normalizacion_ftir,
                )

                if all(len(x) == 0 for x, _ in resultado_f.series_ftir.values()):
                    st.warning(f"⚠️ No se encontraron datos entre {banda_inf:.0f} y {banda_sup:.0f} cm⁻¹. Ajusta los sliders.")
                    st.stop()

                df_cin_f = resultado_f.df_cinetica_interpolada
                gsh_pct_f = df_cin_f['Liberacion_GSH_Porcentaje'].to_numpy()
                nac_pct_f = df_cin_f['Liberacion_NAC_Porcentaje'].to_numpy()

                fig_ftir = go.Figure()
                for i, t in enumerate(resultado_f.tiempos_h):
                    x_t, y_t = resultado_f.series_ftir[t]
                    if len(x_t) == 0:
                        continue
                    color = PALETA_TIEMPOS[i % len(PALETA_TIEMPOS)]
                    fig_ftir.add_trace(go.Scatter(
                        x=x_t, y=y_t, mode='lines', name=f'{material_ftir} {t}H',
                        line=dict(color=color, width=2.5),
                        fill='tozeroy' if t in (0, resultado_f.tiempos_h[-1]) else None,
                        opacity=1.0 if t in (0, resultado_f.tiempos_h[-1]) else 0.55,
                    ))
                fig_ftir.update_layout(
                    xaxis_title='Número de onda (cm⁻¹)', yaxis_title='Absorbancia (normalizada)' if usar_normalizacion_ftir else 'Absorbancia',
                    xaxis=dict(autorange='reversed'),  # convención espectroscópica: cm-1 decreciente hacia la derecha
                    template="plotly_white", margin=dict(t=30, b=30, l=30, r=30), height=500,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )

                fig_evolucion_f = go.Figure()
                fig_evolucion_f.add_trace(go.Scatter(x=resultado_f.tiempos_h, y=resultado_f.perdida_banda, mode='lines+markers', name='% Cambio de Banda (Área)', line=dict(color=config.C_AZUL, width=3), marker=dict(size=10)))
                fig_evolucion_f.add_trace(go.Scatter(x=resultado_f.tiempos_h, y=resultado_f.fwhm, mode='lines+markers', name='FWHM Banda', yaxis='y2', line=dict(color=config.C_DORADO, width=3, dash='dot'), marker=dict(size=10, symbol='diamond')))
                fig_evolucion_f.update_layout(
                    xaxis_title='Tiempo (horas)', yaxis_title='% Cambio de Banda',
                    yaxis2=dict(title='FWHM (cm⁻¹)', overlaying='y', side='right'),
                    template="plotly_white", margin=dict(t=30, b=30, l=30, r=30), height=450,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )

                _n_tf = len(resultado_f.tiempos_h)
                fig_sca_area_f = go.Figure()
                fig_sca_area_f.add_trace(go.Scatter(x=resultado_f.perdida_banda, y=gsh_pct_f, mode='markers+text', name='GSH', marker=dict(size=14, color=config.C_AZUL), text=[f"{t}h" for t in resultado_f.tiempos_h], textposition=_textpos_alternado(_n_tf), textfont=dict(size=10)))
                fig_sca_area_f.add_trace(go.Scatter(x=resultado_f.perdida_banda, y=nac_pct_f, mode='markers+text', name='NAC', marker=dict(size=14, color=config.C_DORADO), text=[f"{t}h" for t in resultado_f.tiempos_h], textposition=_textpos_alternado(_n_tf, invertido=True), textfont=dict(size=10)))
                fig_sca_area_f.update_layout(xaxis_title='% Cambio de Banda (real, por tiempo)', yaxis_title='Fármaco Liberado (%)', template="plotly_white", margin=dict(t=30, b=30, l=30, r=30), height=480)

                fig_sca_fwhm_f = go.Figure()
                fig_sca_fwhm_f.add_trace(go.Scatter(x=resultado_f.fwhm, y=gsh_pct_f, mode='markers+text', name='GSH', marker=dict(size=14, color=config.C_AZUL), text=[f"{t}h" for t in resultado_f.tiempos_h], textposition=_textpos_alternado(_n_tf), textfont=dict(size=10)))
                fig_sca_fwhm_f.add_trace(go.Scatter(x=resultado_f.fwhm, y=nac_pct_f, mode='markers+text', name='NAC', marker=dict(size=14, color=config.C_DORADO), text=[f"{t}h" for t in resultado_f.tiempos_h], textposition=_textpos_alternado(_n_tf, invertido=True), textfont=dict(size=10)))
                fig_sca_fwhm_f.update_layout(xaxis_title='FWHM de la banda (cm⁻¹)', yaxis_title='Fármaco Liberado (%)', template="plotly_white", margin=dict(t=30, b=30, l=30, r=30), height=480)

                ftir_ctx = dict(
                    resultado=resultado_f, fig_ftir=fig_ftir, fig_evolucion=fig_evolucion_f,
                    fig_sca_area=fig_sca_area_f, fig_sca_fwhm=fig_sca_fwhm_f,
                )
                params_ftir = dict(
                    archivo_ftir=getattr(archivo_ftir, 'name', 'archivo subido'),
                    archivo_cinetica=getattr(archivo_cinetica_ftir, 'name', 'archivo subido'),
                    material=material_ftir, banda_inf=banda_inf, banda_sup=banda_sup,
                    normalizar=usar_normalizacion_ftir,
                )

            f1, f2, f3 = st.tabs(["🧪 Espectros", "📈 Correlación", "📄 Datos"])

            with f1:
                st.markdown(f"### Espectro FTIR — Material: {material_ftir}")
                c1, c2, c3 = st.columns(3)
                c1.metric("% Cambio de Banda (96h)", f"{resultado_f.perdida_banda[-1]:.2f}%", delta="vs 0h", delta_color="inverse")
                c2.metric("FWHM inicial → final", f"{resultado_f.fwhm[0]:.2f} → {resultado_f.fwhm[-1]:.2f} cm⁻¹")
                c3.metric("Posición banda (0h → 96h)", f"{resultado_f.posicion_banda_cm1[0]:.1f} → {resultado_f.posicion_banda_cm1[-1]:.1f} cm⁻¹")
                st.plotly_chart(fig_ftir, use_container_width=True)
                st.markdown("#### Evolución de los Índices Químicos (5 tiempos reales)")
                st.plotly_chart(fig_evolucion_f, use_container_width=True)

            with f2:
                st.markdown("### Correlación: Cambio Químico Real vs Liberación de Fármaco")
                st.info(f"n = {resultado_f.pearson_gsh_area['n']} tiempos de medición real. {NOTA_METODOLOGICA_N_BAJO}", icon="ℹ️")
                cA, cB = st.columns(2)
                with cA:
                    st.markdown("**Índice: % Cambio de Banda (Área de Simpson)**")
                    cs1, cs2 = st.columns(2)
                    cs1.metric("Pearson r (GSH)", f"{resultado_f.pearson_gsh_area['r']:.4f}", f"R²={resultado_f.pearson_gsh_area['r2']:.3f} · p={resultado_f.pearson_gsh_area['p_value']:.4f}")
                    cs2.metric("Pearson r (NAC)", f"{resultado_f.pearson_nac_area['r']:.4f}", f"R²={resultado_f.pearson_nac_area['r2']:.3f} · p={resultado_f.pearson_nac_area['p_value']:.4f}")
                    st.plotly_chart(fig_sca_area_f, use_container_width=True)
                with cB:
                    st.markdown("**Índice: FWHM de Banda**")
                    cs3, cs4 = st.columns(2)
                    cs3.metric("Pearson r (GSH)", f"{resultado_f.pearson_gsh_fwhm['r']:.4f}", f"R²={resultado_f.pearson_gsh_fwhm['r2']:.3f} · p={resultado_f.pearson_gsh_fwhm['p_value']:.4f}")
                    cs4.metric("Pearson r (NAC)", f"{resultado_f.pearson_nac_fwhm['r']:.4f}", f"R²={resultado_f.pearson_nac_fwhm['r2']:.3f} · p={resultado_f.pearson_nac_fwhm['p_value']:.4f}")
                    st.plotly_chart(fig_sca_fwhm_f, use_container_width=True)
                    st.caption("✅ Este índice es matemáticamente invariante a la normalización.")

            with f3:
                st.markdown("### Tabla Maestra FTIR (5 tiempos reales sincronizados con cinética)")
                df_maestra_f = pd.DataFrame({
                    'Tiempo (h)': resultado_f.tiempos_h,
                    'Área Simpson': np.round(resultado_f.areas, 4),
                    'FWHM (cm⁻¹)': np.round(resultado_f.fwhm, 4),
                    'Posición Banda (cm⁻¹)': np.round(resultado_f.posicion_banda_cm1, 2),
                    '% Cambio de Banda': np.round(resultado_f.perdida_banda, 2),
                    '% GSH Liberado': gsh_pct_f,
                    '% NAC Liberado': nac_pct_f,
                })
                st.dataframe(df_maestra_f, use_container_width=True, hide_index=True)
                st.download_button("📥 Descargar tabla FTIR (CSV)", data=df_maestra_f.to_csv(index=False).encode('utf-8'), file_name="tabla_maestra_ftir.csv", mime="text/csv")

        except Exception as e:
            st.error(f"Error procesando los datos de FTIR. Verifica el formato del Excel. Detalle técnico: {e}")
    else:
        st.info("⬆️ Sube el Excel de espectros FTIR y el Excel con la hoja 'Cinetica' para ejecutar el análisis químico.", icon="📄")

# ==========================================================================
# DESCARGA DE SNAPSHOT (PDF y HTML, combinado si ambos análisis se ejecutaron)
# ==========================================================================
if xrd_ctx is not None or ftir_ctx is not None:
    params_snapshot = dict(
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M'),
        xrd=params_xrd,
        ftir=params_ftir,
    )
    sello = datetime.now().strftime('%Y%m%d_%H%M')

    st.sidebar.markdown("---")
    st.sidebar.subheader("📸 Snapshot del Análisis")
    st.sidebar.caption(
        "Captura los parámetros actuales (sliders, normalización, archivos) y todas las gráficas en un "
        "reporte explicado. Genera uno nuevo cada vez que ajustes la configuración."
    )

    pdf_bytes = generar_pdf(xrd_ctx, ftir_ctx, params_snapshot)
    st.sidebar.download_button(
        label="📸 Descargar Snapshot (PDF)",
        data=pdf_bytes,
        file_name=f"Snapshot_HDL_Suite_{sello}.pdf",
        mime="application/pdf",
    )

    html_snapshot = generar_html_snapshot(xrd_ctx, ftir_ctx, params_snapshot)
    st.sidebar.download_button(
        label="📸 Descargar Snapshot (HTML, para adjuntar en correo)",
        data=html_snapshot.encode('utf-8'),
        file_name=f"Snapshot_HDL_Suite_{sello}.html",
        mime="text/html",
    )
