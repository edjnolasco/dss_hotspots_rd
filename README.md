# DSS_Hotspots_RD

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

## Arquitectura

El sistema sigue el modelo C4:

### Nivel 1 — Sistema
DSS de predicción de hotspots de accidentes en RD.

### Nivel 2 — Contenedores
- **Frontend**: Streamlit (visualización interactiva)
- **Motor DSS**: Pipeline de datos + modelo predictivo + reglas

### Nivel 3 — Componentes
- Ingesta y normalización de datos
- Ingeniería de características (lags, rolling, tendencia)
- Modelo predictivo (Random Forest)
- Capa de reglas (clasificación de riesgo)
- Métricas Top-K (HitRate@K, nDCG@K)

---

## Tecnologías

- Pandas — manipulación de datos
- NumPy — operaciones numéricas
- Scikit-learn — modelado predictivo
- SHAP — interpretabilidad (opcional)
- Streamlit — interfaz interactiva

---

## Dataset

Fuente:
- Datos abiertos de accidentes de tránsito en República Dominicana

Archivo de ejemplo incluido:
```bash
data/fallecimientos_provincias.csv
