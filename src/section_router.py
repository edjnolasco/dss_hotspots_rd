from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd
import streamlit as st

from src.narrative import build_brief_executive_summary, build_executive_summary
from src.view_state import set_last_summary_text
from ui.ui_about import render_about_section
from ui.ui_export_section import render_export_panel
from ui.ui_help import render_help_section
from ui.ui_map_section import render_map_section
from ui.ui_overview import render_overview_section
from ui.ui_ranking_section import render_ranking_section
from ui.ui_sections import (
    render_metrics_tab,
    render_narrative_tab,
    render_xai_tab,
)


@dataclass
class SectionRenderContext:
    active_section: str
    results: dict[str, Any]
    filtered_ranking: pd.DataFrame
    metricas_df: pd.DataFrame
    explain_df: pd.DataFrame
    scored_df: pd.DataFrame
    metric_column: str
    top_n: int
    show_top_only: bool
    geo_mode: str
    geo_local_path: str
    uploaded_geo: Any
    province_options: list[str]
    selected_years: list[int]
    selected_year_label: str
    selected_provinces: list[str]
    available_provinces_for_years: list[str]
    project_name: str
    version: str
    glossary: dict[str, Any]
    source_label: str | None
    set_selected_province_fn: Callable[[str | None], bool]
    build_rule_trace_text_fn: Callable[[pd.Series], str]
    build_recommendation_text_fn: Callable[[pd.Series], str]
    show_dss_trace: bool


def render_section(context: SectionRenderContext) -> None:
    section = context.active_section

    if section == "Ranking":
        render_ranking_section(
            filtered_ranking=context.filtered_ranking,
            top_n=context.top_n,
            show_dss_trace=context.show_dss_trace,
        )
        return

    if section == "Mapa y drill-down":
        _render_map_and_drilldown(context)
        return

    if section == "Métricas":
        _render_metrics(context)
        return

    if section == "Explicabilidad":
        _render_xai(context)
        return

    if section == "Narrativa":
        _render_narrative(context)
        return

    if section == "Exportación":
        _render_export(context)
        return

    if section == "Ayuda e interpretación":
        render_help_section(context.glossary)
        return

    if section == "Acerca de":
        render_about_section()
        return

    st.warning(f"Sección no reconocida: {section}")


def _render_map_and_drilldown(context: SectionRenderContext) -> None:
    topk_clicked = render_overview_section(
        filtered_ranking=context.filtered_ranking,
        metric_column=context.metric_column,
        results=context.results,
        selected_year=max(context.selected_years) if context.selected_years else 0,
        geo_mode=context.geo_mode,
        metricas_df=context.metricas_df,
        top_n=context.top_n,
        selected_year_label=context.selected_year_label,
        set_selected_province_fn=context.set_selected_province_fn,
        show_dss_trace=context.show_dss_trace,
    )

    if topk_clicked:
        st.rerun()

    # ✅ BLOQUE CORRECTAMENTE INDENTADO
    latest_year = (
        max(context.selected_years)
        if context.selected_years
        else int(context.results.get("latest_year", 0) or 0)
    )

    if context.filtered_ranking is not None and not context.filtered_ranking.empty:
        brief_summary = build_brief_executive_summary(
            ranking_df=context.filtered_ranking,
            metricas_df=context.metricas_df,
            latest_year=latest_year,
            selected_year_label=context.selected_year_label,
        )

        st.markdown(
            f"""
            <div style="
                border-radius: 14px;
                padding: 14px 16px;
                margin: 10px 0 14px 0;
                border: 1px solid rgba(148, 163, 184, 0.18);
                background: rgba(30, 41, 59, 0.35);
            ">
                <strong>Resumen ejecutivo breve:</strong> {brief_summary}
            </div>
            """,
            unsafe_allow_html=True,
        )

    render_map_section(
        geo_mode=context.geo_mode,
        geo_local_path=context.geo_local_path,
        uploaded_geo=context.uploaded_geo,
        filtered_ranking=context.filtered_ranking,
        metric_column=context.metric_column,
        selected_year_label=context.selected_year_label,
        show_top_only=context.show_top_only,
        top_n=context.top_n,
        province_options=context.province_options,
        scored_df=context.scored_df,
        selected_years=context.selected_years,
        set_selected_province_fn=context.set_selected_province_fn,
        build_rule_trace_text_fn=context.build_rule_trace_text_fn,
        build_recommendation_text_fn=context.build_recommendation_text_fn,
    )


def _render_metrics(context: SectionRenderContext) -> None:
    if context.show_dss_trace:
        st.caption(
            "Estas métricas no solo evalúan error del modelo, sino también la calidad de la priorización "
            "Top-K producida por el DSS."
        )
    render_metrics_tab(metricas_df=context.metricas_df)


def _render_xai(context: SectionRenderContext) -> None:
    if context.show_dss_trace:
        st.caption(
            "La explicabilidad muestra qué variables pesan más en la generación del score, "
            "mientras que la decisión operativa final se obtiene después mediante reglas."
        )
    render_xai_tab(explain_df=context.explain_df)


def _render_narrative(context: SectionRenderContext) -> None:
    latest_year = (
        max(context.selected_years)
        if context.selected_years
        else int(context.results.get("latest_year", 0) or 0)
    )

    if context.filtered_ranking is not None and not context.filtered_ranking.empty:
        narrative_text = build_executive_summary(
            ranking_df=context.filtered_ranking,
            metricas_df=context.metricas_df,
            latest_year=latest_year,
            selected_year_label=context.selected_year_label,
        )
    else:
        narrative_text = build_executive_summary(
            ranking_df=context.results.get("ranking_df", pd.DataFrame()),
            metricas_df=context.metricas_df,
            latest_year=latest_year,
            selected_year_label=context.selected_year_label,
        )

    set_last_summary_text(str(narrative_text or ""))
    render_narrative_tab(narrative_text=narrative_text)


def _render_export(context: SectionRenderContext) -> None:
    render_export_panel(
        filtered_ranking=context.filtered_ranking,
        metricas_df=context.metricas_df,
        scored_df=context.scored_df,
        explain_df=context.explain_df,
        selected_years=context.selected_years,
        selected_provinces=context.selected_provinces,
        metric_column=context.metric_column,
        top_n=context.top_n,
        show_top_only=context.show_top_only,
        selected_year_label=context.selected_year_label,
        available_provinces_for_years=context.available_provinces_for_years,
        project_name=context.project_name,
        version=context.version,
        source_label=context.source_label,
        active_section=context.active_section,
    )