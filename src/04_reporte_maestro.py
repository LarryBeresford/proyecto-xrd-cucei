import os
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_FIGURAS = os.path.join(BASE_DIR, 'reports', 'figures')
DIR_REPORTES = os.path.join(BASE_DIR, 'reports')
RUTA_CSV = os.path.join(BASE_DIR, 'data', 'processed', 'tabla_unificada.csv')

# --- 2. COLORES UDEG / CUCEI ---
C_AZUL_RGB = (0, 45, 98)
C_DORADO_RGB = (240, 168, 0)

# --- 3. CLASE DEL REPORTE MAESTRO ---
class ReporteMaestro(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*C_AZUL_RGB)
        self.rect(0, 0, 210, 25, 'F')
        self.set_y(10)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, 'REPORTE EJECUTIVO - DEGRADACIÓN Y CINÉTICA', 0, 1, 'C')
    
    def portada(self):
        self.add_page()
        self.set_fill_color(*C_AZUL_RGB)
        self.rect(0, 0, 210, 35, 'F')
        self.set_fill_color(*C_DORADO_RGB)
        self.rect(0, 35, 210, 4, 'F')
        
        self.set_fill_color(*C_AZUL_RGB)
        self.rect(0, 277, 210, 20, 'F')
        self.set_fill_color(*C_DORADO_RGB)
        self.rect(0, 273, 210, 4, 'F')

        self.set_y(60)
        self.set_font('Helvetica', 'B', 22)
        self.set_text_color(*C_AZUL_RGB)
        self.cell(0, 10, 'UNIVERSIDAD DE GUADALAJARA', 0, 1, 'C')
        self.set_font('Helvetica', 'B', 18)
        self.cell(0, 10, 'CUCEI', 0, 1, 'C')
        
        self.ln(25)
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(*C_DORADO_RGB)
        self.multi_cell(0, 10, 'Estudio Computacional de Liberación de Fármacos\n(GSH y NAC) en Matrices de HDL', 0, 'C')
        
        self.ln(30)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(*C_AZUL_RGB)
        self.cell(0, 8, 'Presenta: Larry Eduardo Beresford Díaz', 0, 1, 'C')
        
        self.ln(15)
        self.set_font('Helvetica', '', 12)
        self.cell(0, 6, 'Director: Dr. Gregorio Guadalupe Carbajal Arizaga', 0, 1, 'C')
        self.cell(0, 6, 'Asesor: M. en C. José Antonio Rivera Mayorga', 0, 1, 'C')

    def seccion_titulo(self, titulo):
        self.ln(5)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(*C_AZUL_RGB)
        self.cell(0, 10, titulo, 0, 1, 'L')
        self.set_draw_color(*C_DORADO_RGB)
        self.set_line_width(0.5)
        self.line(self.get_x(), self.get_y(), 200, self.get_y())
        self.ln(4)

    def parrafo(self, texto):
        self.set_font('Helvetica', '', 11)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, texto)
        self.ln(3)

