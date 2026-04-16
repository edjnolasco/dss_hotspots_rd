# src/glossary.py

from __future__ import annotations

from typing import Dict

# =========================================================
# GLOSARIO COMPLETO (para expander / documentación)
# =========================================================

GLOSARIO_DSS: Dict[str, str] = {
    "DSS (Decision Support System)": (
        "Sistema interactivo que integra datos, modelos analíticos y "
        "conocimiento experto para apoyar la toma de decisiones en "
        "contextos semi-estructurados o no estructurados."
    ),
    "Pipeline de datos": (
        "Secuencia estructurada de procesamiento que incluye ingestión, "
        "limpieza, validación, transformación, modelado y evaluación."
    ),
    "Modelo predictivo": (
        "Algoritmo que aprende patrones a partir de datos históricos para "
        "generar predicciones, clasificaciones o estimaciones de riesgo."
    ),
    "Reglas de negocio": (
        "Condiciones definidas por expertos del dominio que complementan "
        "las decisiones generadas por el modelo y permiten ajustar la lógica "
        "del sistema a necesidades operativas."
    ),
    "Sistema híbrido": (
        "Arquitectura que combina modelos predictivos, reglas de negocio "
        "y visualización interactiva dentro de un mismo sistema DSS."
    ),
    "Top-K Ranking": (
        "Estrategia de priorización mediante la cual el sistema devuelve "
        "las K alternativas más relevantes según una puntuación calculada."
    ),
    "HitRate@K": (
        "Métrica de evaluación que mide si el resultado esperado se encuentra "
        "dentro de las primeras K posiciones del ranking generado."
    ),
    "Validación de datos": (
        "Proceso de verificación de integridad, consistencia y estructura "
        "de los datos antes de su utilización en el análisis."
    ),
    "Feature Engineering": (
        "Proceso de construcción, transformación y selección de variables "
        "relevantes que mejoran el desempeño del modelo."
    ),
    "GeoJSON": (
        "Formato estándar para representar datos geoespaciales, utilizado "
        "para visualizar provincias o regiones en mapas interactivos."
    ),
    "Interpretabilidad (XAI)": (
        "Capacidad del sistema para explicar cómo y por qué se generan "
        "las predicciones o recomendaciones."
    ),
    "Cobertura geográfica": (
        "Grado en que los datos del sistema logran asociarse correctamente "
        "con las entidades territoriales disponibles en la capa cartográfica."
    ),
    "Registros válidos": (
        "Conjunto de observaciones que cumplen con los criterios de calidad "
        "y pueden ser utilizadas en el análisis."
    ),
    "Categoría DSS": (
        "Clasificación de prioridad operativa generada por el sistema de "
        "soporte a decisiones a partir del score de riesgo y de las reglas "
        "de decisión aplicadas."
    ),
    "Score actual": (
        "Índice compuesto de riesgo relativo calculado por el DSS para la "
        "provincia seleccionada. Valores más altos indican mayor prioridad "
        "operativa."
    ),
    "Predicción próxima": (
        "Estimación del número de fallecidos esperados en el próximo período "
        "según la salida del modelo."
    ),
    "Δ abs.": (
        "Diferencia absoluta entre el valor actual observado y la predicción "
        "del próximo período."
    ),
    "Posición": (
        "Lugar que ocupa la provincia dentro del ranking priorizado del DSS "
        "para los filtros activos."
    ),
    "Provincia en foco": (
        "Provincia seleccionada para análisis detallado en la vista focalizada "
        "del dashboard."
    ),
    "Trazabilidad de la decisión": (
        "Explicación textual de la regla aplicada, la justificación y la "
        "recomendación asociadas a la provincia seleccionada."
    ),
    "Año de análisis": (
        "Año seleccionado como referencia para el cálculo del ranking y las métricas."
    ),
    "Provincias visibles": (
        "Número de provincias consideradas en el análisis tras aplicar los filtros activos."
    ),
    "MAE": (
        "Error absoluto medio del modelo. Indica la diferencia promedio entre valores reales y predichos."
    ),
    "R²": (
        "Coeficiente de determinación. Mide qué proporción de la variabilidad es explicada por el modelo."
    ),
}

# =========================================================
# TOOLTIPS DE MÉTRICAS (para UI)
# =========================================================

METRIC_TOOLTIPS: Dict[str, str] = {
    "Dataset cargado": (
        "Indica que la fuente de datos fue leída correctamente y está "
        "disponible para el procesamiento."
    ),
    "Pipeline ejecutado": (
        "Confirma que la secuencia de carga, validación, transformación "
        "y análisis se completó sin errores críticos."
    ),
    "Ranking generado": (
        "Señala que el sistema ya calculó la priorización final de entidades "
        "según la lógica analítica del DSS."
    ),
    "Mapa habilitado": (
        "Indica que la capa geoespacial (GeoJSON) fue cargada y está lista "
        "para visualización e interacción."
    ),
    "Top-K": (
        "Número de elementos prioritarios que el sistema devuelve como salida "
        "principal del ranking."
    ),
    "HitRate@K": (
        "Mide si el caso relevante o esperado aparece dentro de las primeras "
        "K posiciones del ranking generado."
    ),
    "Cobertura geográfica": (
        "Porcentaje o cantidad de territorios que lograron vincularse "
        "correctamente con la capa cartográfica."
    ),
    "Registros válidos": (
        "Cantidad de observaciones que superaron el proceso de validación "
        "y pudieron ser utilizadas en el análisis."
    ),
    "Categoría DSS": (
        "Clasificación de prioridad operativa asignada a la provincia "
        "según el score de riesgo y las reglas de decisión."
    ),
    "Score actual": (
        "Índice compuesto de riesgo relativo calculado por el DSS. "
        "Valores más altos indican mayor prioridad operativa."
    ),
    "Predicción próxima": (
        "Estimación del número de fallecidos esperados en el próximo período "
        "según la salida del modelo."
    ),
    "Δ abs.": (
        "Diferencia absoluta entre el valor actual observado y la predicción "
        "del próximo período."
    ),
    "Posición": (
        "Lugar que ocupa la provincia dentro del ranking priorizado del DSS "
        "para los filtros activos."
    ),
    "Provincia en foco": (
        "Provincia seleccionada actualmente para análisis detallado en la "
        "vista focalizada."
    ),
    "Trazabilidad de la decisión": (
        "Resume la regla aplicada, la justificación y la recomendación "
        "asociadas a la provincia seleccionada."
    ),
    "Año de análisis": (
        "Año seleccionado como referencia para el cálculo del ranking y las métricas."
    ),
    "Provincias visibles": (
        "Número de provincias consideradas en el análisis tras aplicar los filtros activos."
    ),
    "MAE": (
        "Error absoluto medio del modelo. Indica la diferencia promedio entre valores reales y predichos."
    ),
    "R²": (
        "Coeficiente de determinación. Mide qué proporción de la variabilidad es explicada por el modelo."
    ),
}

# =========================================================
# UTILIDAD OPCIONAL (consistencia entre UI y glosario)
# =========================================================

def get_tooltip(key: str) -> str:
    """
    Devuelve el tooltip asociado a una métrica.

    Parameters
    ----------
    key : str
        Nombre de la métrica o concepto.

    Returns
    -------
    str
        Texto del tooltip. Si no existe, retorna cadena vacía
        para evitar errores en la UI.
    """
    return METRIC_TOOLTIPS.get(key, "")