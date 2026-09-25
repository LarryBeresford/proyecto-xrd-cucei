"""
Carga y limpieza de datos crudos (Excel de laboratorio).

Racional: el archivo Excel entregado por el laboratorio mezcla texto de
error ('--'), encabezados repetidos y columnas de desviación estándar
dentro de la misma hoja. Este módulo aísla toda esa "cirugía de datos" en
un solo lugar para que el resto del pipeline reciba siempre arreglos
NumPy/columnas Pandas ya limpias y numéricas.
"""
import pandas as pd
import numpy as np
import warnings

from . import config

warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# Nombre de la hoja y de las columnas tal como aparecen en el Excel maestro.
HOJA_XRD = 'XRD diferentes tiempos'
HOJA_CINETICA = 'Cinetica'


def _resolver_nombre_hoja(ruta_excel, nombre_esperado: str) -> str:
    """
    Encuentra el nombre real de una hoja dentro del Excel, tolerando
    mayúsculas/minúsculas y espacios extra al inicio/final (variaciones
    comunes cuando el archivo se reexporta desde distinto software).

    Si no se encuentra ninguna coincidencia razonable, lanza un error que
    lista las hojas realmente presentes en el archivo -- la causa más
    frecuente es haber subido el archivo equivocado (p.ej. el Excel de
    FTIR en el uploader de XRD, o viceversa), y ese mensaje debe dejarlo
    claro de inmediato en vez de mostrar un KeyError críptico.
    """
    xls = pd.ExcelFile(ruta_excel)
    hojas_disponibles = xls.sheet_names

    if nombre_esperado in hojas_disponibles:
        return nombre_esperado

    objetivo = nombre_esperado.strip().lower()
    for hoja in hojas_disponibles:
        if hoja.strip().lower() == objetivo:
            return hoja

    raise ValueError(
        f"No se encontró la hoja '{nombre_esperado}' en el archivo subido. "
        f"Hojas disponibles en este Excel: {hojas_disponibles}. "
        "Verifica que estás subiendo el archivo correcto en esta pestaña "
        "(el Excel de XRD+Cinética y el Excel de espectros FTIR son archivos "
        "distintos y no son intercambiables)."
    )


def cargar_xrd_crudo(ruta_excel: str = config.ARCHIVO_EXCEL_DEFAULT) -> pd.DataFrame:
    """
    Carga la hoja de XRD y fuerza todas las columnas a numérico,
    convirtiendo marcadores de error ('--', texto, celdas vacías) en NaN.
    """
    hoja_real = _resolver_nombre_hoja(ruta_excel, HOJA_XRD)
    df = pd.read_excel(ruta_excel, sheet_name=hoja_real)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def cargar_cinetica_cruda(ruta_excel: str = config.ARCHIVO_EXCEL_DEFAULT) -> pd.DataFrame:
    """
    Carga la hoja de Cinética, renombra columnas a nombres científicos
    estándar (Tiempo, Liberacion_GSH, Liberacion_NAC) y descarta filas de
    encabezado/unidades que no son datos numéricos reales.
    """
    hoja_real = _resolver_nombre_hoja(ruta_excel, HOJA_CINETICA)
    df = pd.read_excel(ruta_excel, sheet_name=hoja_real, skiprows=1)
    df = df.rename(columns={
        'Unnamed: 0': 'Tiempo',
        'GSH': 'Liberacion_GSH',
        'NAC': 'Liberacion_NAC',
    })
    columnas_util = ['Tiempo', 'Liberacion_GSH', 'Liberacion_NAC']
    for col in columnas_util:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=columnas_util)
    return df.reset_index(drop=True)


def obtener_serie_hdl(df_xrd: pd.DataFrame, tiempo_h: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Extrae (angulo_2theta, intensidad) para el material HDL en un tiempo
    de degradación específico (0, 24, 48, 72 o 96 horas).

    Racional: el Excel maestro usa dos columnas de ángulo distintas
    ('Angulo 2tetha' para 0H, 'Angulo 2tetha.1' para 24/48/72/96H) porque
    cada corrida del difractómetro genera su propio eje de ángulos. Este
    desacoplamiento entre "tiempo" y "columna de ángulo" se resuelve aquí
    una sola vez, en vez de repetirse en cada script.
    """
    if tiempo_h == 0:
        col_angulo = 'Angulo 2tetha'
    else:
        col_angulo = 'Angulo 2tetha.1'
    col_intensidad = f'HDL {tiempo_h}H'

    if col_intensidad not in df_xrd.columns:
        raise ValueError(
            f"No existe la columna '{col_intensidad}' en la hoja '{HOJA_XRD}'. "
            f"Tiempos disponibles esperados: {config.TIEMPOS_XRD_HORAS}"
        )

    sub = df_xrd[[col_angulo, col_intensidad]].dropna()
    return sub[col_angulo].to_numpy(), sub[col_intensidad].to_numpy()
