from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.exporter import build_excel_export, build_export_filename
from src.narrative import build_brief_executive_summary
from src.view_state import (
    get_normalization_mode,
    get_selected_view,
    set_last_export_metadata,
)
from ui.ui_sections import render_export_section


def summarize_selected_provinces(
    selected_provinces: list[str],
    available_provinces: list[str],
    max_items: int = 5,
) -> str:
    """
    Resume la selección de provincias para mostrarla en la UX de exportación.
    """
    if not selected_provinces:
        return "Sin selección"

    if available_provinces and len(selected_provinces) == len(available_provinces):
        return "Todas"

    if len(selected_provinces) <= max_items:
        return ", ".join(selected_provinces)

    preview = ", ".join(selected_provinces[:max_items])
    return f"{preview} +{len(selected_provinces) - max_items} más"


def build_export_metadata(
    *,
    selected_years: list[int],
    selected_provinces: list[str],
    metric_column: str,
    top_n: int,
    show_top_only: bool,
    source_label: str | None,
    selected_year_label: str,
    active_section: str,
    project_name: str,
    version: str,
) -> dict[str, Any]:
    """
    Construye la metadata estándar del análisis para persistencia y exportación.
    """
    return {
        "selected_years": selected_years,
        "selected_provinces": selected_provinces,
        "metric_column": metric_column,
        "top_n": top_n,
        "show_top_only": show_top_only,
        "source_label": source_label,
        "selected_view": get_selected_view(),
        "normalization_mode": get_normalization_mode(),
        "selected_year_label": selected_year_label,
        "active_section": active_section,
        "project_name": project_name,
        "version": version,
    }


def render_export_panel(
    *,
    filtered_ranking: pd.DataFrame,
    metricas_df: pd.DataFrame,
    scored_df: pd.DataFrame,
    explain_df: pd.DataFrame,
    selected_years: list[int],
    selected_provinces: list[str],
    metric_column: str,
    top_n: int,
    show_top_only: bool,
    selected_year_label: str,
    available_provinces_for_years: list[str],
    project_name: str,
    version: str,
    source_label: str | None,
    active_section: str,
) -> None:
    """
    Renderiza la experiencia completa de exportación profesional:
    - metadata
    - resumen ejecutivo breve
    - botón principal
    - opciones avanzadas
    """
    export_scored_df = scored_df[scored_df["year"].isin(selected_years)].copy()

    export_metadata = build_export_metadata(
        selected_years=selected_years,
        selected_provinces=selected_provinces,
        metric_column=metric_column,
        top_n=top_n,
        show_top_only=show_top_only,
        source_label=source_label,
        selected_year_label=selected_year_label,
        active_section=active_section,
        project_name=project_name,
        version=version,
    )

    set_last_export_metadata(export_metadata)

    excel_bytes = build_excel_export(
        filtered_ranking=filtered_ranking,
        metricas_df=metricas_df,
        scored_df=export_scored_df,
        explain_df=explain_df,
        metadata=export_metadata,
    )

    excel_filename = build_export_filename(
        project_name=project_name,
        extension="xlsx",
        selected_years=selected_years,
        metric_column=metric_column,
        normalization_mode=get_normalization_mode(),
        prefix="reporte_dss",
    )

    province_summary = summarize_selected_provinces(
        selected_provinces=selected_provinces,
        available_provinces=available_provinces_for_years,
    )

    latest_year = max(selected_years) if selected_years else 0

    brief_summary = build_brief_executive_summary(
        ranking_df=filtered_ranking,
        metricas_df=metricas_df,
        latest_year=latest_year,
        selected_year_label=selected_year_label,
    )

    with st.container(border=True):
        st.markdown("### 📦 Exportación profesional DSS")
        st.markdown("#### Contexto del análisis")
        st.markdown(
            f"""
- **Años:** {selected_year_label}
- **Provincias:** {province_summary}
- **Métrica:** {metric_column}
- **Top-N:** {top_n}
- **Modo:** {get_normalization_mode()}
- **Fuente:** {source_label or "No disponible"}
"""
        )

        st.markdown(
            f"""
            <div style="
                border-radius: 12px;
                padding: 12px 14px;
                margin: 8px 0 12px 0;
                border: 1px solid rgba(148, 163, 184, 0.18);
                background: rgba(30, 41, 59, 0.32);
            ">
                <strong>Resumen ejecutivo breve:</strong> {brief_summary}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.download_button(
            label="📥 Descargar reporte DSS completo (Excel)",
            data=excel_bytes,
            file_name=excel_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_dss_excel_report",
            use_container_width=True,
        )

        st.caption(
            "Incluye ranking priorizado, métricas, datos completos, explicabilidad (XAI) y metadata del análisis."
        )

        st.success("Este archivo es apto para análisis, auditoría y presentación ejecutiva.")

    with st.expander("Opciones avanzadas de exportación"):
        render_export_section(
            filtered_ranking=filtered_ranking,
            metricas_df=metricas_df,
            scored_df=export_scored_df,
            explain_df=explain_df,
            selected_provinces=selected_provinces,
            project_name=project_name,
            version=version,
            selected_year=max(selected_years) if selected_years else 0,
        )