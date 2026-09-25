"""
Cuantificación de cristalinidad y amorfización del pico basal del HDL.

Dos índices de degradación, deliberadamente independientes entre sí, para
que el argumento de "colapso estructural" no dependa de una sola métrica:

1. Área bajo la curva (Regla de Simpson compuesta): el área del pico es
   proporcional a la cantidad de material en fase cristalina ordenada que
   contribuye a esa reflexión. Su pérdida porcentual respecto a t=0h es el
   "Índice de Pérdida de Cristalinidad".

2. FWHM (Full Width at Half Maximum): un cristal perfectamente ordenado
   difracta en un ángulo muy preciso, produciendo picos angostos. Defectos,
   dominios cristalinos más pequeños o desorden estructural ensanchan el
   pico. El crecimiento del FWHM en el tiempo es el "Índice de
   Amorfización".
"""
import numpy as np
from scipy.integrate import simpson
from scipy.signal import peak_widths


def recortar_ventana(x: np.ndarray, y: np.ndarray, limite_inf: float, limite_sup: float):
    """Aísla la región angular donde se ubica el pico de interés."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = (x >= limite_inf) & (x <= limite_sup)
    return x[mask], y[mask]


def calcular_area_simpson(x: np.ndarray, y: np.ndarray) -> float:
    """
    Integra numéricamente el área bajo la curva y = f(x) usando la Regla
    de Simpson compuesta (scipy.integrate.simpson), que aproxima la curva
    entre puntos consecutivos con parábolas, ideal para picos de forma
    suave tipo campana como los de difracción de rayos X.

    Si el número de puntos es insuficiente (<3) para Simpson, cae a la
    regla del trapecio como respaldo, en vez de fallar silenciosamente.
    """
    if len(x) < 2 or len(y) < 2:
        return 0.0
    if len(x) < 3:
        return float(np.trapz(y, x))
    return float(simpson(y=y, x=x))


def calcular_fwhm(x: np.ndarray, y: np.ndarray) -> float:
    """
    Calcula el ancho a media altura (FWHM) del pico máximo dentro de la
    ventana ya recortada (x, y). Localiza automáticamente el índice del
    máximo, por lo que no requiere que el llamador conozca la posición
    del pico de antemano.

    Devuelve 0.0 si no hay suficientes puntos para estimar un ancho
    (degradación total / pico desaparecido), en vez de lanzar una
    excepción que interrumpiría el pipeline completo.
    """
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    if len(y) < 3 or np.all(y == 0):
        return 0.0
    try:
        pico_idx = int(np.argmax(y))
        resultados = peak_widths(y, [pico_idx], rel_height=0.5)
        ancho_en_muestras = resultados[0][0]
        # Espaciado angular promedio real (más robusto que x[1]-x[0] solo,
        # ante pequeñas irregularidades de muestreo del difractómetro).
        dx_promedio = float(np.mean(np.diff(x))) if len(x) > 1 else 0.0
        return abs(ancho_en_muestras * dx_promedio)
    except Exception:
        return 0.0


def indice_perdida_cristalinidad(area_referencia: float, area_actual: float) -> float:
    """
    % de pérdida de cristalinidad respecto al material intacto (t=0h):
        perdida (%) = (area_0h - area_t) / area_0h * 100
    """
    if area_referencia == 0:
        return 0.0
    return (area_referencia - area_actual) / area_referencia * 100.0
