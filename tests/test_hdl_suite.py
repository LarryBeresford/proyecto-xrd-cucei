"""
Pruebas de validación numérica del núcleo hdl_suite.

Objetivo (para el entregable de titulación, modalidad Diseño de Sistema
de Computación): demostrar con casos de solución analítica conocida que
los algoritmos numéricos (Simpson, Bragg, Min-Max, Pearson) son
correctos, y no solo que "el programa corre".

Ejecutar con:  python -m pytest tests/ -v
"""
import os
import sys
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hdl_suite import bragg, crystallinity, preprocessing, kinetics, correlation
import pandas as pd


# ---------------------------------------------------------------------
# Normalización Min-Max
# ---------------------------------------------------------------------
def test_normalizar_min_max_rango_0_1():
    y = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
    y_norm = preprocessing.normalizar_min_max(y)
    assert np.isclose(y_norm.min(), 0.0)
    assert np.isclose(y_norm.max(), 1.0)
    assert np.isclose(y_norm[2], 0.5)  # punto medio -> 0.5


def test_normalizar_min_max_constante_no_falla():
    y = np.array([5.0, 5.0, 5.0])
    y_norm = preprocessing.normalizar_min_max(y)
    np.testing.assert_array_equal(y_norm, y)


# ---------------------------------------------------------------------
# Ley de Bragg (round-trip: d -> theta -> d debe recuperar el valor)
# ---------------------------------------------------------------------
def test_bragg_round_trip():
    d_original = 7.9  # angstroms, típico plano basal de HDL
    angulo = bragg.angulo_desde_d(d_original)
    d_recuperado = bragg.calcular_distancia_bragg(angulo)
    assert np.isclose(d_original, d_recuperado, atol=1e-6)


def test_bragg_valor_conocido():
    # Para Cu-K-alpha (1.5406 A) y 2theta = 10 grados, d debe ser ~8.83 A
    # (calculado independientemente: d = 1.5406 / (2*sin(5 deg)))
    d = bragg.calcular_distancia_bragg(10.0)
    esperado = 1.5406 / (2 * np.sin(np.radians(5.0)))
    assert np.isclose(d, esperado, rtol=1e-9)


# ---------------------------------------------------------------------
# Integración de Simpson (área bajo la curva)
# ---------------------------------------------------------------------
def test_simpson_area_parabola_conocida():
    # Integral de x^2 entre 0 y 2 = 8/3 (solución analítica exacta)
    x = np.linspace(0, 2, 101)
    y = x ** 2
    area = crystallinity.calcular_area_simpson(x, y)
    assert np.isclose(area, 8.0 / 3.0, atol=1e-3)


def test_simpson_area_rectangulo():
    # Integral de una constante y=3 entre 0 y 4 = 12
    x = np.linspace(0, 4, 21)
    y = np.full_like(x, 3.0)
    area = crystallinity.calcular_area_simpson(x, y)
    assert np.isclose(area, 12.0, atol=1e-6)


def test_recortar_ventana_aisla_region_correcta():
    x = np.array([1, 5, 9, 12, 20])
    y = np.array([0, 1, 2, 3, 4])
    x_win, y_win = crystallinity.recortar_ventana(x, y, 8.0, 15.0)
    np.testing.assert_array_equal(x_win, np.array([9, 12]))
    np.testing.assert_array_equal(y_win, np.array([2, 3]))


# ---------------------------------------------------------------------
# FWHM sobre un pico gaussiano sintético con ancho conocido
# ---------------------------------------------------------------------
def test_fwhm_gaussiana_sintetica():
    # Gaussiana: FWHM_teorico = 2*sqrt(2*ln2)*sigma ~= 2.3548*sigma
    sigma = 1.0
    x = np.linspace(-10, 10, 2001)
    y = np.exp(-(x ** 2) / (2 * sigma ** 2))
    fwhm_medido = crystallinity.calcular_fwhm(x, y)
    fwhm_teorico = 2 * np.sqrt(2 * np.log(2)) * sigma
    assert np.isclose(fwhm_medido, fwhm_teorico, rtol=0.05)


def test_indice_perdida_cristalinidad():
    # Si el área se reduce a la mitad, la pérdida debe ser 50%
    perdida = crystallinity.indice_perdida_cristalinidad(area_referencia=10.0, area_actual=5.0)
    assert np.isclose(perdida, 50.0)


# ---------------------------------------------------------------------
# Interpolación cinética
# ---------------------------------------------------------------------
def test_interpolar_cinetica_recupera_puntos_reales():
    # Si los tiempos objetivo coinciden EXACTAMENTE con los tiempos
    # reales medidos, la interpolación debe devolver esos mismos valores.
    df_cin = pd.DataFrame({
        'Tiempo': [0, 1440, 2880],
        'Liberacion_GSH': [0.0, 50.0, 80.0],
        'Liberacion_NAC': [0.0, 40.0, 70.0],
    })
    resultado = kinetics.interpolar_cinetica(df_cin, horas_objetivo=[0, 24, 48])
    assert np.isclose(resultado.loc[1, 'Liberacion_GSH_Porcentaje'], 50.0)
    assert np.isclose(resultado.loc[2, 'Liberacion_NAC_Porcentaje'], 70.0)


# ---------------------------------------------------------------------
# Correlación de Pearson
# ---------------------------------------------------------------------
def test_pearson_correlacion_perfecta():
    x = np.array([0, 10, 20, 30, 40])
    y = np.array([0, 10, 20, 30, 40])
    resultado = correlation.calcular_pearson(x, y)
    assert np.isclose(resultado['r'], 1.0, atol=1e-9)
    assert resultado['n'] == 5
    assert resultado['n_bajo'] is True  # n=5 < 8


def test_pearson_longitudes_distintas_lanza_error():
    with pytest.raises(ValueError):
        correlation.calcular_pearson([1, 2, 3], [1, 2])
