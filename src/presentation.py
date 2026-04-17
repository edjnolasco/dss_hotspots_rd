from __future__ import annotations

import streamlit as st
import pandas as pd

from .narrative import build_brief_executive_summary


def render_presentation_mode(context) -> None:
    st.title("DSS Hotspots RD")
    st.caption("Panel ejecutivo para priorización territorial de riesgo vial")

    latest_year = (
        max(context.selected_years)
        if context.selected_years
        else int(context.results.get("latest_year", 0) or 0)
    )

    if context.filtered_ranking is not None and not context.filtered_ranking.empty:
        summary = build_brief_executive_summary(
            ranking_df=context.filtered_ranking,
            metricas_df=context.metricas_df,
            latest_year=latest_year,
            selected_year_label=context.selected_year_label,
        )

        st.markdown("## Resumen ejecutivo")
        st.info(summary)

    st.markdown("## Indicadores clave")
    c1, c2, c3, c4 = st.columns(4)

    total_provinces = (
        len(context.filtered_ranking)
        if context.filtered_ranking is not None
        else 0
    )

    top1 = None
    if context.filtered_ranking is not None and not context.filtered_ranking.empty:
        top1 = context.filtered_ranking.iloc[0]["provincia"]

    c1.metric("Período", context.selected_year_label)
    c2.metric("Provincias evaluadas", total_provinces)
    c3.metric("Top prioritaria", top1 or "N/D")
    c4.metric("Top-N", context.top_n)

    st.markdown("## Mapa de priorización")
    context.render_map_fn()

    st.markdown("## Provincias prioritarias")
    if context.filtered_ranking is not None and not context.filtered_ranking.empty:
        preview_cols = [
            col for col in ["rank", "provincia", context.metric_column]
            if col in context.filtered_ranking.columns
        ]
        st.dataframe(
            context.filtered_ranking[preview_cols].head(context.top_n),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("## Recomendación DSS")
    st.success(
        "Se recomienda priorizar intervención en las provincias del Top-N "
        "por su mayor nivel relativo de criticidad en el período analizado."
    )

    st.markdown("## Exportación")
    context.render_export_fn(executive=True)