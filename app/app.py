from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from streamlit_plotly_events import plotly_events

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR if (APP_DIR / "src").exists() else APP_DIR.parent

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.data_sources import (  # noqa: E402
    OFFICIAL_PROVINCES_URL,
    fetch_remote_dataframe,
    load_local_dataframe,
    normalize_official_provinces,
    read_dataframe_from_bytes,
)
from src.pipeline import run_pipeline  # noqa: E402
from src.state import ensure_session_state, reset_selection_state  # noqa: E402
from src.ui_map import (  # noqa: E402
    build_geo_quality_summary,
    build_map_cached,
    extract_selected_province_from_click,
    load_geojson_source,
    should_accept_map_click,
)
from src.ui_sections import (  # noqa: E402
    apply_interactive_filters,
    build_year_ranking,
    render_export_section,
    render_kpi_summary,
    render_metrics_tab,
    render_narrative_tab,
    render_province_drilldown,
    render_ranking_tab,
    render_xai_tab,
)
from src.version import AUTHOR, PROJECT_NAME, VERSION  # noqa: E402

FULL_WIDTH = "stretch"

SECTION_OPTIONS = [
    "Ranking",
    "Mapa y drill-down",
    "Métricas",
    "Explicabilidad",
    "Narrativa",
    "Exportación",
]

SOURCE_OPTIONS = [
    "Ruta local",
    "Subir CSV/XLSX",
    "Fuente oficial DIGESETT",
]

GEO_OPTIONS = [
    "Ruta local",
    "Subir GeoJSON",
    "Omitir mapa",
]

METRIC_OPTIONS = [
    "categoria",
    "score_riesgo",
    "fallecidos_actuales",
    "pred_fallecidos_next",
    "delta_pct",
]


def request_section(section_name: str) -> None:
    st.session_state["active_section"] = section_name
    st.session_state["force_section"] = section_name