# --- 4. CONSTRUCCIÓN DEL DOCUMENTO ---
def generar_documento():
    pdf = ReporteMaestro()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.portada()
    
    # --- PÁGINA 2: INTRO Y VISUAL ---
    pdf.add_page()
    pdf.seccion_titulo('1. El Vehículo y el Pasajero (Contexto)')
    pdf.parrafo("Imaginemos que el material Hidróxido Doble Laminar (HDL) es un 'vehículo' blindado de transporte. Su misión es llevar 'pasajeros' (las moléculas de fármaco GSH y NAC) de forma segura hacia el interior del cuerpo.")
    pdf.parrafo("La gran pregunta científica de este proyecto es: ¿Cómo bajan los pasajeros del vehículo? ¿Simplemente abren la puerta y salen, o el vehículo tiene que desmoronarse por completo para dejarlos libres? Para averiguarlo, cruzamos datos de la estructura del material (XRD) con la velocidad a la que sale el fármaco (Cinética).")
    
    pdf.seccion_titulo('2. La Evidencia Visual (Diagnóstico Inicial)')
    ruta_xrd = os.path.join(DIR_FIGURAS, 'xrd_diag.png')
    if os.path.exists(ruta_xrd):
        pdf.image(ruta_xrd, x=15, w=180)
    pdf.parrafo("Si observamos el vehículo a través de un difractómetro (XRD) al inicio del experimento (línea azul), vemos picos altos y firmes: la estructura está intacta. Tras 96 horas sumergido (línea amarilla), los picos se aplastan y ensanchan. Visualmente, el vehículo se está desmoronando.")

    # --- PÁGINA 3: MATEMÁTICA ---
    pdf.add_page()
    pdf.seccion_titulo('3. La Prueba Matemática (Cuantificación)')
    ruta_mvp = os.path.join(DIR_FIGURAS, 'MVP_Cuantificacion.png')
    if os.path.exists(ruta_mvp):
        pdf.image(ruta_mvp, x=15, w=180)
    pdf.parrafo("En ciencia, no basta con decir que 'se ve aplastado'. Al programar un algoritmo de integración matemática (Regla de Simpson) sobre el pico principal del material, logramos calcular el Área Bajo la Curva exacta.")
    pdf.parrafo("El resultado es irrefutable: la matriz inorgánica perdió exactamente un 5.9% de su estructura cristalina en ese plano durante las primeras 96 horas. Hemos transformado una observación visual en un Índice de Degradación medible.")

    # --- PÁGINA 4: INTERPOLACIÓN ---
    pdf.add_page()
    pdf.seccion_titulo('4. El Reloj Unificado (Alineación Temporal)')
    pdf.parrafo("Teníamos un reto: la estructura (XRD) se midió en cortes de horas (0, 24, 48...), pero la liberación del fármaco (Cinética) se midió en minutos a intervalos irregulares. No podíamos compararlos directamente.")
    pdf.parrafo("Para resolverlo, desarrollamos un motor de interpolación matemática que 'aprendió' la curva de liberación y predijo exactamente cuánto fármaco había salido en la marca exacta de las 24, 48, 72 y 96 horas. El resultado es esta tabla unificada:")
    
    if os.path.exists(RUTA_CSV):
        df_csv = pd.read_csv(RUTA_CSV)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(40, 8, 'Tiempo (Horas)', border=1, fill=True, align='C')
        pdf.cell(40, 8, 'Tiempo (Minutos)', border=1, fill=True, align='C')
        pdf.cell(50, 8, '% GSH Liberado', border=1, fill=True, align='C')
        pdf.cell(50, 8, '% NAC Liberado', border=1, fill=True, align='C')
        pdf.ln()
        
        pdf.set_font('Helvetica', '', 10)
        for _, row in df_csv.iterrows():
            pdf.cell(40, 8, str(int(row['Tiempo_Horas'])), border=1, align='C')
            pdf.cell(40, 8, str(int(row['Tiempo_Minutos'])), border=1, align='C')
            pdf.cell(50, 8, f"{row['Liberacion_GSH_Porcentaje']}%", border=1, align='C')
            pdf.cell(50, 8, f"{row['Liberacion_NAC_Porcentaje']}%", border=1, align='C')
            pdf.ln()
    
    pdf.ln(5)
    pdf.seccion_titulo('Conclusión Ejecutiva')
    pdf.parrafo("Tenemos ahora todas las piezas sobre la mesa. Sabemos exactamente cuánto se destruyó el material (5.9%) y, gracias a la interpolación, sabemos exactamente cuánto fármaco salió en ese mismo periodo de 96 horas. El siguiente paso del proyecto será cruzar estas dos variables para encontrar el nivel de correlación estadística entre la destrucción del vehículo y la liberación del pasajero.")

    ruta_salida = os.path.join(DIR_REPORTES, 'Reporte_04_Maestro.pdf')
    pdf.output(ruta_salida)
    print(f"\n[ÉXITO] REPORTE MAESTRO GENERADO. Revisa: {ruta_salida}")

if __name__ == "__main__":
    generar_documento()