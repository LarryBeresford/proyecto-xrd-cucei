"""
HDL Analytical Suite - Núcleo de cálculo compartido
=====================================================

Paquete central de funciones físico-matemáticas usadas tanto por la
aplicación web (app.py) como por los scripts de línea de comandos
(01_diagnostico.py .. 04_reporte_maestro.py). Consolidar la lógica aquí
evita que cada script reimplemente (con variaciones) la limpieza de datos,
la Ley de Bragg, la integración de Simpson, el FWHM, la interpolación
cinética y la correlación de Pearson.

Racional científico general:
Este paquete implementa el pipeline de 4 etapas descrito en el protocolo
de titulación: (1) preprocesamiento y normalización, (2) análisis
cristalográfico estructural (Bragg + FWHM + Simpson), (3) sincronización
temporal cinética-cristalografía (interpolación lineal), y (4) inferencia
estadística (Pearson) para evaluar causalidad entre degradación
estructural y liberación de fármaco.
"""

from . import config, data_io, preprocessing, bragg, crystallinity, kinetics, correlation, ftir, pipeline

__all__ = [
    "config",
    "data_io",
    "preprocessing",
    "bragg",
    "crystallinity",
    "kinetics",
    "correlation",
    "ftir",
    "pipeline",
]
