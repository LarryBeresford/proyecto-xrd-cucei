"""
Ley de Bragg: traduce la posición angular de un pico de difracción a una
distancia interlaminar física (colapso/expansión de las capas del HDL).

    n * lambda = 2 * d * sin(theta)   =>   d = n*lambda / (2 * sin(theta))

Racional físico: en un Hidróxido Doble Laminar (HDL), la estructura es un
apilamiento de láminas cargadas positivamente con aniones (y, en este
sistema, moléculas de fármaco) intercalados entre ellas. El pico de
difracción a bajo ángulo (2theta pequeño) corresponde al plano basal
(00l), cuya posición está determinada directamente por la distancia entre
láminas consecutivas. Si el fármaco escapa y la estructura colapsa o se
reordena, esa distancia cambia, y por lo tanto el pico se desplaza. Medir
ese desplazamiento en angstroms convierte una observación cualitativa
("el pico se movió") en una medida física cuantitativa del colapso
estructural.
"""
import numpy as np

from . import config


def calcular_distancia_bragg(
    angulo_2theta_grados: float,
    longitud_onda_nm: float = config.LONGITUD_ONDA_CU_KALPHA_ANGSTROM,
    orden_difraccion_n: int = 1,
) -> float:
    """
    Calcula el espaciado interlaminar d (mismas unidades que
    longitud_onda_nm; por defecto angstroms, ya que se usa
    lambda(Cu-K-alpha) = 1.5406 A).

    Parameters
    ----------
    angulo_2theta_grados : ángulo de difracción 2theta, en grados.
    longitud_onda_nm : longitud de onda de la fuente de rayos X.
    orden_difraccion_n : orden de difracción (n=1 para el pico basal
        principal, que es el caso de interés en este proyecto).
    """
    theta_rad = np.radians(angulo_2theta_grados / 2.0)
    d_spacing = (orden_difraccion_n * longitud_onda_nm) / (2 * np.sin(theta_rad))
    return d_spacing


def angulo_desde_d(
    d_spacing_nm: float,
    longitud_onda_nm: float = config.LONGITUD_ONDA_CU_KALPHA_ANGSTROM,
    orden_difraccion_n: int = 1,
) -> float:
    """
    Inversa de la Ley de Bragg: dado un espaciado d, devuelve el ángulo
    2theta (grados) esperado. Útil para pruebas de consistencia
    (round-trip) y para validar el módulo ante el comité de titulación.
    """
    theta_rad = np.arcsin((orden_difraccion_n * longitud_onda_nm) / (2 * d_spacing_nm))
    return np.degrees(theta_rad) * 2.0
