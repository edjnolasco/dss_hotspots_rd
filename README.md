# DSS_Hotspots_RD

![CI](https://github.com/edjnolasco/dss_hotspots_rd/actions/workflows/ci.yml/badge.svg)

Sistema de Soporte a la Decisión (DSS) para la predicción y priorización de hotspots de accidentes de tránsito en la República Dominicana.

## Autor
Edwin José Nolasco

---

## Descripción

Este proyecto implementa un DSS híbrido orientado a la toma de decisiones en seguridad vial, integrando:

- Modelos predictivos basados en Machine Learning
- Reglas de negocio para clasificación de riesgo
- Visualización interactiva mediante dashboard

El sistema permite identificar provincias con mayor probabilidad de incremento en fallecimientos, facilitando la priorización de intervenciones.

---

## Demo

👉 *(Opcional — agrega aquí cuando lo despliegues)*  
- Streamlit Cloud: https://tu-app.streamlit.app  

---

## Dashboard (Vista del sistema)

![Dashboard DSS](docs/dashboard.png)

> Visualización del ranking de riesgo por provincia y métricas del sistema DSS.

---

## Arquitectura

El sistema sigue el modelo C4:

### Nivel 1 — Sistema
DSS de predicción de hotspots de accidentes en RD.

### Nivel 2 — Contenedores
- **Frontend**: Streamlit
- **Motor DSS**: Pipeline + modelo + reglas

### Nivel 3 — Componentes
- Ingesta y normalización de datos
- Ingeniería de características
- Modelo predictivo (Random Forest)
- Capa de reglas DSS
- Métricas Top-K (HitRate@K, nDCG@K)

---

## Tecnologías

- Pandas
- NumPy
- Scikit-learn
- SHAP (opcional)
- Streamlit

---

## Dataset

Fuente:
- Datos abiertos de accidentes de tránsito en República Dominicana

Archivo incluido:
```bash
data/fallecimientos_provincias.csv
