import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import os
import warnings
from datetime import datetime

# Ignorar advertencias de formato de excel para mantener la consola limpia
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# --- 1. CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO_EXCEL = os.path.join(BASE_DIR, 'data', 'raw', 'datos_cucei.xlsx')
DIR_FIGURAS = os.path.join(BASE_DIR, 'reports', 'figures')
DIR_REPORTES = os.path.join(BASE_DIR, 'reports')

# Crear carpetas por si acaso
os.makedirs(DIR_FIGURAS, exist_ok=True)
os.makedirs(DIR_REPORTES, exist_ok=True)

# --- 2. COLORES UDEG / CUCEI ---
C_AZUL = '#002D62'
C_AZUL_RGB = (0, 45, 98)
C_DORADO = '#F0A800'
C_DORADO_RGB = (240, 168, 0)

# --- 3. CARGA DE DATOS ---
def cargar_datos():
    try:
        df_xrd = pd.read_excel(ARCHIVO_EXCEL, sheet_name='XRD diferentes tiempos')
        df_cin = pd.read_excel(ARCHIVO_EXCEL, sheet_name='Cinetica', skiprows=1)
        
        # LIMPIEZA XRD: Convierte errores (como '--') en nulos para que no falle matplotlib
        for col in df_xrd.columns:
            df_xrd[col] = pd.to_numeric(df_xrd[col], errors='coerce')
        
        # LIMPIEZA CINÉTICA
        df_cin = df_cin.rename(columns={
            'Unnamed: 0': 'Tiempo', 
            'GSH': 'Liberacion_GSH', 
            'NAC': 'Liberacion_NAC'
        })
        for col in ['Tiempo', 'Liberacion_GSH', 'Liberacion_NAC']:
            if col in df_cin.columns:
                df_cin[col] = pd.to_numeric(df_cin[col], errors='coerce')
                
        # Filtra filas inválidas
        df_cin = df_cin[df_cin['Tiempo'].notnull()]
        return df_xrd, df_cin
    except Exception as e:
        print(f"Error al cargar el Excel. Verifica que el archivo exista en data/raw/datos_cucei.xlsx: {e}")
        return None, None

# --- 4. GENERACIÓN DE GRÁFICAS ---
def generar_graficas(df_xrd, df_cin):
    ruta_xrd = os.path.join(DIR_FIGURAS, 'xrd_diag.png')
    ruta_cin = os.path.join(DIR_FIGURAS, 'cin_diag.png')

    # Gráfica XRD
    plt.figure(figsize=(10, 5))
    plt.plot(df_xrd['Angulo 2tetha'], df_xrd['HDL 0H'], label='HDL 0 Horas (Base)', color=C_AZUL, linewidth=1.5)
    plt.plot(df_xrd['Angulo 2tetha.1'], df_xrd['HDL 96H'], label='HDL 96 Horas (Degradado)', color=C_DORADO, linewidth=1.5, alpha=0.8)
    plt.title('Diagnóstico XRD: HDL Base (0h vs 96h)', fontsize=14, fontweight='bold', color=C_AZUL)
    plt.xlabel('Ángulo 2θ', fontsize=12)
    plt.ylabel('Intensidad (U.A.)', fontsize=12)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.xlim(0, 30) 
    plt.tight_layout()
    plt.savefig(ruta_xrd, dpi=300)
    plt.close()

    # Gráfica Cinética
    plt.figure(figsize=(10, 5))
    plt.plot(df_cin['Tiempo'], df_cin['Liberacion_GSH'], marker='o', label='GSH', color=C_AZUL, linewidth=2)
    plt.plot(df_cin['Tiempo'], df_cin['Liberacion_NAC'], marker='s', label='NAC', color=C_DORADO, linewidth=2)
    plt.title('Cinética de Liberación (% vs Tiempo)', fontsize=14, fontweight='bold', color=C_AZUL)
    plt.xlabel('Tiempo (minutos)', fontsize=12)
    plt.ylabel('% de Liberación', fontsize=12)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(ruta_cin, dpi=300)
    plt.close()
    
    return ruta_xrd, ruta_cin

