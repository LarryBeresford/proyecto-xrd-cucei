"""
Motor de sincronización temporal (interpolación lineal).

Racional: la cinética de liberación se mide en minutos, con muestreos
irregulares (más frecuentes al inicio del experimento). La cristalografía
(XRD) se mide en cortes fijos de horas (0, 24, 48, 72, 96h). Para poder
correlacionar ambas variables se necesita evaluarlas en los *mismos*
instantes de tiempo. Este módulo construye una función continua a partir
de los puntos reales de cinética (interp1d lineal) y la evalúa
exactamente en los minutos correspondientes a cada tiempo de muestreo
XRD.

Limitación a reconocer explícitamente ante el comité: la interpolación
lineal asume que el comportamiento entre dos mediciones reales es una
línea recta. Es una aproximación razonable para curvas de liberación que
no oscilan bruscamente entre muestras, pero no captura una posible
cinética no lineal fina entre puntos.
"""
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

from . import config


def interpolar_cinetica(
    df_cinetica: pd.DataFrame,
    horas_objetivo: list[int] = config.TIEMPOS_XRD_HORAS,
    clip_0_100: bool = True,
) -> pd.DataFrame:
    """
    Proyecta Liberacion_GSH y Liberacion_NAC (medidas en minutos) sobre
    la malla temporal del XRD (horas_objetivo, convertidas a minutos).

    Parameters
    ----------
    df_cinetica : DataFrame con columnas Tiempo, Liberacion_GSH,
        Liberacion_NAC (ya limpio, ver data_io.cargar_cinetica_cruda).
    horas_objetivo : tiempos XRD (horas) en los que se desea el valor
        interpolado de liberación.
    clip_0_100 : si True, acota el resultado a [0, 100] % para evitar que
        la extrapolación en los bordes produzca porcentajes físicamente
        imposibles.
    """
    horas_objetivo = np.array(horas_objetivo, dtype=float)
    minutos_objetivo = horas_objetivo * 60.0

    tiempos_reales = df_cinetica['Tiempo'].to_numpy()
    gsh_real = df_cinetica['Liberacion_GSH'].to_numpy()
    nac_real = df_cinetica['Liberacion_NAC'].to_numpy()

    funcion_gsh = interp1d(tiempos_reales, gsh_real, kind='linear', fill_value='extrapolate')
    funcion_nac = interp1d(tiempos_reales, nac_real, kind='linear', fill_value='extrapolate')

    gsh_interp = funcion_gsh(minutos_objetivo)
    nac_interp = funcion_nac(minutos_objetivo)

    if clip_0_100:
        gsh_interp = np.clip(gsh_interp, 0, 100)
        nac_interp = np.clip(nac_interp, 0, 100)

    df_unificado = pd.DataFrame({
        'Tiempo_Horas': horas_objetivo,
        'Tiempo_Minutos': minutos_objetivo,
        'Liberacion_GSH_Porcentaje': np.round(gsh_interp, 2),
        'Liberacion_NAC_Porcentaje': np.round(nac_interp, 2),
    })

    # Por lógica química/física: en t=0 no ha habido liberación todavía.
    df_unificado.loc[df_unificado['Tiempo_Horas'] == 0, 'Liberacion_GSH_Porcentaje'] = 0.0
    df_unificado.loc[df_unificado['Tiempo_Horas'] == 0, 'Liberacion_NAC_Porcentaje'] = 0.0

    return df_unificado
