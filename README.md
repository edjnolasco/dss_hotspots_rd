# 🚦 DSS_Hotspots_RD

![CI](https://github.com/edjnolasco/dss_hotspots_rd/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-stable-success)

📊 Sistema de Soporte a la Decisión (DSS) para la predicción y priorización de hotspots de accidentes de tránsito en la República Dominicana.

---

## 👤 Autor
**Edwin José Nolasco**

---

## 📌 Descripción

Este proyecto implementa un DSS híbrido orientado a la toma de decisiones en seguridad vial, integrando:

- 🤖 Modelos predictivos basados en Machine Learning  
- 📏 Reglas de negocio para clasificación de riesgo  
- 📊 Visualización interactiva mediante dashboard  

El sistema permite identificar provincias con mayor probabilidad de incremento en fallecimientos, facilitando la priorización de intervenciones.

---

## 🌐 Demo

👉 *(Opcional — agrega aquí cuando lo despliegues)*  
- Streamlit Cloud: https://tu-app.streamlit.app  

---

## 🖥️ Dashboard (Vista del sistema)

![Dashboard DSS](docs/dashboard.png)

> Visualización del ranking de riesgo por provincia y métricas del sistema DSS.

---

## 🧠 Arquitectura (Modelo C4)

### 🔹 Nivel 1 — Sistema
DSS de predicción de hotspots de accidentes en RD.

### 🔹 Nivel 2 — Contenedores
- 🖥️ **Frontend**: Streamlit  
- ⚙️ **Motor DSS**: Pipeline + modelo + reglas  

### 🔹 Nivel 3 — Componentes
- 📥 Ingesta y normalización de datos  
- 🧮 Ingeniería de características  
- 🌲 Modelo predictivo (Random Forest)  
- 📐 Capa de reglas DSS  
- 📊 Métricas Top-K (HitRate@K, nDCG@K)  

---

## ⚙️ Arquitectura funcional DSS

Flujo lógico del sistema:

DATA → PIPELINE → MODELO → REGLAS → RANKING → VISUALIZACIÓN



### 🔧 Componentes clave

**1. 📂 Data Layer**
- Normalización robusta del dataset  
- Estandarización de columnas (`provincia`, `year`, `fecha`, etc.)  

**2. 🧠 Pipeline (`src/pipeline.py`)**
- Feature engineering temporal:
  - ⏳ lags  
  - 📉 rolling means  
  - 🔄 deltas  
- Modelo:
  - 🌲 RandomForestRegressor  

**3. 📏 Reglas DSS**

| Score | Categoría |
|------|--------|
| ≥ 0.75 | 🔴 Alta |
| ≥ 0.50 | 🟠 Media-Alta |
| ≥ 0.25 | 🟡 Media |
| < 0.25 | 🟢 Baja |

---

**4. 🎯 Capa de decisión**
- Ranking por riesgo  
- Selección Top-N dinámica  

**5. 🗺️ UI**
- Mapa interactivo  
- Drill-down por provincia  
- Filtros múltiples  

---

## 📊 Métricas Top-K (Evaluación del DSS)

El problema se modela como **priorización (ranking)**, no solo predicción.

### 📌 Definiciones

- Ranking predicho → `score_riesgo`  
- Ranking real → `fallecidos_actuales`  

---

### 🔍 Métricas implementadas

#### 🔹 HitRate@K
Proporción de provincias relevantes capturadas por el modelo:

HitRate@K = |TopK_real ∩ TopK_predicho| / |TopK_real|


---

#### 🔹 Top-K Accuracy
Equivalente a HitRate en este contexto.

---

#### 🔹 Precision@K
Calidad del Top-K predicho:

Precision@K = |TopK_real ∩ TopK_predicho| / |TopK_predicho|


---

### 🎯 Interpretación

- 📈 HitRate alto → el DSS identifica correctamente zonas críticas  
- 🎯 Precision alta → ranking confiable  
- ⚠️ Más relevante que MAE en este contexto  

---

## 🧰 Tecnologías

- 🐍 Pandas  
- 🔢 NumPy  
- 🤖 Scikit-learn  
- 📊 Streamlit  
- 🔍 SHAP (opcional)  

---

## 🚀 Ejecución

### 1. Clonar

```bash
git clone https://github.com/edjnolasco/dss_hotspots_rd.git
cd dss_hotspots_rd
```

2. Entorno

```bash

python -m venv .venv
source .venv/bin/activate  # Linux / Mac
.venv\Scripts\activate     # Windows

```

3. Dependencias

```bash
pip install -r requirements.txt
```

4. Ejecutar

```
streamlit run app/app.py

```
🗂️ Estructura del proyecto

```text
dss_hotspots_rd/
│
├── app/
│   └── app.py
│
├── src/
│   ├── pipeline.py
│   ├── ui_map.py
│   ├── ui_sections.py
│   ├── data_sources.py
│   ├── province_utils.py
│   └── ...
│
├── data/
├── docs/
├── tests/
├── requirements.txt
└── README.md

```

🔁 CI (Integración continua)

✔ Validación de compilación
✔ Validación del pipeline
✔ Control de errores críticos

📈 Estado del proyecto

🟢 Versión estable
✔ Pipeline validado
✔ UI interactiva funcional
✔ Métricas DSS implementadas

🔮 Líneas futuras
🤖 Integración con SVM (kernels + regularización)
🔍 SHAP avanzado
📊 Evaluación multi-año
🌐 Datos en tiempo real

⚠️ Nota

Este sistema está diseñado como DSS experimental/académico.
Debe utilizarse como apoyo a la decisión, no como predicción determinista.

🇺🇸 English
📊 Description

Decision Support System (DSS) for predicting and prioritizing traffic accident hotspots in the Dominican Republic.

This project integrates:

🤖 Machine Learning models
📏 Business rules
🗺️ Interactive visualization

The goal is to identify high-risk provinces to support road safety decision-making.

🧠 DSS Architecture

DATA → PIPELINE → MODEL → RULES → RANKING → VISUALIZATION

Components:
📂 Data Layer: Robust normalization (province, year, date, etc.)
🧠 Pipeline: Feature engineering + Random Forest
📏 Rules Layer: Risk classification
🎯 Ranking Layer: Top-N prioritization
🖥️ UI Layer: Streamlit + interactive map

📊 Metrics (Top-K Evaluation)

The problem is treated as a ranking task, not just regression.

🔹 HitRate@K → coverage of critical regions
🔹 Precision@K → ranking quality
🔹 Top-K Accuracy → DSS performance

🚀 Run

```bash

git clone https://github.com/edjnolasco/dss_hotspots_rd.git
cd dss_hotspots_rd
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/app.py

```

🗂️ Structure

app/        → UI
src/        → DSS logic
data/       → dataset
docs/       → resources
tests/      → validations

📈 Status

🟢 Stable
✔ Validated pipeline
✔ Functional UI
✔ Top-K metrics implemented

👤 Author

Edwin José Nolasco

⚠️ Disclaimer

This system is designed as an experimental/academic DSS.
Results should be interpreted as decision support, not deterministic predictions.