# --- 5. GENERACIÓN DEL REPORTE PDF ---
class ReporteCUCEI(FPDF):
    def header(self):
        # Evitar que este encabezado aparezca en la portada (página 1)
        if self.page_no() == 1:
            return
            
        self.set_fill_color(*C_AZUL_RGB)
        self.rect(0, 0, 210, 25, 'F')
        self.set_y(10)
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, 'REPORTE DE DIAGNÓSTICO DE DATOS', 0, 1, 'C')
        self.set_font('Helvetica', '', 11)
        self.set_text_color(*C_DORADO_RGB)
        self.cell(0, 6, 'Proyecto de Titulación - Informe Técnico', 0, 1, 'C')
        self.ln(10)

    def portada(self):
        self.add_page()
        
        # Franjas Superiores (Azul y Dorada)
        self.set_fill_color(*C_AZUL_RGB)
        self.rect(0, 0, 210, 35, 'F')
        self.set_fill_color(*C_DORADO_RGB)
        self.rect(0, 35, 210, 4, 'F')
        
        # Franjas Inferiores (Azul y Dorada)
        self.set_fill_color(*C_AZUL_RGB)
        self.rect(0, 277, 210, 20, 'F')
        self.set_fill_color(*C_DORADO_RGB)
        self.rect(0, 273, 210, 4, 'F')

        # Institución
        self.set_y(60)
        self.set_font('Helvetica', 'B', 22)
        self.set_text_color(*C_AZUL_RGB)
        self.cell(0, 10, 'UNIVERSIDAD DE GUADALAJARA', 0, 1, 'C')
        
        self.set_font('Helvetica', 'B', 18)
        self.cell(0, 10, 'CUCEI', 0, 1, 'C')
        
        self.ln(5)
        self.set_font('Helvetica', '', 16)
        self.cell(0, 10, 'Licenciatura en Química', 0, 1, 'C')
        
        # Título del Proyecto
        self.ln(25)
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(*C_DORADO_RGB)
        self.multi_cell(0, 10, 'Diagnóstico y Análisis Computacional\nde Datos XRD y Cinética de Liberación', 0, 'C')
        
        # Autor
        self.ln(30)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(*C_AZUL_RGB)
        self.cell(0, 8, 'Presenta:', 0, 1, 'C')
        self.set_font('Helvetica', '', 14)
        self.cell(0, 8, 'Larry Eduardo Beresford Díaz', 0, 1, 'C')
        
        # Asesores
        self.ln(20)
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 6, 'Director del Proyecto:', 0, 1, 'C')
        self.set_font('Helvetica', '', 12)
        self.cell(0, 6, 'Dr. Gregorio Guadalupe Carbajal Arizaga', 0, 1, 'C')
        
        self.ln(10)
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 6, 'Asesor:', 0, 1, 'C')
        self.set_font('Helvetica', '', 12)
        self.cell(0, 6, 'M. en C. José Antonio Rivera Mayorga', 0, 1, 'C')
        
        # Lugar y Fecha
        self.set_y(245)
        self.set_font('Helvetica', 'I', 12)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, 'Zapopan, Jalisco, México', 0, 1, 'C')
        anio_actual = datetime.now().year
        self.cell(0, 6, str(anio_actual), 0, 1, 'C')

    def chapter_title(self, title):
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(*C_AZUL_RGB)
        self.cell(0, 10, title, 0, 1, 'L')
        self.set_draw_color(*C_DORADO_RGB)
        self.set_line_width(0.5)
        self.line(self.get_x(), self.get_y(), 200, self.get_y())
        self.ln(4)

    def chapter_body(self, text):
        self.set_font('Helvetica', '', 11)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 6, text)
        self.ln(5)

