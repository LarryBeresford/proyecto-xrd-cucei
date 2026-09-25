# HDL-SyncXRD

**Suite analítica para cuantificar la degradación estructural (XRD) y química (FTIR) de hidróxidos dobles laminares (HDL) y sincronizarla con la cinética de liberación de fármacos.**

Proyecto académico de la Licenciatura en Química, CUCEI — Universidad de Guadalajara.

## Propósito

La evaluación de la estabilidad de una matriz HDL suele depender de la inspección visual de espectros superpuestos. HDL-SyncXRD propone un flujo reproducible para convertir estas observaciones en métricas numéricas y compararlas con la liberación de moléculas como glutatión (GSH) y N-acetilcisteína (NAC).

Objetivo general del proyecto (planteamiento del asesor): desarrollar una plataforma que permita la correlación de cambios estructurales y/o químicos detectables por **XRD y FTIR** con los fenómenos de liberación y degradación en HDL intercalados.

La herramienta recibe datos experimentales de XRD, FTIR y cinética, los limpia, alinea sus escalas de tiempo y genera visualizaciones y reportes técnicos. Su objetivo es apoyar el análisis cuantitativo, trazable y auditable de la evolución estructural/química de matrices inorgánicas durante ensayos de liberación.

> **Alcance científico:** las correlaciones calculadas describen asociación estadística entre variables sincronizadas. Por sí solas no demuestran causalidad; esta requiere controles, réplicas independientes y un diseño experimental apropiado.

## Capacidades actuales

- Lectura de archivos Excel con las hojas `XRD diferentes tiempos` y `Cinetica`.
- Limpieza de valores no numéricos y selección interactiva de la región de interés en 2θ.
- Normalización Min-Max opcional de difractogramas.
- Integración numérica de picos mediante la regla compuesta de Simpson.
- Cálculo del espaciado basal por la ley de Bragg usando radiación Cu Kα (`λ = 1.5406 Å`).
- Cálculo de FWHM como métrica de ensanchamiento/amorfización, integrado como segundo índice de degradación (independiente del área de Simpson) en la app y en el reporte PDF.
- Interpolación lineal de cinética de liberación a los tiempos cristalográficos de 0, 24, 48, 72 y 96 h.
- Correlación de Pearson calculada con la degradación **real** medida en cada uno de los 5 tiempos de XRD disponibles (no una trayectoria lineal inferida), tanto vía área de Simpson como vía FWHM.
- Visualización interactiva de XRD, evolución temporal de los índices de degradación, cinética y relaciones estadísticas.
- Generación de reportes PDF institucionales y exportación de la tabla temporal sincronizada.
- Núcleo de cálculo (`src/hdl_suite/`) desacoplado de la interfaz, con pruebas unitarias (`tests/`) que validan cada algoritmo contra casos de solución analítica conocida.
- **Análisis FTIR** (`hdl_suite/ftir.py`): lectura de espectros de infrarrojo (número de onda vs. absorbancia) para HDL/GSH/NAC en los mismos 5 tiempos reales, con área de Simpson, FWHM y posición de banda (cm⁻¹) como índices de cambio químico, correlacionados vía Pearson (r y R²) con la cinética de liberación. La asignación química de la banda analizada debe confirmarse con el asesor/director.
- R² (bondad de ajuste) reportado junto con Pearson r y su p-value en ambas técnicas.

> **Nota metodológica:** la normalización Min-Max se aplica sobre el espectro completo *antes* de recortar la ventana de interés, no después — normalizar una ventana ya recortada reescala cada tiempo a su propio máximo local y puede enmascarar o exagerar artificialmente la pérdida real de intensidad entre tiempos. El índice FWHM es matemáticamente invariante a esta elección; el índice de área no lo es y debe interpretarse con esa salvedad.

## Flujo de análisis

```text
Excel experimental
   ├── XRD: ángulo 2θ e intensidad por tiempo
   └── Cinética: tiempo (min) y porcentaje liberado
                 │
                 ▼
Limpieza, validación y selección del pico basal
                 │
                 ▼
Área (Simpson) · FWHM · posición de pico · espaciado basal d
                 │
                 ▼
Interpolación de liberación a 0, 24, 48, 72 y 96 h
                 │
                 ▼
Tablero Streamlit · tabla unificada · reporte PDF
```

## Estructura del repositorio

