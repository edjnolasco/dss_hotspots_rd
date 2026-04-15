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
    if section_name in SECTION_OPTIONS:
        st.session_state["active_section"] = section_name


def ensure_app_state() -> None:
    ensure_session_state()

    defaults: dict[str, Any] = {
        "analysis_results": None,
        "source_label": None,
        "active_section": "Mapa y drill-down",
        "selected_province": None,
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
        "show_dss_trace": True,
        "show_top_only": False,
        "top_n": None,
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

    if st.session_state["active_section"] not in SECTION_OPTIONS:
        st.session_state["active_section"] = "Mapa y drill-down"


def set_selected_province(new_value: str | None) -> bool:
    old_value = st.session_state.get("selected_province")
    if old_value == new_value:
        return False

    st.session_state["selected_province"] = new_value
    st.session_state["province_focus_selectbox"] = new_value
    return True


def sync_focus_province(valid_options: list[str]) -> None:
    if not valid_options:
        st.session_state["selected_province"] = None
        return

    current = st.session_state.get("selected_province")
    if current not in valid_options:
        st.session_state["selected_province"] = valid_options[0]


def coerce_top_n(num_items: int, current_value: int | None) -> int:
    if num_items <= 0:
        return 0
    if num_items <= 3:
        return num_items
    if current_value is None:
        return min(10, num_items)
    return min(max(current_value, 3), num_items)


def get_metric_value(metricas_df: pd.DataFrame, metric_name: str) -> float | None:
    row = metricas_df.loc[metricas_df["metrica"] == metric_name, "valor"]
    if row.empty:
        return None
    try:
        return float(row.iloc[0])
    except Exception:
        return None


def build_rule_trace_text(row: pd.Series) -> str:
    regla = str(row.get("regla_aplicada", "")).strip()
    justificacion = str(row.get("justificacion_regla", "")).strip()

    if regla and justificacion:
        return f"{regla}. {justificacion}"

    if justificacion:
        return justificacion

    if regla:
        return regla

    categoria = str(row.get("categoria", "")).strip()
    score = float(pd.to_numeric(row.get("score_riesgo", 0.0), errors="coerce"))
    delta_abs = float(pd.to_numeric(row.get("delta_abs", 0.0), errors="coerce"))

    return (
        "No se encontró trazabilidad textual completa en la salida de reglas. "
        f"Resumen mínimo disponible: categoría={categoria}, score={score:.3f}, "
        f"delta_abs={delta_abs:.2f}."
    )


def build_recommendation_text(row: pd.Series) -> str:
    recomendacion = str(row.get("recomendacion", "")).strip()
    if recomendacion:
        return recomendacion

    provincia = str(row.get("provincia", "")).strip()
    categoria = str(row.get("categoria", "")).strip()

    if categoria == "Alta prioridad":
        return (
            f"Priorizar intervención inmediata en {provincia}, con seguimiento intensivo "
            "y asignación preferente de recursos preventivos."
        )

    if categoria == "Vigilancia preventiva":
        return (
            f"Mantener vigilancia preventiva en {provincia}, monitorear la tendencia "
            "y preparar escalamiento si persiste el deterioro."
        )

    return f"Mantener seguimiento rutinario en {provincia} y reevaluar en el próximo ciclo."

def resolve_clicked_province_from_plotly_event(
    selected_points: list[dict[str, Any]] | None,
    figure: Any,
    matched_df: pd.DataFrame,
) -> str | None:
    if not selected_points:
        return None

    point = selected_points[0] or {}
    curve_number = point.get("curveNumber")
    point_index = point.get("pointIndex")

    if not isinstance(curve_number, int) or not isinstance(point_index, int):
        return None

    try:
        trace = figure.data[curve_number]
    except Exception:
        return None

    customdata = getattr(trace, "customdata", None)
    if customdata is not None:
        try:
            item = customdata[point_index]
            if isinstance(item, str):
                candidate = item.strip()
                if candidate:
                    return candidate
            if isinstance(item, (list, tuple)) and len(item) > 0:
                candidate = str(item[0]).strip()
                if candidate:
                    return candidate
        except Exception:
            pass

    locations = getattr(trace, "locations", None)
    if locations is not None:
        try:
            geo_name = str(locations[point_index]).strip()
            if geo_name and not matched_df.empty:
                match = matched_df.loc[
                    matched_df["geo_match_name"].astype(str).str.strip() == geo_name,
                    "provincia",
                ]
                if not match.empty:
                    return str(match.iloc[0]).strip()
        except Exception:
            pass

    return None

def render_decision_engine_summary(
    filtered_ranking: pd.DataFrame,
    metricas_df: pd.DataFrame,
    top_n: int,
    selected_year_label: str,
) -> None:
    st.markdown("### Motor DSS visible")

    c1, c2, c3, c4 = st.columns(4)
    c1.info("1. Datos históricos por provincia")
    c2.info("2. Modelo predictivo → score de riesgo")
    c3.info("3. Reglas DSS → categoría operativa")
    c4.info("4. Ranking Top-K → priorización")

    top_row = filtered_ranking.iloc[0]
    hit3 = get_metric_value(metricas_df, "hitrate_at_3")
    hit5 = get_metric_value(metricas_df, "hitrate_at_5")
    precision3 = get_metric_value(metricas_df, "precision_at_3")

    score_text = f"{float(top_row['score_riesgo']):.3f}"
    categoria_text = str(top_row["categoria"])
    provincia_text = str(top_row["provincia"])
    hit3_text = "N/D" if hit3 is None else f"{hit3:.3f}"
    hit5_text = "N/D" if hit5 is None else f"{hit5:.3f}"
    precision3_text = "N/D" if precision3 is None else f"{precision3:.3f}"

    st.caption(
        f"Período analizado: {selected_year_label}. "
        f"La provincia actualmente priorizada en la salida del DSS es {provincia_text}, "
        f"con score {score_text} y categoría '{categoria_text}'. "
        f"En la evaluación de priorización, HitRate@3 = {hit3_text}, HitRate@5 = {hit5_text} "
        f"y Precision@3 = {precision3_text}. El ranking visible usa Top-{top_n} según los filtros activos."
    )


def render_topk_preview(filtered_ranking: pd.DataFrame, top_n: int) -> bool:
    st.markdown("### Top-K priorizado")

    preview_n = min(top_n, len(filtered_ranking))
    preview_df = filtered_ranking.head(preview_n).copy()

    if preview_df.empty:
        st.info("No hay provincias disponibles para mostrar en el Top-K.")
        return False

    color_map = {
        "Alta prioridad": {
            "bg": "rgba(231, 76, 60, 0.10)",
            "border": "#e74c3c",
            "badge": "🔴 Alta prioridad",
        },
        "Vigilancia preventiva": {
            "bg": "rgba(243, 156, 18, 0.12)",
            "border": "#f39c12",
            "badge": "🟡 Vigilancia preventiva",
        },
        "Seguimiento rutinario": {
            "bg": "rgba(46, 204, 113, 0.10)",
            "border": "#2ecc71",
            "badge": "🟢 Seguimiento rutinario",
        },
        "N/D": {
            "bg": "rgba(189, 195, 199, 0.14)",
            "border": "#bdc3c7",
            "badge": "⚪ N/D",
        },
    }

    num_cards = len(preview_df)
    num_cols = 1 if num_cards == 1 else 2 if num_cards <= 4 else 3

    rows = [
        preview_df.iloc[i:i + num_cols]
        for i in range(0, num_cards, num_cols)
    ]

    clicked_any = False

    for row_idx, row_df in enumerate(rows):
        cols = st.columns(num_cols)

        for col_idx, (col, (_, row)) in enumerate(zip(cols, row_df.iterrows())):
            provincia = str(row.get("provincia", "N/D")).strip()
            categoria = str(row.get("categoria", "N/D")).strip() or "N/D"
            score = float(pd.to_numeric(row.get("score_riesgo", 0.0), errors="coerce"))
            pred_next = float(
                pd.to_numeric(row.get("pred_fallecidos_next", 0.0), errors="coerce")
            )
            delta_abs = float(pd.to_numeric(row.get("delta_abs", 0.0), errors="coerce"))
            posicion = int(pd.to_numeric(row.get("ranking_posicion", 0), errors="coerce"))

            rule_text = str(row.get("regla_aplicada", "")).strip()
            justification_text = str(row.get("justificacion_regla", "")).strip()

            current_focus = str(st.session_state.get("selected_province", "")).strip()
            is_active = current_focus == provincia
            palette = color_map.get(categoria, color_map["N/D"])
            
            palette = color_map.get(categoria, color_map["N/D"])

            detail_parts = [
                f"<b>Score:</b> {score:.3f}",
                f"<b>Predicción:</b> {pred_next:.2f}",
                f"<b>Δ abs.:</b> {delta_abs:+.2f}",
            ]

            if rule_text:
                detail_parts.append(f"<b>Regla:</b> {rule_text}")

            if justification_text:
                detail_parts.append(f"<b>Justificación:</b> {justification_text}")

            detail_html = "<br>".join(detail_parts)

            with col:
                st.markdown(
                    f"""
                    <div style="
                        background:{palette['bg']};
                        border-left: 6px solid {palette['border']};
                        border-radius: 12px;
                        padding: 14px 16px;
                        margin-bottom: 8px;
                        min-height: 220px;
                        box-shadow: {'0 0 0 3px rgba(44, 62, 80, 0.22), 0 8px 22px rgba(0, 0, 0, 0.08)' if is_active else 'none'};
                        transform: {'translateY(-1px)' if is_active else 'none'};
                    ">
                        <div style="
                            display:flex;
                            justify-content:space-between;
                            align-items:flex-start;
                            gap:12px;
                            margin-bottom:8px;
                        ">
                            <div style="font-weight:700; font-size:1.05rem;">
                                #{posicion} · {provincia}
                            </div>
                            <div style="
                                font-size:0.9rem;
                                font-weight:600;
                                color:#2c3e50;
                                white-space:nowrap;
                                text-align:right;
                            ">
                                {palette['badge']}<br>
                                <span style="
                                    font-size:0.78rem;
                                    color:{'#2c3e50' if is_active else '#7f8c8d'};
                                    font-weight:{'700' if is_active else '500'};
                                ">
                                    {'📍 En foco' if is_active else '&nbsp;'}
                                </span>
                            </div>
                        </div>
                        <div style="font-size:0.95rem; line-height:1.5;">
                            {detail_html}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                button_label = "Provincia en foco" if is_active else f"Enfocar {provincia}"

                clicked = st.button(
                    button_label,
                    key=f"topk_card_select_{row_idx}_{col_idx}_{provincia}",
                    width="stretch",
                    disabled=is_active,
                )

                if clicked:
                    if set_selected_province(provincia):
                        clicked_any = True

    return clicked_any

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

    st.header("Salida DSS")
    st.checkbox(
        "Mostrar trazabilidad DSS",
        key="show_dss_trace",
    )

    run_clicked = st.button(
        "Ejecutar análisis",
        type="primary",
        width="stretch",
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
        st.session_state["selected_years"] = []
        st.session_state["selected_provinces_filter"] = []
        st.session_state["include_all_years"] = True
        st.session_state["include_all_provinces"] = True
        st.session_state["metric_column"] = "categoria"
        st.session_state["show_top_only"] = False
        st.session_state["top_n"] = None

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
    st.session_state["top_n"] = top_n
    fcol4.info(f"Top-N fijado en {top_n}")
else:
    current_top_n = coerce_top_n(
        num_items=num_provinces_visible,
        current_value=st.session_state.get("top_n"),
    )
    st.session_state["top_n"] = current_top_n

    top_n = fcol4.slider(
        "Top-N",
        min_value=3,
        max_value=num_provinces_visible,
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

province_options = sorted(filtered_ranking["provincia"].dropna().astype(str).unique().tolist())
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

if st.session_state.get("show_dss_trace", True):
    render_decision_engine_summary(
        filtered_ranking=filtered_ranking,
        metricas_df=metricas_df,
        top_n=top_n,
        selected_year_label=selected_year_label,
    )
    topk_clicked = render_topk_preview(
    filtered_ranking=filtered_ranking,
    top_n=top_n,
)

if topk_clicked:
    st.rerun()

current_section = st.session_state.get("active_section", "Mapa y drill-down")
if current_section not in SECTION_OPTIONS:
    current_section = "Mapa y drill-down"
    st.session_state["active_section"] = current_section

active_section = st.radio(
    "Sección",
    options=SECTION_OPTIONS,
    horizontal=True,
    key="active_section",
    label_visibility="collapsed",
)

if active_section == "Ranking":
    if st.session_state.get("show_dss_trace", True):
        st.markdown("### Lectura operativa del ranking")
        st.caption(
            "El ranking no representa solo una ordenación visual. "
            "Expresa la salida final del DSS después de combinar el score predictivo "
            "con la lógica de reglas explícitas."
        )
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

                left_map_col, right_focus_col = st.columns([1.45, 1.15])

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

                    clicked_province = resolve_clicked_province_from_plotly_event(
                        selected_points=selected_points,
                        figure=figure,
                        matched_df=map_result["matched_df"],
                    )

                    if clicked_province:
                        clicked_province = str(clicked_province).strip()

                    normalized_options = {str(p).strip(): p for p in province_options}

                    if clicked_province in normalized_options:
                        clicked_province = normalized_options[clicked_province]
                    else:
                        clicked_province = None

                    if debug_map_click:
                        st.write("selected_points:", selected_points)
                        st.write("clicked_province:", clicked_province)

                    if clicked_province and should_accept_map_click(clicked_province):
                        current_selected = st.session_state.get("selected_province")
                        if str(current_selected).strip() != str(clicked_province).strip():
                            if set_selected_province(clicked_province):
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
                                st.dataframe(
                                    matched_preview[debug_cols],
                                    width="stretch",
                                )
                            else:
                                st.dataframe(
                                    matched_preview.head(10),
                                    width="stretch",
                                )

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

                    if st.session_state.get("province_focus_selectbox") != current_selected:
                        st.session_state["province_focus_selectbox"] = current_selected

                    province_from_ui = st.selectbox(
                        "Provincia en foco",
                        options=province_options,
                        key="province_focus_selectbox",
                    )

                    if province_from_ui != st.session_state.get("selected_province"):
                        if set_selected_province(province_from_ui):
                            st.rerun()

                    clear_selection = st.button(
                        "Restablecer foco",
                        width="stretch",
                        key="clear_province_selection",
                    )
                    if clear_selection and province_options:
                        default_focus = province_options[0]
                        if set_selected_province(default_focus):
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
                            "Provincia en foco - "
                            f"{st.session_state['selected_province']} ({selected_year_label})"
                        ),
                        selected_province=st.session_state["selected_province"],
                    )

                    st.plotly_chart(
                        focus_map_result["figure"],
                        width="stretch",
                    )

                    if not focus_df.empty:
                        province_row = focus_df.iloc[0]

                        categoria = str(province_row.get("categoria", "N/D")).strip() or "N/D"

                        badge_map = {
                            "Alta prioridad": {
                                "bg": "rgba(231, 76, 60, 0.14)",
                                "border": "#e74c3c",
                                "text": "#ffb3ad",
                                "label": "🔴 Alta prioridad",
                            },
                            "Vigilancia preventiva": {
                                "bg": "rgba(243, 156, 18, 0.16)",
                                "border": "#f39c12",
                                "text": "#ffd27a",
                                "label": "🟡 Vigilancia preventiva",
                            },
                            "Seguimiento rutinario": {
                                "bg": "rgba(46, 204, 113, 0.14)",
                                "border": "#2ecc71",
                                "text": "#9df0b8",
                                "label": "🟢 Seguimiento rutinario",
                            },
                            "N/D": {
                                "bg": "rgba(189, 195, 199, 0.14)",
                                "border": "#bdc3c7",
                                "text": "#dfe6e9",
                                "label": "⚪ N/D",
                            },
                        }

                        badge = badge_map.get(categoria, badge_map["N/D"])

                        st.markdown(
                            f"""
                            <div style="margin-bottom: 10px;">
                                <div style="font-size: 2rem; font-weight: 700; line-height: 1.1; margin-bottom: 10px;">
                                    {province_row['provincia']}
                                </div>
                                <div style="
                                    display: inline-block;
                                    padding: 8px 12px;
                                    border-radius: 999px;
                                    border: 1px solid {badge['border']};
                                    background: {badge['bg']};
                                    color: {badge['text']};
                                    font-weight: 600;
                                    font-size: 0.95rem;
                                ">
                                    {badge['label']}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        m1, m2 = st.columns(2)
                        m3, m4 = st.columns(2)

                        m1.metric("Score actual", f"{float(province_row['score_riesgo']):.3f}")
                        m2.metric(
                            "Predicción próxima",
                            f"{float(province_row['pred_fallecidos_next']):.2f}",
                        )

                        delta_abs = float(pd.to_numeric(province_row.get("delta_abs", 0.0), errors="coerce"))
                        m3.metric("Δ abs.", f"{delta_abs:+.2f}")

                        ranking_pos = province_row.get("ranking_posicion", None)
                        ranking_text = "N/D" if pd.isna(ranking_pos) else f"#{int(ranking_pos)}"
                        m4.metric("Posición", ranking_text)

                        with st.container(border=True):
                            st.markdown("**Trazabilidad de la decisión**")

                            regla_text = str(province_row.get("regla_aplicada", "")).strip()
                            just_text = str(province_row.get("justificacion_regla", "")).strip()
                            rec_text = str(province_row.get("recomendacion", "")).strip()

                            if regla_text:
                                st.write(f"**Regla aplicada:** {regla_text}")

                            if just_text:
                                st.write(f"**Justificación:** {just_text}")
                            else:
                                st.write(build_rule_trace_text(province_row))

                            if rec_text:
                                st.write(f"**Recomendación:** {rec_text}")
                            else:
                                st.write(build_recommendation_text(province_row))

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
    if st.session_state.get("show_dss_trace", True):
        st.caption(
            "Estas métricas no solo evalúan error del modelo, sino también la calidad de la priorización "
            "Top-K producida por el DSS."
        )
    render_metrics_tab(metricas_df=metricas_df)

elif active_section == "Explicabilidad":
    if st.session_state.get("show_dss_trace", True):
        st.caption(
            "La explicabilidad muestra qué variables pesan más en la generación del score, "
            "mientras que la decisión operativa final se obtiene después mediante reglas."
        )
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