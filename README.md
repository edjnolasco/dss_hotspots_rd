# DSS_Hotspots_RD

![CI](https://github.com/edjnolasco/dss_hotspots_rd/actions/workflows/ci.yml/badge.svg)
![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen)
![Version](https://img.shields.io/badge/version-v1.2.0-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Framework](https://img.shields.io/badge/streamlit-1.56.0-red)
![ML](https://img.shields.io/badge/modeling-multi--model-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Status](https://img.shields.io/badge/status-stable-success)

Sistema de Soporte a la Decisión (DSS) para la identificación, priorización y visualización de zonas críticas de siniestralidad vial en la República Dominicana.

---

## 🔖 Versión actual

**v1.2.0**

Esta versión consolida una evolución importante del proyecto mediante:

- motor predictivo **multi-modelo**
- **benchmark** comparativo de algoritmos
- exportación automática de **tablas y figuras**
- modo **presentación ON/OFF**
- narrativa ejecutiva estructurada sin scroll interno

---

## 🎯 Objetivo

El sistema tiene como propósito apoyar la toma de decisiones en seguridad vial mediante:

- identificación de provincias con mayor criticidad relativa
- estimación de riesgo usando datos históricos
- priorización operativa mediante ranking **Top-K**
- generación de recomendaciones accionables
- interpretación ejecutiva de la salida del DSS

---

## 🚀 Valor diferencial

DSS_Hotspots_RD no se limita a mostrar indicadores o aplicar un único modelo de machine learning. El sistema integra:

- un enfoque **híbrido DSS**: datos + modelo + reglas + ranking
- comparación entre **múltiples algoritmos**
- una capa explícita de **reglas DSS**
- explicabilidad del modelo
- narrativa ejecutiva orientada a decisión
- exportación reproducible para informes académicos y técnicos

Este enfoque mejora la robustez, la interpretabilidad y la utilidad operativa del sistema.

---

## 🧠 Enfoque DSS

El flujo general del sistema es:

```text
Datos → Features → Modelo ML → Score → Reglas DSS → Ranking → Decisión
```

### Componentes principales

- **Data Layer**: datos históricos normalizados por provincia y año
- **Feature Engineering**: construcción de variables derivadas para predicción
- **Predictive Engine**: estimación del riesgo mediante modelos ML
- **Rule Engine**: categorización operativa con reglas DSS
- **Ranking Layer**: priorización territorial Top-K
- **Narrative Layer**: síntesis ejecutiva de resultados
- **Export Layer**: generación de artefactos para análisis y reporte

---

## 🤖 Motor predictivo multi-modelo

La versión `v1.2.0` incorpora selección dinámica del motor predictivo desde la interfaz. Los modelos soportados actualmente son:

- Random Forest
- Extra Trees
- Gradient Boosting
- HistGradientBoosting
- SVM (SVR con kernel RBF)

Esto permite comparar enfoques ensemble, boosting y basados en márgenes dentro de una misma tubería DSS.

---

## 📊 Benchmark de modelos

El sistema incluye un módulo de benchmarking que permite evaluar los modelos bajo una misma estrategia de validación.

### Métricas consideradas

- **MAE** (Mean Absolute Error)
- **RMSE** (Root Mean Squared Error)
- **R²** (Coefficient of Determination)

### Estrategia de validación

- partición temporal
- entrenamiento con años históricos
- evaluación sobre el período más reciente disponible
- comparación homogénea entre algoritmos

### Resultado

El benchmark puede visualizarse directamente en la app y exportarse automáticamente a:

- `CSV`
- `XLSX`
- `PNG`

---

## 🧾 Narrativa ejecutiva

La salida del DSS no se presenta únicamente como tabla o gráfico. El sistema genera una narrativa estructurada que resume:

- contexto del análisis
- resultado general
- provincias priorizadas
- desempeño del sistema
- interpretación
- lectura operativa

En **modo presentación**, la narrativa se simplifica para una lectura más ejecutiva:

- hallazgo principal
- provincias priorizadas
- lectura ejecutiva
- recomendación general

---

## 🖥️ Modo presentación

Se incorporó un toggle **Presentación ON/OFF** para alternar entre:

### Modo análisis
- benchmark visible
- bloque técnico del modelo
- narrativa completa
- secciones analíticas completas

### Modo presentación
- interfaz más limpia
- ocultación de ruido técnico
- narrativa ejecutiva simplificada
- navegación más enfocada a demostración

---

## 🧩 Arquitectura del proyecto

```text
DSS_Hotspots_RD/
│
├── VERSION
├── README.md
├── CHANGELOG.md
├── release_notes_v1.2.0.md
├── requirements.txt
├── requirements.lock.txt
│
├── app/
│   ├── app.py
│   └── ui/
│       ├── ui_about.py
│       ├── ui_help.py
│       ├── ui_model_selector.py
│       ├── ui_sections.py
│       └── ui_summary.py
│
├── src/
│   ├── benchmark_exports.py
│   ├── data_sources.py
│   ├── debug_tools.py
│   ├── exporter.py
│   ├── features.py
│   ├── glossary.py
│   ├── interactive_filters.py
│   ├── metrics.py
│   ├── model_benchmark.py
│   ├── model_catalog.py
│   ├── modeling.py
│   ├── narrative.py
│   ├── pipeline.py
│   ├── rules.py
│   ├── section_router.py
│   ├── state.py
│   ├── version.py
│   └── view_state.py
│
├── data/
├── reports/
│   ├── figures/
│   └── tables/
└── tests/
```

---

## 🧱 Arquitectura DSS (C4 – nivel contenedor)

```text
[Usuario]
   ↓
[Streamlit UI]
   ↓
[DSS Pipeline]
   ├── Feature Engineering
   ├── Multi-Model Engine
   │   ├── Random Forest
   │   ├── Extra Trees
   │   ├── Gradient Boosting
   │   ├── HistGradientBoosting
   │   └── SVM (SVR-RBF)
   ├── Scoring Layer
   ├── Rule Engine
   ├── Ranking Engine (Top-K)
   ├── Explainability
   └── Narrative Engine
   ↓
[Visualization + Export]
```

---

## 🔍 Explicabilidad

El sistema incorpora una estrategia escalonada de interpretabilidad:

1. **SHAP**, si aplica al modelo y al entorno
2. **Feature Importance**, para modelos compatibles
3. **Permutation Importance**, como mecanismo de respaldo

Esto permite complementar la salida del ranking con evidencia sobre las variables de mayor influencia.

---

## 📤 Exportación

La app genera artefactos reutilizables para análisis y documentación.

### Tablas
- ranking filtrado (`CSV`)
- resultados completos (`XLSX`)

### Figuras
- benchmark comparativo (`PNG`)

### Ubicación de salida
```text
reports/
├── figures/
└── tables/
```

---

## ⚙️ Instalación

### Instalación estándar

```bash
pip install -r requirements.txt
```

### Reproducibilidad exacta del entorno

```bash
pip install -r requirements.lock.txt
```

---

## ▶️ Ejecución

```bash
streamlit run app/app.py
```

---

## 🔁 Reproducibilidad

El proyecto incorpora elementos para facilitar replicación y trazabilidad:

- dependencias fijas en `requirements.txt`
- snapshot del entorno en `requirements.lock.txt`
- estrategia de validación temporal
- exportación automática de artefactos
- control explícito de versión mediante archivo `VERSION`

---

## 📊 Resultados esperados

La salida del sistema combina:

- ranking territorial priorizado
- score de riesgo normalizado
- categoría DSS
- recomendación operativa
- lectura ejecutiva del análisis

En términos metodológicos, el sistema permite comparar el desempeño de modelos distintos sin alterar la lógica general del DSS.

---

## 📘 Aplicación académica

Este proyecto puede utilizarse como base para:

- sistemas de soporte a la decisión en transporte
- integración de machine learning y reglas
- visualización analítica territorial
- benchmarking de modelos predictivos
- documentación académica de tipo tesis, paper o informe técnico

---

## 📚 Cómo citar (APA 7)

```text
Nolasco, E. J. (2026). DSS_Hotspots_RD: Sistema de soporte a la decisión para la priorización de siniestralidad vial basado en modelos multi-algoritmo y reglas (v1.2.0) [Software]. GitHub. https://github.com/edjnolasco/dss_hotspots_rd
```

---

## 👤 Autor

**Edwin José Nolasco**

---

## 📌 Licencia

**MIT License**

---

## 🧠 Conclusión

DSS_Hotspots_RD demuestra que la integración de modelos predictivos, reglas de decisión y mecanismos de priorización puede dar lugar a un sistema más robusto, interpretable y útil para contextos reales de análisis territorial.

El sistema no busca únicamente predecir, sino estructurar decisiones apoyadas en evidencia.
