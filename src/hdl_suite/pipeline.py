"""
Pipeline de alto nivel: orquesta las 4 etapas del análisis sobre un
archivo Excel de laboratorio y devuelve un único diccionario de
resultados listo para ser consumido por la app de Streamlit o por los
scripts de generación de reportes.

Esta es la pieza central que "arma" el argumento científico completo:
para cada uno de los 5 tiempos de muestreo XRD reales (0, 24, 48, 72,
96h) calcula el área de Simpson, el FWHM y el espaciado de Bragg del pico
basal del HDL; sincroniza la cinética de liberación (GSH y NAC) sobre esa
misma malla de tiempos mediante interpolación lineal; y finalmente
corre Pearson entre la degradación estructural real (no sintética) y la
liberación de fármaco.
"""
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

from . import config, data_io, preprocessing, bragg, crystallinity, kinetics, correlation


@dataclass
class ResultadoAnalisis:
    tiempos_h: list
    areas: list
    fwhm: list
    d_spacing: list
    pico_2theta: list
    perdida_cristalinidad: list
    df_cinetica_interpolada: pd.DataFrame
    pearson_gsh_area: dict
    pearson_nac_area: dict
    pearson_gsh_fwhm: dict
    pearson_nac_fwhm: dict
    series_xrd: dict = field(default_factory=dict)  # tiempo_h -> (x, y) ya recortado/normalizado
    limite_inf: float = config.LIMITE_INF_DEFAULT
    limite_sup: float = config.LIMITE_SUP_DEFAULT
    normalizado: bool = True


def ejecutar_pipeline(
    ruta_excel: str = config.ARCHIVO_EXCEL_DEFAULT,
    limite_inf: float = config.LIMITE_INF_DEFAULT,
    limite_sup: float = config.LIMITE_SUP_DEFAULT,
    normalizar: bool = True,
    tiempos_h: list = None,
) -> ResultadoAnalisis:
    """
    Ejecuta el pipeline completo de 4 etapas sobre un archivo Excel.

    Parameters
    ----------
    ruta_excel : ruta al Excel maestro (hojas 'XRD diferentes tiempos' y
        'Cinetica').
    limite_inf, limite_sup : ventana angular (2theta, grados) donde se
        ubica el pico basal principal del HDL.
    normalizar : si True, aplica normalización Min-Max a cada
        diffractograma antes de integrar/medir FWHM.
    tiempos_h : lista de tiempos XRD a analizar; por defecto
        config.TIEMPOS_XRD_HORAS = [0, 24, 48, 72, 96].
    """
    if tiempos_h is None:
        tiempos_h = config.TIEMPOS_XRD_HORAS

    # --- ETAPA 1 y 2: carga, normalización y análisis cristalográfico ---
    df_xrd = data_io.cargar_xrd_crudo(ruta_excel)

    series_xrd, areas, fwhm_vals, d_spacing_vals, pico_2theta_vals = {}, [], [], [], []

    for t in tiempos_h:
        x_raw, y_raw = data_io.obtener_serie_hdl(df_xrd, t)
        x_win, y_win = crystallinity.recortar_ventana(x_raw, y_raw, limite_inf, limite_sup)

        if len(x_win) == 0:
            # Ventana sin datos: se registra como degradación total (0)
            # en vez de romper el pipeline completo por un mal ajuste de sliders.
            series_xrd[t] = (x_win, y_win)
            areas.append(0.0)
            fwhm_vals.append(0.0)
            d_spacing_vals.append(np.nan)
            pico_2theta_vals.append(np.nan)
            continue

        if normalizar:
            y_win = preprocessing.normalizar_min_max(y_win)

        series_xrd[t] = (x_win, y_win)
        areas.append(crystallinity.calcular_area_simpson(x_win, y_win))
        fwhm_vals.append(crystallinity.calcular_fwhm(x_win, y_win))

        idx_pico = int(np.argmax(y_win))
        angulo_pico = float(x_win[idx_pico])
        pico_2theta_vals.append(angulo_pico)
        d_spacing_vals.append(bragg.calcular_distancia_bragg(angulo_pico))

    area_0h = areas[0] if areas else 0.0
    perdida_cristalinidad = [
        crystallinity.indice_perdida_cristalinidad(area_0h, a) for a in areas
    ]

    # --- ETAPA 3: sincronización temporal de la cinética ---
    df_cin_cruda = data_io.cargar_cinetica_cruda(ruta_excel)
    df_cin_interp = kinetics.interpolar_cinetica(df_cin_cruda, horas_objetivo=tiempos_h)

    # --- ETAPA 4: inferencia estadística (Pearson) ---
    # Se usa la degradación REAL medida en cada tiempo (no una rampa
    # sintética), tanto vía área de Simpson como vía FWHM, para robustecer
    # el argumento con dos índices independientes.
    gsh_pct = df_cin_interp['Liberacion_GSH_Porcentaje'].to_numpy()
    nac_pct = df_cin_interp['Liberacion_NAC_Porcentaje'].to_numpy()

    pearson_gsh_area = correlation.calcular_pearson(perdida_cristalinidad, gsh_pct)
    pearson_nac_area = correlation.calcular_pearson(perdida_cristalinidad, nac_pct)
    pearson_gsh_fwhm = correlation.calcular_pearson(fwhm_vals, gsh_pct)
    pearson_nac_fwhm = correlation.calcular_pearson(fwhm_vals, nac_pct)

    return ResultadoAnalisis(
        tiempos_h=list(tiempos_h),
        areas=areas,
        fwhm=fwhm_vals,
        d_spacing=d_spacing_vals,
        pico_2theta=pico_2theta_vals,
        perdida_cristalinidad=perdida_cristalinidad,
        df_cinetica_interpolada=df_cin_interp,
        pearson_gsh_area=pearson_gsh_area,
        pearson_nac_area=pearson_nac_area,
        pearson_gsh_fwhm=pearson_gsh_fwhm,
        pearson_nac_fwhm=pearson_nac_fwhm,
        series_xrd=series_xrd,
        limite_inf=limite_inf,
        limite_sup=limite_sup,
        normalizado=normalizar,
    )
