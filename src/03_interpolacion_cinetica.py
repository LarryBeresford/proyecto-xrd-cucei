"""
Entregable 3: Motor de sincronización temporal (cinética -> malla XRD).

Reescrito para usar el núcleo compartido `hdl_suite.kinetics`, en vez de
reimplementar su propia interpolación lineal (antes duplicada respecto a
app.py).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hdl_suite import config, data_io, kinetics  # noqa: E402

if __name__ == "__main__":
    print("Iniciando motor de interpolación matemática...")
    df_cinetica = data_io.cargar_cinetica_cruda()

    if not df_cinetica.empty:
        df_final = kinetics.interpolar_cinetica(df_cinetica, horas_objetivo=config.TIEMPOS_XRD_HORAS)

        ruta_csv = os.path.join(config.DIR_PROCESSED, 'tabla_unificada.csv')
        df_final.to_csv(ruta_csv, index=False)

        print("\n¡Interpolación exitosa! Los datos se han alineado temporalmente.")
        print("-" * 65)
        print("TABLA MAESTRA UNIFICADA (Lista para cruce con XRD)")
        print("-" * 65)
        print(df_final.to_string(index=False))
        print("-" * 65)
        print(f"Archivo guardado en: {ruta_csv}")
    else:
        print("Error: No se encontraron datos válidos en la hoja de Cinética.")
