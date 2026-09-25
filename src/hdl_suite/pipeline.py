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

from . import config, data_io, preprocessing, bragg, crystallinity, kinetics, correlation, ftir


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

        # Importante: la normalización se aplica sobre el ESPECTRO COMPLETO,
        # antes de recortar la ventana del pico. Normalizar después de
        # recortar reescala cada ventana a su propio máximo local, lo cual
        # destruye la comparabilidad de área/FWHM entre tiempos (cada
        # ventana terminaría con altura máxima = 1 sin importar cuánto se
        # haya degradado realmente el pico).
        if normalizar:
            y_raw = preprocessing.normalizar_min_max(y_raw)

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


@dataclass
class ResultadoAnalisisFTIR:
    tiempos_h: list
    material: str
    areas: list
    fwhm: list
    posicion_banda_cm1: list
    perdida_banda: list  # % de cambio del área de la banda vs t=0h (puede ser + o -)
    df_cinetica_interpolada: pd.DataFrame
    pearson_gsh_area: dict
    pearson_nac_area: dict
    pearson_gsh_fwhm: dict
    pearson_nac_fwhm: dict
    series_ftir: dict = field(default_factory=dict)
    banda_inf: float = config.FTIR_BANDA_INF_DEFAULT
    banda_sup: float = config.FTIR_BANDA_SUP_DEFAULT
    normalizado: bool = True


def ejecutar_pipeline_ftir(
    ruta_excel_ftir: str = config.ARCHIVO_EXCEL_FTIR_DEFAULT,
    ruta_excel_cinetica: str = config.ARCHIVO_EXCEL_DEFAULT,
    banda_inf: float = config.FTIR_BANDA_INF_DEFAULT,
    banda_sup: float = config.FTIR_BANDA_SUP_DEFAULT,
    material: str = config.FTIR_MATERIAL_DEFAULT,
    normalizar: bool = True,
    tiempos_h: list = None,
) -> ResultadoAnalisisFTIR:
    """
    Pipeline paralelo al de XRD, pero para espectros FTIR. Reutiliza el
    mismo núcleo numérico (crystallinity.calcular_area_simpson /
    calcular_fwhm, kinetics.interpolar_cinetica, correlation.calcular_pearson)
    -- la Ley de Bragg NO aplica aquí, por lo que en su lugar se reporta la
    posición (numero de onda, cm-1) de la banda característica en cada
    tiempo, como indicador de desplazamiento químico.

    Parameters
    ----------
    ruta_excel_ftir : ruta al Excel de espectros FTIR ("Datos Degradación
        FTIR.xlsx" o equivalente: 3 filas de encabezado, columna 'x' en
        cm-1, columnas '{MATERIAL}_{T}H').
    ruta_excel_cinetica : ruta al Excel que contiene la hoja 'Cinetica'
        (por defecto el Excel maestro de XRD, ya que la cinética no está
        duplicada en el archivo de FTIR).
    banda_inf, banda_sup : ventana espectral (cm-1) de la banda a analizar.
    material : 'HDL', 'GSH' o 'NAC' -- qué espectro se analiza.
    """
    if tiempos_h is None:
        tiempos_h = config.TIEMPOS_XRD_HORAS

    df_ftir = ftir.cargar_ftir_crudo(ruta_excel_ftir)

    series_ftir, areas, fwhm_vals, posicion_banda = {}, [], [], []

    for t in tiempos_h:
        x_raw, y_raw = ftir.obtener_serie_ftir(df_ftir, material, t)

        if normalizar:
            y_raw = preprocessing.normalizar_min_max(y_raw)

        x_win, y_win = crystallinity.recortar_ventana(x_raw, y_raw, banda_inf, banda_sup)

        if len(x_win) == 0:
            series_ftir[t] = (x_win, y_win)
            areas.append(0.0)
            fwhm_vals.append(0.0)
            posicion_banda.append(np.nan)
            continue

        series_ftir[t] = (x_win, y_win)
        areas.append(crystallinity.calcular_area_simpson(x_win, y_win))
        fwhm_vals.append(crystallinity.calcular_fwhm(x_win, y_win))

        idx_pico = int(np.argmax(y_win))
        posicion_banda.append(float(x_win[idx_pico]))

    area_0h = areas[0] if areas else 0.0
    perdida_banda = [
        crystallinity.indice_perdida_cristalinidad(area_0h, a) for a in areas
    ]

    df_cin_cruda = data_io.cargar_cinetica_cruda(ruta_excel_cinetica)
    df_cin_interp = kinetics.interpolar_cinetica(df_cin_cruda, horas_objetivo=tiempos_h)

    gsh_pct = df_cin_interp['Liberacion_GSH_Porcentaje'].to_numpy()
    nac_pct = df_cin_interp['Liberacion_NAC_Porcentaje'].to_numpy()

    pearson_gsh_area = correlation.calcular_pearson(perdida_banda, gsh_pct)
    pearson_nac_area = correlation.calcular_pearson(perdida_banda, nac_pct)
    pearson_gsh_fwhm = correlation.calcular_pearson(fwhm_vals, gsh_pct)
    pearson_nac_fwhm = correlation.calcular_pearson(fwhm_vals, nac_pct)

    return ResultadoAnalisisFTIR(
        tiempos_h=list(tiempos_h),
        material=material,
        areas=areas,
        fwhm=fwhm_vals,
        posicion_banda_cm1=posicion_banda,
        perdida_banda=perdida_banda,
        df_cinetica_interpolada=df_cin_interp,
        pearson_gsh_area=pearson_gsh_area,
        pearson_nac_area=pearson_nac_area,
        pearson_gsh_fwhm=pearson_gsh_fwhm,
        pearson_nac_fwhm=pearson_nac_fwhm,
        series_ftir=series_ftir,
        banda_inf=banda_inf,
        banda_sup=banda_sup,
        normalizado=normalizar,
    )
