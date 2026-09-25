"""
Preprocesamiento: normalización Min-Max de diffractogramas.

Racional físico: la intensidad absoluta de un difractograma depende de
factores instrumentales (cantidad de muestra, tiempo de conteo,
calibración del día de medición) que no tienen relación con la estructura
del material. Comparar áreas o alturas absolutas entre corridas distintas
introduce un sesgo instrumental. La normalización Min-Max lleva cada señal
al intervalo [0, 1], de modo que las comparaciones entre tiempos reflejen
únicamente cambios en la *forma* del pico (orden cristalino), no en la
escala de medición.
"""
import numpy as np


def normalizar_min_max(y: np.ndarray) -> np.ndarray:
    """
    Aplica normalización Min-Max: y_norm = (y - min(y)) / (max(y) - min(y)).

    Devuelve el arreglo sin modificar si está vacío o si es constante
    (max == min), para evitar división entre cero.
    """
    y = np.asarray(y, dtype=float)
    if y.size == 0:
        return y
    y_min, y_max = np.min(y), np.max(y)
    if np.isclose(y_max, y_min):
        return y
    return (y - y_min) / (y_max - y_min)