def ensamblar_pdf(ruta_xrd, ruta_cin):
    pdf = ReporteCUCEI()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- 1. LLAMAR A LA PORTADA PRIMERO ---
    pdf.portada()
    
    # --- 2. AGREGAR EL RESTO DEL DOCUMENTO ---
    pdf.add_page()
    
    pdf.chapter_title('1. Contexto y Objetivo del Proyecto')
    texto_intro = (
        "Este proyecto analiza un sistema de liberación de fármacos a nivel microscópico. Se utiliza un material "
        "llamado Hidróxido Doble Laminar (HDL), que funciona como un 'vehículo' en forma de capas (similar a un sándwich) "
        "para atrapar y transportar moléculas antioxidantes (GSH y NAC).\n\n"
        "El problema central de investigación es entender CÓMO el vehículo libera a su pasajero al entrar al cuerpo humano. "
        "¿El fármaco simplemente sale flotando, o el vehículo tiene que destruirse para poder liberarlo? "
        "El presente documento explora los datos iniciales crudos obtenidos en el laboratorio para validar si es factible "
        "demostrar mediante análisis de datos y programación que la estructura del HDL se está desmoronando (degradación) "
        "a medida que libera las moléculas."
    )
    pdf.chapter_body(texto_intro)
    
    pdf.chapter_title('2. Inspección de Señales de Difracción (XRD)')
    pdf.image(ruta_xrd, x=15, w=180)
    texto_xrd = (
        "¿Qué estamos viendo en esta gráfica?\n"
        "La Difracción de Rayos X (XRD) es una técnica analítica que permite visualizar el 'orden' interno y la solidez "
        "de un material. Cuando el material está perfectamente estructurado, los rayos rebotan de forma limpia y la gráfica "
        "muestra picos muy altos, delgados y precisos (como se observa en la línea azul que representa al material intacto a las 0 horas).\n\n"
        "Interpretación para el proyecto:\n"
        "Al observar la línea dorada (que representa al mismo material pero después de haber estado 96 horas sumergido en líquido), "
        "vemos claramente que los picos se 'aplastan', se ensanchan y la línea se vuelve mucho más ruidosa o inestable. Para cualquier "
        "lector ajeno al laboratorio, esta es la comprobación visual directa de que el material base o 'vehículo' está perdiendo "
        "su forma original y se está desmoronando estructuralmente."
    )
    pdf.chapter_body(texto_xrd)
    
    pdf.add_page()
    pdf.chapter_title('3. Análisis de las Curvas de Liberación (Cinética)')
    pdf.image(ruta_cin, x=15, w=180)
    texto_cin = (
        "¿Qué nos dice la cinética?\n"
        "Mientras que el XRD mide qué tan sólido es el material, las pruebas de cinética miden exactamente a qué velocidad "
        "y en qué cantidad va escapando el fármaco hacia el líquido circundante con el paso de los minutos.\n\n"
        "Interpretación para el proyecto:\n"
        "Ambas curvas muestran un comportamiento clásico. Al inicio, vemos una subida muy pronunciada y casi vertical "
        "(el fármaco sale rápidamente del vehículo). Sin embargo, después de ciertas horas, la línea deja de subir y se vuelve "
        "plana (alcanza un estado de equilibrio o 'plateau'). Esto nos indica que la liberación de la medicina no es infinita, "
        "sino que llega a un límite. La gran incógnita científica que resolveremos es: ¿Ese límite en la liberación coincide "
        "exactamente con el nivel de destrucción física del material que vimos en la gráfica anterior?"
    )
    pdf.chapter_body(texto_cin)
    
    pdf.chapter_title('Conclusión y Siguientes Pasos')
    texto_concl = (
        "El diagnóstico de la información es completamente exitoso. Las bases de datos proporcionadas demuestran fenómenos "
        "físicos muy claros y no contienen errores de lectura insalvables.\n\n"
        "Siguientes Pasos (Entregable 2):\n"
        "El verdadero valor de un proyecto de titulación en ciencia de datos es eliminar la subjetividad del ojo humano. "
        "Para la ciencia, ya no bastará con decir 'la gráfica se ve más aplastada'. En la siguiente fase, programaremos un "
        "algoritmo en Python capaz de calcular matemáticamente el 'Área Bajo la Curva' exacta de los picos de XRD para generar un "
        "'Índice Numérico de Degradación'. Finalmente, cruzaremos ese nuevo índice con las curvas de liberación para demostrar, "
        "con rigor estadístico, la correlación directa entre ambos fenómenos."
    )
    pdf.chapter_body(texto_concl)
    
    ruta_pdf = os.path.join(DIR_REPORTES, 'Reporte_01_Diagnostico.pdf')
    pdf.output(ruta_pdf)
    print(f"\n[ÉXITO] Reporte PDF generado con explicaciones detalladas en: {ruta_pdf}")

# --- EJECUCIÓN ---
if __name__ == "__main__":
    print("Iniciando procesamiento de Entregable 1...")
    df_xrd, df_cin = cargar_datos()
    
    if df_xrd is not None and not df_xrd.empty:
        print("Generando gráficas...")
        r_xrd, r_cin = generar_graficas(df_xrd, df_cin)
        print("Compilando reporte ejecutivo con portada...")
        ensamblar_pdf(r_xrd, r_cin)
    else:
        print("No se pudieron procesar los datos.")