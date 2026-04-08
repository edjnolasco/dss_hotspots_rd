# DSS_Hotspots_RD

Sistema de Soporte a la Decisión (DSS) para la predicción y priorización de hotspots de accidentes de tránsito en la República Dominicana.

## Autor
Edwin José Nolasco

## Descripción

Este proyecto implementa un DSS híbrido que combina:
- Modelos predictivos (Machine Learning)
- Reglas de negocio
- Visualización interactiva

El objetivo es identificar provincias con mayor riesgo de fallecimientos para apoyar la toma de decisiones.

## Tecnologías
- Pandas
- NumPy
- Scikit-learn
- SHAP
- Streamlit

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app/app.py
