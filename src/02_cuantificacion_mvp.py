"""
Entregable 2 (MVP): Cuantificación del desgaste estructural del HDL.

Reescrito para usar el núcleo compartido `hdl_suite` (antes este script
reimplementaba su propia limpieza de datos, Ley de Bragg y Simpson,
duplicando lógica con app.py). Ahora es un consumidor delgado del mismo
pipeline validado por tests/test_hdl_suite.py.
"""
import os
import sys
import warnings

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hdl_suite import config, pipeline  # noqa: E402

warnings.filterwarnings('ignore')

if __name__ == "__main__":
    resultado = pipeline.ejecutar_pipeline(
        limite_inf=config.LIMITE_INF_DEFAULT,
        limite_sup=config.LIMITE_SUP_DEFAULT,
        normalizar=False,  # se conserva el comportamiento histórico de este MVP (áreas absolutas)
        tiempos_h=[0, 96],  # el MVP original solo comparaba 0h vs 96h
    )

    x_0h, y_0h = resultado.series_xrd[0]
    x_96h, y_96h = resultado.series_xrd[96]
    area_0h, area_96h = resultado.areas[0], resultado.areas[1]
    perdida_porcentaje = resultado.perdida_cristalinidad[1]

    plt.figure(figsize=(9, 5))
    plt.fill_between(x_0h, y_0h, color=config.C_AZUL, alpha=0.3, label=f'Área Intacta (0h): {area_0h:.2f} U.A.')
    plt.fill_between(x_96h, y_96h, color=config.C_DORADO, alpha=0.6, label=f'Área Degradada (96h): {area_96h:.2f} U.A.')
    plt.plot(x_0h, y_0h, color=config.C_AZUL, linewidth=2)
    plt.plot(x_96h, y_96h, color=config.C_DORADO, linewidth=2)

    plt.title('MVP: Cuantificación del Desgaste Estructural (HDL)', fontsize=14, fontweight='bold')
    plt.xlabel('Ángulo 2θ', fontsize=12)
    plt.ylabel('Intensidad de Difracción', fontsize=12)

    texto_kpi = f"PÉRDIDA DE CRISTALINIDAD:\n{perdida_porcentaje:.1f}%"
    plt.text(13, max(y_0h) * 0.8, texto_kpi, fontsize=12, fontweight='bold',
              bbox=dict(facecolor='#f8d7da', edgecolor='#dc3545', boxstyle='round,pad=0.5'))

    plt.legend(loc='upper left')
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.tight_layout()

    ruta_salida = os.path.join(config.DIR_FIGURAS, 'MVP_Cuantificacion.png')
    plt.savefig(ruta_salida, dpi=300)
    print(f"¡MVP generado con éxito! Pérdida de cristalinidad (0h->96h): {perdida_porcentaje:.2f}%")
    print(f"Revisa la imagen en: {ruta_salida}")
