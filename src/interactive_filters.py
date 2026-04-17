from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st

from src.view_state import (
    build_active_analysis_context,
    get_normalization_mode,
    get_selected_years,
    set_active_analysis_context,
    set_selected_top_k,
    set_state,
)
from ui.ui_sections import apply_interactive_filters, build_year_ranking


@dataclass
class InteractiveContext:
    selected_years: list[int]
    selected_provinces: list[str]
    metric_column: str
    top_n: int
    show_top_only: bool
    filtered_ranking: pd.DataFrame
    province_options: list[str]
    selected_year_label: str
    available_provinces_for_years: list[str]
    year_filtered_df: pd.DataFrame


def coerce_top_n(num_items: int, current_value: int | None) -> int:
    if num_items <= 0:
        return 0
    if num_items <= 3:
        return num_items
    if current_value is None:
        return min(9, num_items)
    return min(max(int(current_value), 3), num_items)


def build_interactive_context(
    *,
    active_section: str,
    analytic_sections: set[str],
    scored_df: pd.DataFrame,
    all_years: list[int],
    default_year: int,
    metric_options: list[str],
    source_mode: str,
    geo_mode: str,
) -> InteractiveContext:
    """
    Construye y devuelve todo el contexto de exploración interactiva.
    También sincroniza session_state y el contexto activo del análisis.
    """
    selected_years: list[int] = all_years.copy()
    selected_provinces: list[str] = []
    metric_column = st.session_state.get("metric_column", "categoria")
    top_n = st.session_state.get("top_n", 0) or 0
    show_top_only = st.session_state.get("show_top_only", False)
    filtered_ranking = pd.DataFrame()
    province_options: list[str] = []
    selected_year_label = str(all_years[-1]) if all_years else ""
    available_provinces_for_years: list[str] = []
    year_filtered_df = scored_df.copy()

    if active_section not in analytic_sections:
        return InteractiveContext(
            selected_years=selected_years,
            selected_provinces=selected_provinces,
            metric_column=metric_column,
            top_n=top_n,
            show_top_only=show_top_only,
            filtered_ranking=filtered_ranking,
            province_options=province_options,
            selected_year_label=selected_year_label,
            available_provinces_for_years=available_provinces_for_years,
            year_filtered_df=year_filtered_df,
        )

    st.markdown("### Exploración interactiva")

    fcol1, fcol2, fcol3, fcol4 = st.columns([1.2, 1.6, 1.0, 1.0])

    include_all_years = fcol1.checkbox(
        "Todos los años",
        key="include_all_years",
    )

    if include_all_years:
        selected_years = all_years
        st.session_state["selected_years"] = all_years
    else:
        current_years = (
            get_selected_years()
            or st.session_state.get("selected_years", [default_year])
            or [default_year]
        )
        current_years = [y for y in current_years if y in all_years]
        if not current_years:
            current_years = [default_year]

        if st.session_state.get("selected_years") != current_years:
            st.session_state["selected_years"] = current_years

        selected_years = fcol1.multiselect(
            "Años",
            options=all_years,
            key="selected_years",
        )

        if not selected_years:
            st.warning("Debes seleccionar al menos un año.")
            st.stop()

    year_filtered_df = scored_df[scored_df["year"].isin(selected_years)].copy()

    available_provinces_for_years = sorted(
        year_filtered_df["provincia"].dropna().astype(str).unique().tolist()
    )

    if not available_provinces_for_years:
        st.warning("No hay provincias disponibles para la combinación actual de años.")
        st.stop()

    include_all_provinces = fcol2.checkbox(
        "Todas las provincias",
        key="include_all_provinces",
    )

    if include_all_provinces:
        selected_provinces = available_provinces_for_years
        st.session_state["selected_provinces_filter"] = available_provinces_for_years
    else:
        current_provinces = st.session_state.get("selected_provinces_filter", []) or []
        current_provinces = [
            p for p in current_provinces if p in available_provinces_for_years
        ]

        if not current_provinces:
            current_provinces = available_provinces_for_years[: min(5, len(available_provinces_for_years))]

        if st.session_state.get("selected_provinces_filter") != current_provinces:
            st.session_state["selected_provinces_filter"] = current_provinces

        selected_provinces = fcol2.multiselect(
            "Provincias",
            options=available_provinces_for_years,
            placeholder="Selecciona una o varias provincias",
            key="selected_provinces_filter",
        )

        if not selected_provinces:
            st.warning("Debes seleccionar al menos una provincia.")
            st.stop()

    metric_column = fcol3.selectbox(
        "Variable del mapa",
        options=metric_options,
        key="metric_column",
    )
    set_state("selected_metric", metric_column)

    num_provinces_visible = len(selected_provinces)

    if num_provinces_visible == 0:
        st.warning("No hay provincias disponibles para los filtros actuales.")
        st.stop()

    if num_provinces_visible <= 3:
        top_n = num_provinces_visible
        st.session_state["top_n"] = top_n
        set_selected_top_k(top_n)
        fcol4.info(f"Top-N fijado en {top_n}")
    else:
        current_top_n = coerce_top_n(
            num_items=num_provinces_visible,
            current_value=st.session_state.get("top_n"),
        )

        if st.session_state.get("top_n") != current_top_n:
            st.session_state["top_n"] = current_top_n

        top_n = fcol4.slider(
            "Top-N",
            min_value=3,
            max_value=num_provinces_visible,
            key="top_n",
        )
        set_selected_top_k(top_n)

    show_top_only = st.checkbox(
        "Mostrar solo Top-N en ranking y mapa",
        key="show_top_only",
    )

    base_multi_year = (
        year_filtered_df[year_filtered_df["provincia"].isin(selected_provinces)]
        .sort_values(["provincia", "year"])
        .groupby("provincia", as_index=False)
        .tail(1)
        .copy()
    )

    filtered_ranking = build_year_ranking(
        base_multi_year,
        int(base_multi_year["year"].max()),
    )

    filtered_ranking = apply_interactive_filters(
        ranking_df=filtered_ranking,
        selected_provinces=selected_provinces,
        top_n=top_n,
        show_top_only=show_top_only,
    )

    if filtered_ranking.empty:
        st.warning("No hay datos disponibles con la combinación actual de filtros.")
        st.stop()

    province_options = sorted(
        filtered_ranking["provincia"].dropna().astype(str).unique().tolist()
    )

    selected_year_label = (
        str(selected_years[0])
        if len(selected_years) == 1
        else f"{min(selected_years)}–{max(selected_years)}"
    )

    analysis_context = build_active_analysis_context(
        available_years=all_years,
        available_metrics=metric_options,
    )
    analysis_context.update(
        {
            "source_mode": source_mode,
            "geo_mode": geo_mode,
            "active_section": active_section,
            "selected_provinces_filter": selected_provinces,
            "show_top_only": show_top_only,
            "top_n": top_n,
            "selected_year_label": selected_year_label,
            "source_label": st.session_state.get("source_label"),
            "normalization_mode": get_normalization_mode(),
        }
    )
    set_active_analysis_context(analysis_context)

    return InteractiveContext(
        selected_years=selected_years,
        selected_provinces=selected_provinces,
        metric_column=metric_column,
        top_n=top_n,
        show_top_only=show_top_only,
        filtered_ranking=filtered_ranking,
        province_options=province_options,
        selected_year_label=selected_year_label,
        available_provinces_for_years=available_provinces_for_years,
        year_filtered_df=year_filtered_df,
    )