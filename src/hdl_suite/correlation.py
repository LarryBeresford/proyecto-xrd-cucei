"""
Inferencia estadística: correlación de Pearson entre degradación
estructural real (medida en cada uno de los 5 tiempos de XRD) y
liberación de fármaco interpolada en esos mismos tiempos.

Nota metodológica importante (documentar en el protocolo): con n=5
puntos de tiempo, el poder estadístico de la prueba es limitado. Un
p-value < 0.05 con n=5 es evidencia cuantitativa sugestiva -y ya superior
a la inspección visual subjetiva que se buscaba reemplazar- pero no debe
presentarse como una prueba estadística robusta en el sentido clásico.
Se recomienda declarar esta limitación de forma proactiva y proponer,
como trabajo futuro, aumentar la densidad de muestreo XRD.
"""
import numpy as np
from scipy.stats import pearsonr


def calcular_pearson(x: np.ndarray, y: np.ndarray) -> dict:
    """
    Calcula r de Pearson y su p-value asociado entre dos series
    numéricas de igual longitud (p.ej. Índice de Pérdida de Cristalinidad
    vs. % de fármaco liberado, ambos evaluados en los mismos tiempos).

    Devuelve un diccionario con r, p_value, n (tamaño de muestra) y una
    bandera n_bajo que advierte cuando n < 8 (regla práctica común para
    considerar baja la potencia estadística de una prueba de Pearson).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    if len(x) != len(y):
        raise ValueError("Las series de degradación y liberación deben tener la misma longitud.")
    if len(x) < 2:
        return {"r": np.nan, "p_value": np.nan, "n": len(x), "n_bajo": True}

    r, p_value = pearsonr(x, y)
    return {
        "r": float(r),
        "p_value": float(p_value),
        "n": len(x),
        "n_bajo": len(x) < 8,
    }
