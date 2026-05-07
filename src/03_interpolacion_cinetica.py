import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
import os

# --- 1. CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_EXCEL = os.path.join(BASE_DIR, 'data', 'raw', 'datos_cucei.xlsx')
DIR_PROCESADOS = os.path.join(BASE_DIR, 'data', 'processed')

os.makedirs(DIR_PROCESADOS, exist_ok=True)

# --- 2. CARGA Y LIMPIEZA DE LA CINÉTICA ---
def cargar_cinetica():
    df = pd.read_excel(ARCHIVO_EXCEL, sheet_name='Cinetica', skiprows=1)
    df = df.rename(columns={'Unnamed: 0': 'Tiempo', 'GSH': 'Liberacion_GSH', 'NAC': 'Liberacion_NAC'})
    
    for col in ['Tiempo', 'Liberacion_GSH', 'Liberacion_NAC']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # Eliminar valores nulos para poder hacer la matemática continua
    df = df.dropna(subset=['Tiempo', 'Liberacion_GSH', 'Liberacion_NAC'])
    return df

# --- 3. MOTOR DE INTERPOLACIÓN ---
def interpolar_datos(df):
    # Tiempos objetivo del difractómetro (en horas)
    horas_xrd = np.array([0, 24, 48, 72, 96])
    
    # Conversión a minutos para empatar con la cinética
    minutos_objetivo = horas_xrd * 60 
    
    tiempos_reales = df['Tiempo'].values
    gsh_real = df['Liberacion_GSH'].values
    nac_real = df['Liberacion_NAC'].values
    
    # Crear funciones matemáticas continuas (interp1d) basadas en los puntos reales
    # kind='linear' conecta los puntos, fill_value='extrapolate' permite predecir en los bordes
    funcion_gsh = interp1d(tiempos_reales, gsh_real, kind='linear', fill_value='extrapolate')
    funcion_nac = interp1d(tiempos_reales, nac_real, kind='linear', fill_value='extrapolate')
    
    # Calcular los valores exactos en los minutos que necesitamos
    gsh_interpolado = funcion_gsh(minutos_objetivo)
    nac_interpolado = funcion_nac(minutos_objetivo)
    
    # Ensamblar el DataFrame unificado
    df_unificado = pd.DataFrame({
        'Tiempo_Horas': horas_xrd,
        'Tiempo_Minutos': minutos_objetivo,
        'Liberacion_GSH_Porcentaje': np.round(gsh_interpolado, 2),
        'Liberacion_NAC_Porcentaje': np.round(nac_interpolado, 2)
    })
    
    # Forzar que el tiempo 0 sea 0% de liberación por lógica química
    df_unificado.loc[0, 'Liberacion_GSH_Porcentaje'] = 0.0
    df_unificado.loc[0, 'Liberacion_NAC_Porcentaje'] = 0.0
    
    return df_unificado

# --- EJECUCIÓN ---
if __name__ == "__main__":
    print("Iniciando motor de interpolación matemática...")
    df_cinetica = cargar_cinetica()
    
    if not df_cinetica.empty:
        df_final = interpolar_datos(df_cinetica)
        
        # Guardar la tabla limpia para el modelo final
        ruta_csv = os.path.join(DIR_PROCESADOS, 'tabla_unificada.csv')
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