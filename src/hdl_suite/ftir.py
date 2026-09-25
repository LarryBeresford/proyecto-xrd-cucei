"""
Análisis de espectros FTIR (Espectroscopía Infrarroja por Transformada de
Fourier) — segunda técnica estructural/química requerida por el objetivo
general del proyecto ("...cambios estructurales y/o químicos detectables
por XRD y FTIR...", ver presentación de planteamiento del asesor).

Racional físico-químico: mientras que XRD (bragg.py, crystallinity.py)
mide el orden de largo alcance del apilamiento laminar, FTIR es sensible
a los enlaces químicos específicos (vibraciones de tensión y flexión de
grupos funcionales). Rastrear cómo cambia el área, el ancho (FWHM) y la
posición de una banda característica del HDL o de las moléculas
intercaladas (GSH, NAC) a lo largo del tiempo aporta una segunda línea de
evidencia -de naturaleza química, no solo estructural- para la hipótesis
del proyecto: que la liberación del fármaco está acompañada de un cambio
químico/estructural medible, no solo de una pérdida de orden cristalino.

Nota metodológica importante: a diferencia de la Ley de Bragg (exclusiva
de difracción de rayos X), en FTIR NO se calcula un espaciado interlaminar
a partir de la posición de la banda. Aquí la posición de la banda
(numero de onda, cm-1) se reporta directamente como "desplazamiento de
banda", y su interpretación química (a qué modo vibracional corresponde)
debe ser confirmada por el asesor/director según la asignación
espectroscópica conocida del sistema HDL-GSH/NAC-NO3.
"""
import numpy as np
import pandas as pd

from . import config

MATERIALES_VALIDOS = ("HDL", "GSH", "NAC")


def _parsear_encabezados_ftir(df_crudo: pd.DataFrame) -> pd.DataFrame:
    """
    Reestructura el bloque de 3 filas de encabezado del Excel de FTIR
    (fila 0: material HDL/GSH/NAC repetido; fila 1: unidades, se ignora;
    fila 2: tiempo '0H'/'24H'/...) en columnas planas 'x', 'HDL_0H',
    'GSH_0H', etc. Función separada de la lectura de Excel para poder
    probarla unitariamente sin depender de un archivo en disco.
    """
    fila_material = df_crudo.iloc[0].tolist()
    fila_tiempo = df_crudo.iloc[2].tolist()

    columnas = ['x']
    for material, tiempo in zip(fila_material[1:], fila_tiempo[1:]):
        tiempo_str = str(tiempo).upper().replace('H', '') if pd.notna(tiempo) else ''
        columnas.append(f"{material}_{tiempo_str}H")

    datos = df_crudo.iloc[3:].reset_index(drop=True).copy()
    datos.columns = columnas
    for col in datos.columns:
        datos[col] = pd.to_numeric(datos[col], errors='coerce')

    datos = datos.dropna(subset=['x']).sort_values('x').reset_index(drop=True)
    return datos


def cargar_ftir_crudo(ruta_excel: str, hoja=0) -> pd.DataFrame:
    """
    Carga el Excel de espectros FTIR (formato: fila 1 = material,
    fila 2 = unidades, fila 3 = tiempo, fila 4 en adelante = datos;
    primera columna = número de onda en cm-1).
    """
    df_crudo = pd.read_excel(ruta_excel, sheet_name=hoja, header=None)
    return _parsear_encabezados_ftir(df_crudo)


def obtener_serie_ftir(df_ftir: pd.DataFrame, material: str, tiempo_h: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Extrae (numero_de_onda, absorbancia) para un material (HDL/GSH/NAC) y
    tiempo específico (0, 24, 48, 72 o 96 horas).
    """
    material = material.upper()
    if material not in MATERIALES_VALIDOS:
        raise ValueError(f"Material '{material}' no reconocido. Use uno de {MATERIALES_VALIDOS}.")

    col = f"{material}_{tiempo_h}H"
    if col not in df_ftir.columns:
        raise ValueError(
            f"No existe la columna '{col}' en los datos de FTIR. "
            f"Columnas disponibles: {list(df_ftir.columns)}"
        )
    sub = df_ftir[['x', col]].dropna()
    return sub['x'].to_numpy(), sub[col].to_numpy()