```text
data/
  raw/          # Archivo experimental original
  processed/    # Tablas derivadas y reproducibles
reports/
  figures/      # Figuras generadas por los scripts
  *.pdf         # Reportes técnicos exportados
src/
  hdl_suite/                   # Núcleo de cálculo compartido (sin duplicación entre scripts y app)
    config.py                  # Rutas, constantes físicas, paleta institucional
    data_io.py                 # Carga y limpieza del Excel de laboratorio
    preprocessing.py           # Normalización Min-Max
    bragg.py                   # Ley de Bragg (d-spacing)
    crystallinity.py           # Simpson (área) y FWHM (amorfización)
    kinetics.py                # Interpolación lineal cinética -> malla XRD
    correlation.py             # Correlación de Pearson
    pipeline.py                # Orquestación de las 4 etapas del análisis
  01_diagnostico.py            # Exploración inicial y reporte diagnóstico
  02_cuantificacion_mvp.py     # Área de pico por regla de Simpson (usa hdl_suite)
  03_interpolacion_cinetica.py # Sincronización temporal de la cinética (usa hdl_suite)
  04_reporte_maestro.py        # Reporte ejecutivo consolidado (usa hdl_suite)
  app.py                       # Aplicación web Streamlit (usa hdl_suite)
tests/
  test_hdl_suite.py            # Pruebas unitarias contra casos de solución analítica conocida
requirements.txt
```

## Instalación

Requiere Python 3.10 o superior.

```powershell
git clone https://github.com/LarryBeresford/proyecto-xrd-cucei.git
cd proyecto-xrd-cucei
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Para permitir la exportación de figuras Plotly dentro del PDF, Kaleido debe estar disponible; se instala mediante `requirements.txt`.

## Ejecutar la aplicación web

```powershell
streamlit run src/app.py
```

En el navegador, cargue un archivo `.xlsx` con la plantilla esperada. Ajuste los límites de 2θ para incluir únicamente el pico basal que desea analizar y descargue el reporte al finalizar.

## Ejecutar los entregables por separado

```powershell
python src/01_diagnostico.py
python src/02_cuantificacion_mvp.py
python src/03_interpolacion_cinetica.py
python src/04_reporte_maestro.py
```

Los scripts usan por defecto `data/raw/datos_cucei.xlsx` y escriben sus resultados en `data/processed/` y `reports/`.

## Ejecutar las pruebas

```powershell
python -m pytest tests/ -v
```

## Fundamento analítico

### Espaciado basal — ley de Bragg

Para un pico ubicado en `2θ`, el ángulo de Bragg es `θ = (2θ)/2` y el espaciado basal se calcula como:

```text
d = λ / (2 sin θ)
```

### Cristalinidad relativa — integración de Simpson

El área bajo un pico, tras una estrategia de preprocesamiento consistente, se utiliza como descriptor de cristalinidad relativa. La comparación entre tiempos debe realizarse con la misma región de integración, condiciones instrumentales y tratamiento de línea base.

### Sincronización temporal

La cinética medida en minutos se interpola en los tiempos de muestreo XRD. Esto permite construir una tabla conjunta para análisis exploratorio de asociación entre liberación y métricas estructurales.

## Recomendaciones para resultados publicables

- ✅ Implementado: las métricas XRD (área, FWHM, d-spacing) se calculan con datos experimentales reales en **cada** uno de los 5 tiempos disponibles (0, 24, 48, 72 y 96 h); ya no se infiere una trayectoria estructural lineal entre 0h y 96h.
- Aplicar y documentar corrección de línea base y detección robusta de picos antes de integrar o calcular FWHM.
- Conservar réplicas experimentales y reportar incertidumbre, intervalos de confianza y tamaño de muestra.
- Usar Pearson solo cuando sus supuestos sean defendibles; contrastarlo con Spearman cuando corresponda.
- Interpretar correlación como asociación, no como prueba aislada de mecanismo causal.

## Datos y ética científica

Los resultados generados son herramientas de apoyo a la interpretación experimental. La validación final de la identidad de fases, cambios estructurales y mecanismo de liberación corresponde al criterio del investigador y a la evidencia experimental complementaria.

## Autoría

**Larry Eduardo Beresford Díaz**  
Licenciatura en Química, CUCEI — Universidad de Guadalajara

Dirección: Dr. Gregorio Guadalupe Carbajal Arizaga  
Asesoría: M. en C. José Antonio Rivera Mayorga
