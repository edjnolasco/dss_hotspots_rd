from __future__ import annotations

from typing import Callable

import pandas as pd
import streamlit as st

from ui.ui_sections import render_kpi_summary
from ui.ui_summary import render_decision_engine_summary
from ui.ui_topk import render_topk_preview


def render_overview_section(
    filtered_ranking: pd.DataFrame,
    metric_column: str,
    results: dict,
    selected_year: int,
    geo_mode: str,
    metricas_df: pd.DataFrame,
    top_n: int,
    selected_year_label: str,
    set_selected_province_fn: Callable[[str | None], bool],
    show_dss_trace: bool,
) -> bool:
    """
    Renderiza el bloque superior de la app:
    - Resumen ejecutivo
    - Vista DSS resumida
    - Exploración territorial (entrada a mapa y drill-down)

    Devuelve True si hubo clic en Top-K y se requiere rerun.
    """
    st.markdown("## Resumen ejecutivo")
    st.caption(
        "Síntesis general del estado del sistema a partir de la información disponible."
    )

    render_kpi_summary(
        filtered_ranking=filtered_ranking,
        metric_column=metric_column,
        results=results,
        selected_year=selected_year,
        geo_mode=geo_mode,
    )

    topk_clicked = False

    if show_dss_trace:
        st.markdown("## Trazabilidad DSS")
        st.caption(
            "Lectura resumida del motor de decisión y acceso rápido al Top-K priorizado."
        )

        render_decision_engine_summary(
            filtered_ranking=filtered_ranking,
            metricas_df=metricas_df,
            top_n=top_n,
            selected_year_label=selected_year_label,
        )

        topk_clicked = render_topk_preview(
            filtered_ranking=filtered_ranking,
            top_n=top_n,
            set_selected_province_fn=set_selected_province_fn,
        )

    st.markdown("## Exploración territorial")
    st.caption(
        "Consulta la distribución espacial del riesgo y profundiza en una provincia específica."
    )

    return topk_clicked