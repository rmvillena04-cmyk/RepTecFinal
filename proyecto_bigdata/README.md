# ⚽ Análisis de Rendimiento en el Fútbol Europeo
### Pipeline ETL · EDA · Cubo Dimensional con PySpark
**Asignatura:** Introducción a los Sistemas Big Data — UFV 2025-2026  
**Integrantes:** Pablo Peredo · Rodrigo Urrutia · Ricardo Sada · Nicolás Quetg

---

## 🎯 Objetivo

Construir un pipeline ETL completamente automatizado que integre tres fuentes heterogéneas de datos de fútbol, las transforme en un modelo dimensional almacenado en SQLite, y responda preguntas de negocio mediante PySpark en Google Colab.

**Pregunta central:** ¿Se puede predecir el éxito deportivo de un equipo a partir de estadísticas individuales, métricas colectivas y datos de videojuego?

---

## 📁 Estructura del repositorio

```
proyecto-bigdata-laliga/
├── data/
│   ├── raw/          ← Fuentes originales (F1, F2, F3 crudos)
│   ├── processed/    ← CSVs intermedios tras transformación
│   └── final/        ← Tablas del modelo estrella (para PySpark)
│       ├── dim_tiempo.csv
│       ├── dim_equipo.csv
│       ├── dim_temporada.csv
│       ├── dim_jugador.csv
│       └── fact_rendimiento.csv
├── src/
│   ├── extract.py    ← Fase EXTRACT (descarga/generación datos)
│   ├── transform.py  ← Fases T01–T10 (limpieza completa)
│   ├── load.py       ← Modelo estrella + carga SQLite
│   ├── eda.py        ← 8 gráficas obligatorias del EDA
│   └── pipeline.py   ← Runner principal end-to-end
├── notebooks/
│   ├── 01_eda_inicial.ipynb        ← EDA inicial (Cubo OLAP)
│   ├── 02_etl_pipeline.ipynb       ← Análisis xG ganadores/perdedores
│   ├── 03_pyspark_cubo_colab.ipynb ← ⭐ Cuaderno PySpark (Colab)
│   └── 04_fc24_visualizaciones.ipynb ← Visualizaciones EA FC24
├── outputs/
│   └── eda/          ← 8 gráficas EDA (PNG)
├── logs/
│   ├── pipeline.log
│   └── pipeline_tracking.json
├── informe/          ← Documento PDF/Word entregable
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🗃️ Fuentes de Datos

| ID | Fuente | Formato | Registros | Descripción |
|----|--------|---------|-----------|-------------|
| F1 | Football-Data.co.uk | CSV | 1.900 | Partidos LaLiga 2020/21–2024/25 (resultados, tiros, tarjetas, cuotas) |
| F2 | Understat | CSV | 100 | xG, xGA, xPTS por equipo y temporada |
| F3 | EA Sports FC 24 (Kaggle) | CSV | 482 | Atributos individuales de jugadores LaLiga |

---

## 🔄 Pipeline ETL

```
F1 CSV  ──┐
F2 CSV  ──┼──► EXTRACT ──► TRANSFORM (T01–T10) ──► LOAD ──► data/final/
F3 CSV  ──┘                                          │
                                                      ├── SQLite DW
                                                      └── GitHub CSVs → PySpark
```

### Transformaciones aplicadas (T01–T10)

| # | Transformación | Descripción |
|---|---------------|-------------|
| T01 | Eliminación de duplicados | `drop_duplicates()` por clave primaria |
| T02 | Tratamiento de nulos | Imputación por mediana/moda por columna |
| T03 | Eliminación de blancos | `strip()` + reemplazo por NaN |
| T04 | Corrección de tipos | Cast a int/float/datetime según semántica |
| T05 | Normalización fechas | ISO-8601 con timezone UTC |
| T06 | Normalización texto | Minúsculas + eliminación de acentos |
| T07 | Corrección de rangos | Overall 1–99, minutos ≤ 3420, valores ≥ 0 |
| T08 | Outliers IQR | Acotado por IQR en variables numéricas |
| T09 | Seudonimización PII | Hash SHA-256 sobre nombres reales |
| T10 | Validación referencial | Detección de registros huérfanos |

---

## ⭐ Modelo en Estrella

```
         DIM_TIEMPO
              │
DIM_EQUIPO ──┤── FACT_RENDIMIENTO ──┤── DIM_EQUIPO (rival)
              │
         DIM_TEMPORADA
              │
         DIM_JUGADOR (lado)
```

**Granularidad FACT:** Un registro por equipo × partido × perspectiva (local/visitante)  
**Medidas:** goles_favor, goles_contra, tiros, tiros_puerta, corners, faltas, amarillas, rojas, xg_partido, puntos

---

## 🚀 Ejecución rápida

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar pipeline completo (extrae datos, transforma, carga, genera gráficas)
cd src
python pipeline.py
```

El pipeline genera en ~10 segundos:
- `data/raw/` — 3 ficheros fuente
- `data/processed/` — 3 ficheros limpios
- `data/final/` — 5 CSVs del modelo estrella
- `outputs/eda/` — 8 gráficas PNG
- `logs/pipeline_tracking.json` — Tracking completo

---

## 📊 Preguntas de Negocio (PySpark)

Abre `notebooks/03_pyspark_cubo_colab.ipynb` en Google Colab:

| Q | Pregunta | Dimensiones usadas |
|---|----------|-------------------|
| Q1 | ¿Evolución mensual de goles por temporada? | DIM_TIEMPO + DIM_TEMPORADA |
| Q2 | ¿Ranking de equipos por puntos acumulados? | DIM_EQUIPO + DIM_TEMPORADA |
| Q3 | ¿Rendimiento local vs visitante por equipo? | DIM_EQUIPO |
| Q4 | ¿Correlación entre xG y puntos? | DIM_EQUIPO + DIM_TEMPORADA |
| Q5 | ¿Qué atributos FIFA predicen mejor el rendimiento? | DIM_JUGADOR |

---

## 🔗 Google Colab

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/TU_USUARIO/proyecto-bigdata-laliga/blob/main/notebooks/03_pyspark_cubo_colab.ipynb)

---

## 🤖 Uso de Inteligencia Artificial

| Herramienta | Tarea | Grado modificación |
|-------------|-------|-------------------|
| Claude Sonnet 4.6 (Anthropic) | Generación del esqueleto de módulos ETL | Alto — código revisado y adaptado al dominio |
| Claude Sonnet 4.6 (Anthropic) | Diseño del modelo estrella y DDL SQLite | Medio — estructura validada contra requisitos |

> El código generado por IA fue ejecutado, depurado y validado por todos los integrantes del grupo.

---

## 📚 Bibliografía

- Kimball, R. & Ross, M. (2013). *The Data Warehouse Toolkit*, 3rd ed. Wiley.
- pandas Documentation — https://pandas.pydata.org/docs/
- PySpark Documentation — https://spark.apache.org/docs/latest/api/python/
- SQLAlchemy Documentation — https://docs.sqlalchemy.org/
- Football-Data.co.uk — https://www.football-data.co.uk/
- Understat — https://understat.com/
- EA Sports FC 24 Dataset — https://www.kaggle.com/datasets/stefanoleone992/ea-sports-fc-24-complete-player-dataset
