from __future__ import annotations

import streamlit as st
from typing import Any

from ui.ui_components import render_glossary_expander


def render_help_section(glossary: dict[str, Any]) -> None:
    """
    Renderiza la sección 'Ayuda e interpretación' del DSS.

    Esta sección centraliza:
    - criterios de lectura del sistema
    - definiciones clave
    - glosario DSS
    """

    st.markdown("### Ayuda e interpretación")
    st.caption(
        "Esta sección reúne definiciones, criterios de lectura e interpretación "
        "de la salida generada por el sistema."
    )

    help_col1, help_col2 = st.columns([1.15, 1.0])

    # =========================
    # Columna izquierda
    # =========================
    with help_col1:

        with st.container(border=True):
            st.markdown("**Cómo leer la salida del DSS**")
            st.write(
                "El sistema no presenta únicamente una predicción aislada. "
                "La salida final combina una capa analítica y una capa de reglas, "
                "por lo que la prioridad operativa depende tanto del comportamiento "
                "estimado como de la lógica de decisión aplicada."
            )

        with st.container(border=True):
            st.markdown("**Claves de interpretación**")

            st.write(
                "**Score de riesgo.** Resume la intensidad relativa del riesgo y sirve "
                "como base para la priorización comparativa entre provincias."
            )

            st.write(
                "**Predicción próxima.** Representa el valor esperado para el siguiente "
                "período, útil para anticipar deterioro, estabilidad o mejora."
            )

            st.write(
                "**Δ abs. y Δ %.** Expresan la magnitud del cambio entre la situación "
                "actual y la estimación siguiente, en términos absolutos y relativos."
            )

            st.write(
                "**Categoría DSS.** Es la clasificación operativa final que el sistema "
                "asigna después de aplicar la lógica de reglas."
            )

            st.write(
                "**Top-K.** Corresponde al subconjunto de provincias que concentran la "
                "prioridad de intervención o seguimiento en el escenario analizado."
            )

        with st.container(border=True):
            st.markdown("**Lectura metodológica mínima**")
            st.write(
                "La vista de ranking refleja la salida final del DSS. "
                "La sección de métricas evalúa la calidad de la priorización, "
                "la explicabilidad permite observar el peso relativo de variables "
                "y la narrativa resume los hallazgos principales en lenguaje interpretativo."
            )

        with st.container(border=True):
            st.markdown("**Nota de uso**")
            st.write(
                "La interpretación adecuada del DSS requiere considerar conjuntamente "
                "la categoría asignada, la posición en el ranking, la predicción siguiente "
                "y el contexto comparativo entre provincias."
            )

    # =========================
    # Columna derecha
    # =========================
    with help_col2:

        with st.container(border=True):
            st.markdown("**Glosario integrado**")
            st.caption(
                "Conceptos clave utilizados en la lógica del sistema y en la "
                "interpretación del dashboard."
            )

            render_glossary_expander(
                glossary=glossary,
                title="Conceptos del glosario",
                intro="",
                expanded=False,
            )