def ensure_app_state() -> None:
    ensure_session_state()

    defaults: dict[str, Any] = {
        "analysis_results": None,
        "source_label": None,
        "active_section": "Mapa y drill-down",
        "active_section_widget": "Mapa y drill-down",
        "force_section": None,
        "selected_province": None,
        "selected_province_widget": None,
        "selected_years": [],
        "selected_provinces_filter": [],
        "include_all_years": True,
        "include_all_provinces": True,
        "debug_map_click": False,
        "metric_column": "categoria",
        "source_mode": "Ruta local",
        "geo_mode": "Ruta local",
        "local_path": str(ROOT / "data" / "fallecimientos_provincias.csv"),
        "geo_local_path": str(ROOT / "data" / "rd_provinces.geojson"),
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if st.session_state["metric_column"] not in METRIC_OPTIONS:
        st.session_state["metric_column"] = "categoria"

    if st.session_state["source_mode"] not in SOURCE_OPTIONS:
        st.session_state["source_mode"] = "Ruta local"

    if st.session_state["geo_mode"] not in GEO_OPTIONS:
        st.session_state["geo_mode"] = "Ruta local"


def set_selected_province(new_value: str | None) -> bool:
    old_value = st.session_state.get("selected_province")
    if old_value == new_value:
        return False

    st.session_state["selected_province"] = new_value
    st.session_state["selected_province_widget"] = new_value
    return True


def sync_focus_province(valid_options: list[str]) -> None:
    if not valid_options:
        st.session_state["selected_province"] = None
        st.session_state["selected_province_widget"] = None
        return

    current = st.session_state.get("selected_province")
    if current not in valid_options:
        current = valid_options[0]
        st.session_state["selected_province"] = current

    st.session_state["selected_province_widget"] = current


def coerce_top_n(num_items: int, current_value: int | None) -> int:
    if num_items <= 0:
        return 0
    if num_items <= 3:
        return num_items
    if current_value is None:
        return min(10, num_items)
    return min(max(current_value, 3), num_items)


st.set_page_config(page_title=f"{PROJECT_NAME} {VERSION}", layout="wide")
st.title(f"{PROJECT_NAME} {VERSION}")
st.caption(f"Autor: {AUTHOR}")

ensure_app_state()


@st.cache_data(show_spinner=False)
def load_data_remote() -> pd.DataFrame:
    raw = fetch_remote_dataframe(
        OFFICIAL_PROVINCES_URL,
        filename_hint="fallecimientos_provincias.csv",
    )
    return normalize_official_provinces(raw)


@st.cache_data(show_spinner=False)
def load_data_local(path_str: str) -> pd.DataFrame:
    raw = load_local_dataframe(path_str)
    return normalize_official_provinces(raw)


@st.cache_data(show_spinner=False)
def process_uploaded_data(file_name: str, file_bytes: bytes) -> pd.DataFrame:
    raw = read_dataframe_from_bytes(file_bytes, filename_hint=file_name)
    return normalize_official_provinces(raw)


@st.cache_data(show_spinner=False)
def process_pipeline(df: pd.DataFrame) -> dict[str, Any]:
    return run_pipeline(df)


with st.sidebar:
    st.header("Fuente de datos")
    source_mode = st.radio(
        "Selecciona la fuente",
        SOURCE_OPTIONS,
        key="source_mode",
    )

    local_path = (
        st.text_input(
            "Ruta local del dataset",
            key="local_path",
        )
        if source_mode == "Ruta local"
        else st.session_state.get("local_path", "")
    )

    uploaded_file = (
        st.file_uploader(
            "Sube el dataset",
            type=["csv", "xlsx", "xls"],
            key="uploaded_dataset",
        )
        if source_mode == "Subir CSV/XLSX"
        else None
    )

    st.header("GeoJSON")
    geo_mode = st.radio(
        "Selecciona la fuente del mapa",
        GEO_OPTIONS,
        key="geo_mode",
    )

    geo_local_path = (
        st.text_input(
            "Ruta local del GeoJSON",
            key="geo_local_path",
        )
        if geo_mode == "Ruta local"
        else st.session_state.get("geo_local_path", "")
    )

    uploaded_geo = (
        st.file_uploader(
            "Sube el GeoJSON",
            type=["geojson", "json"],
            key="uploaded_geojson",
        )
        if geo_mode == "Subir GeoJSON"
        else None
    )

    st.header("Diagnóstico")
    debug_map_click = st.checkbox(
        "Modo debug de clic del mapa",
        key="debug_map_click",
    )

    run_clicked = st.button(
        "Ejecutar análisis",
        type="primary",
        width=FULL_WIDTH,
        key="run_analysis_button",
    )

if run_clicked:
    try:
        if source_mode == "Fuente oficial DIGESETT":
            try:
                normalized_df = load_data_remote()
                source_label = "Fuente oficial DIGESETT"
            except Exception:
                st.error(
                    "La fuente oficial DIGESETT rechazó la descarga remota "
                    "(HTTP 403 o acceso restringido). Usa la opción "
                    "'Subir CSV/XLSX' con el archivo oficial descargado manualmente."
                )
                st.stop()

        elif source_mode == "Subir CSV/XLSX":
            if uploaded_file is None:
                st.error("Debes subir un archivo.")
                st.stop()

            normalized_df = process_uploaded_data(
                uploaded_file.name,
                uploaded_file.getvalue(),
            )
            source_label = f"Archivo subido: {uploaded_file.name}"

        else:
            normalized_df = load_data_local(local_path)
            source_label = f"Ruta local: {local_path}"

        st.session_state["analysis_results"] = process_pipeline(normalized_df)
        st.session_state["source_label"] = source_label

        reset_selection_state()
        st.session_state["selected_province"] = None
        st.session_state["selected_province_widget"] = None
        st.session_state["selected_years"] = []
        st.session_state["selected_provinces_filter"] = []
        st.session_state["include_all_years"] = True
        st.session_state["include_all_provinces"] = True
        st.session_state["metric_column"] = "categoria"

        request_section("Mapa y drill-down")
        st.success("Análisis ejecutado correctamente.")
        st.rerun()

    except Exception as exc:
        st.error("No fue posible completar el análisis.")
        st.exception(exc)

results = st.session_state.get("analysis_results")

if not results:
    st.info("Configura la fuente de datos y ejecuta el análisis.")
    st.markdown("### Fuente oficial prevista")
    st.code(OFFICIAL_PROVINCES_URL)
    st.markdown("### Nota sobre DIGESETT")
    st.write(
        "Si la descarga remota falla con HTTP 403, usa la opción 'Subir CSV/XLSX' "
        "con el archivo oficial descargado manualmente."
    )
    st.markdown("### GeoJSON esperado")
    st.code(str(ROOT / "data" / "rd_provinces.geojson"))
    st.stop()

st.write(st.session_state.get("source_label", "Fuente no especificada"))

scored_df = results["scored_df"].copy()
metricas_df = results["metricas_df"].copy()
explain_df = results["explain_df"].copy()

all_years = sorted(scored_df["year"].dropna().astype(int).unique().tolist())
default_year = int(results.get("latest_year", all_years[-1]))

st.markdown("## Exploración interactiva")

fcol1, fcol2, fcol3, fcol4 = st.columns([1.2, 1.6, 1.0, 1.0])

include_all_years = fcol1.checkbox(
    "Todos los años",
    key="include_all_years",
)

if include_all_years:
    selected_years = all_years
    st.session_state["selected_years"] = all_years
else:
    current_years = st.session_state.get("selected_years", [default_year]) or [default_year]
    current_years = [y for y in current_years if y in all_years]
    if not current_years:
        current_years = [default_year]

    selected_years = fcol1.multiselect(
        "Años",
        options=all_years,
        default=current_years,
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
    current_provinces = [p for p in current_provinces if p in available_provinces_for_years]

    selected_provinces = fcol2.multiselect(
        "Provincias",
        options=available_provinces_for_years,
        default=current_provinces,
        placeholder="Selecciona una o varias provincias",
        key="selected_provinces_filter",
    )

    if not selected_provinces:
        st.warning("Debes seleccionar al menos una provincia.")
        st.stop()

metric_column = fcol3.selectbox(
    "Variable del mapa",
    options=METRIC_OPTIONS,
    key="metric_column",
)

num_provinces_visible = len(selected_provinces)

if num_provinces_visible == 0:
    st.warning("No hay provincias disponibles para los filtros actuales.")
    st.stop()

if num_provinces_visible <= 3:
    top_n = num_provinces_visible
    fcol4.info(f"Top-N fijado en {top_n}")
else:
    current_top_n = coerce_top_n(
        num_items=num_provinces_visible,
        current_value=st.session_state.get("top_n"),
    )

    top_n = fcol4.slider(
        "Top-N",
        min_value=3,
        max_value=num_provinces_visible,
        value=current_top_n,
        key="top_n",
    )

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

filtered_ranking = build_year_ranking(base_multi_year, int(base_multi_year["year"].max()))

filtered_ranking = apply_interactive_filters(
    ranking_df=filtered_ranking,
    selected_provinces=selected_provinces,
    top_n=top_n,
    show_top_only=show_top_only,
)

if filtered_ranking.empty:
    st.warning("No hay datos disponibles con la combinación actual de filtros.")
    st.stop()

province_options = filtered_ranking["provincia"].dropna().astype(str).tolist()
sync_focus_province(province_options)

selected_year_label = (
    str(selected_years[0]) if len(selected_years) == 1 else f"{min(selected_years)}–{max(selected_years)}"
)

render_kpi_summary(
    filtered_ranking=filtered_ranking,
    metric_column=metric_column,
    results=results,
    selected_year=max(selected_years),
    geo_mode=geo_mode,
)

forced_section = st.session_state.get("force_section")
if forced_section in SECTION_OPTIONS:
    widget_index = SECTION_OPTIONS.index(forced_section)
else:
    current_section = st.session_state.get("active_section", "Mapa y drill-down")
    widget_index = SECTION_OPTIONS.index(current_section)

selected_section = st.radio(
    "Sección",
    options=SECTION_OPTIONS,
    index=widget_index,
    horizontal=True,
    key="active_section_widget",
    label_visibility="collapsed",
)

st.session_state["active_section"] = selected_section
st.session_state["force_section"] = None
active_section = selected_section

if active_section == "Ranking":
    render_ranking_tab(filtered_ranking=filtered_ranking, top_n=top_n)

elif active_section == "Mapa y drill-down":
    if geo_mode == "Omitir mapa":
        st.info("Mapa omitido.")
    else:
        try:
            geo_source = load_geojson_source(
                geo_mode=geo_mode,
                geo_local_path=geo_local_path,
                uploaded_geo=uploaded_geo,
            )

            if geo_source is None:
                st.info("Sube un archivo GeoJSON.")
            else:
                selected_province = st.session_state.get("selected_province")

                map_result = build_map_cached(
                    df_map=filtered_ranking,
                    geo_source=geo_source,
                    color_col=metric_column,
                    title=f"Mapa nacional por provincia - {selected_year_label}",
                    selected_province=selected_province,
                )

                left_map_col, right_focus_col = st.columns([1.6, 1.0])

                with left_map_col:
                    st.markdown("### Vista nacional")

                    figure = map_result["figure"]
                    selected_points = plotly_events(
                        figure,
                        click_event=True,
                        select_event=False,
                        hover_event=False,
                        override_height=620,
                        key=(
                            f"plotly_click_map_{selected_year_label}_{metric_column}_"
                            f"{show_top_only}_{top_n}_{len(province_options)}"
                        ),
                    )

                    clicked_province = extract_selected_province_from_click(
                        selected_points=selected_points,
                        fallback_df=map_result["matched_df"],
                    )

                    if (
                        clicked_province in province_options
                        and should_accept_map_click(clicked_province)
                    ):
                        if set_selected_province(clicked_province):
                            request_section("Mapa y drill-down")
                            st.rerun()

                    if debug_map_click:
                        with st.expander("Debug del clic del mapa", expanded=False):
                            st.write("selected_points:", selected_points)
                            st.write("clicked_province:", clicked_province)
                            st.write("province_options:", province_options)
                            matched_preview = map_result["matched_df"].copy()
                            debug_cols = [
                                col
                                for col in [
                                    "provincia",
                                    "provincia_canon",
                                    "geo_match_name",
                                    metric_column,
                                ]
                                if col in matched_preview.columns
                            ]
                            if debug_cols:
                                st.dataframe(matched_preview[debug_cols], width=FULL_WIDTH)
                            else:
                                st.dataframe(matched_preview.head(10), width=FULL_WIDTH)

                    coverage, unmatched_count = build_geo_quality_summary(
                        base_ranking_df=filtered_ranking,
                        unmatched_provinces=map_result.get("unmatched_provinces", []),
                    )

                    q1, q2 = st.columns(2)
                    q1.metric("Cobertura geográfica", f"{coverage:.2f}%")
                    q2.metric("Provincias sin match", unmatched_count)

                    unmatched_provinces = map_result.get("unmatched_provinces", [])
                    if unmatched_provinces:
                        st.warning(
                            "Provincias sin correspondencia en el GeoJSON: "
                            f"{unmatched_provinces}"
                        )

                    st.caption(
                        "Haz clic sobre una provincia en el mapa nacional para actualizar la vista focalizada y dejarla marcada."
                    )

                with right_focus_col:
                    st.markdown("### Vista focalizada")

                    current_selected = st.session_state.get("selected_province")
                    if current_selected not in province_options and province_options:
                        current_selected = province_options[0]
                        st.session_state["selected_province"] = current_selected
                        st.session_state["selected_province_widget"] = current_selected

                    if (
                        province_options
                        and st.session_state.get("selected_province_widget") != current_selected
                    ):
                        st.session_state["selected_province_widget"] = current_selected

                    province_from_ui = st.selectbox(
                        "Provincia en foco",
                        options=province_options,
                        key="selected_province_widget",
                    )

                    if province_from_ui != current_selected:
                        if set_selected_province(province_from_ui):
                            request_section("Mapa y drill-down")
                            st.rerun()

                    clear_selection = st.button(
                        "Restablecer foco",
                        width=FULL_WIDTH,
                        key="clear_province_selection",
                    )
                    if clear_selection and province_options:
                        if set_selected_province(province_options[0]):
                            request_section("Mapa y drill-down")
                            st.rerun()

                    focus_df = filtered_ranking[
                        filtered_ranking["provincia"] == st.session_state["selected_province"]
                    ].copy()

                    if focus_df.empty and province_options:
                        fallback_province = province_options[0]
                        set_selected_province(fallback_province)
                        focus_df = filtered_ranking[
                            filtered_ranking["provincia"] == fallback_province
                        ].copy()

                    focus_map_result = build_map_cached(
                        df_map=focus_df,
                        geo_source=geo_source,
                        color_col=metric_column,
                        title=(
                            f"Provincia en foco - "
                            f"{st.session_state['selected_province']} ({selected_year_label})"
                        ),
                        selected_province=st.session_state["selected_province"],
                    )

                    st.plotly_chart(
                        focus_map_result["figure"],
                        width=FULL_WIDTH,
                    )

                    if not focus_df.empty:
                        province_row = focus_df.iloc[0]
                        st.metric("Provincia", province_row["provincia"])
                        st.metric("Categoría", str(province_row["categoria"]))
                        st.metric("Score actual", f"{float(province_row['score_riesgo']):.3f}")

                st.markdown("---")

                drill_year = int(max(selected_years))
                render_province_drilldown(
                    scored_df=scored_df[scored_df["year"].isin(selected_years)].copy(),
                    province_name=st.session_state["selected_province"],
                    selected_year=drill_year,
                )

        except Exception as exc:
            st.warning(f"No fue posible generar el mapa: {exc}")

elif active_section == "Métricas":
    render_metrics_tab(metricas_df=metricas_df)

elif active_section == "Explicabilidad":
    render_xai_tab(explain_df=explain_df)

elif active_section == "Narrativa":
    render_narrative_tab(narrative_text=results["narrative_text"])

elif active_section == "Exportación":
    render_export_section(
        filtered_ranking=filtered_ranking,
        metricas_df=metricas_df,
        scored_df=scored_df[scored_df["year"].isin(selected_years)].copy(),
        explain_df=explain_df,
        selected_provinces=selected_provinces,
        project_name=PROJECT_NAME,
        version=VERSION,
        selected_year=max(selected_years),
    )