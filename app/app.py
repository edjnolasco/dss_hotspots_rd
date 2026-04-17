from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent

PATH_CANDIDATES = [
    APP_DIR,       # permite importar ui.*
    PROJECT_ROOT,  # permite importar src.*
]

for candidate in PATH_CANDIDATES:
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

ROOT = PROJECT_ROOT

from src.section_router import SectionRenderContext, render_section

from src.data_sources import (  # noqa: E402
    OFFICIAL_PROVINCES_URL,
    fetch_remote_dataframe,
    load_local_dataframe,
    normalize_official_provinces,
    read_dataframe_from_bytes,
)
from src.debug_tools import (  # noqa: E402
    build_pipeline_debug_info,
    configure_logger,
    debug_flag,
    measure_runtime,
    render_dataframe_previews,
    render_debug_sidebar,
    render_pipeline_metrics,
    render_session_state_debug,
    render_trace_table,
    sync_debug_state,
)
from src.glossary import GLOSARIO_DSS  # noqa: E402
from src.interactive_filters import build_interactive_context  # noqa: E402
from src.pipeline import run_pipeline  # noqa: E402
from src.section_router import SectionRenderContext, render_section  # noqa: E402
from src.state import ensure_session_state, reset_selection_state  # noqa: E402
from src.version import AUTHOR, PROJECT_NAME, VERSION  # noqa: E402
from src.view_state import (  # noqa: E402
    VIEW_ABOUT,
    VIEW_HELP,
    VIEW_MAP,
    VIEW_RANKING,
    VIEW_SUMMARY,
    init_view_state,
    set_active_analysis_context,
    set_last_export_metadata,
    set_last_summary_text,
    set_selected_top_k,
    set_selected_view,
    set_selected_years,
    set_state,
)
from ui.ui_about import render_about_section  # noqa: E402
from ui.ui_help import render_help_section  # noqa: E402

SECTION_OPTIONS = [
    "Ranking",
    "Mapa y drill-down",
    "Métricas",
    "Explicabilidad",
    "Narrativa",
    "Exportación",
    "Ayuda e interpretación",
    "Acerca de",
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

ANALYTIC_SECTIONS = {
    "Ranking",
    "Mapa y drill-down",
    "Métricas",
    "Explicabilidad",
    "Narrativa",
    "Exportación",
}

SECTION_HEADERS = {
    "Ranking": (
        "Ranking priorizado",
        "Consulta la salida ordenada del DSS y su lectura operativa.",
    ),
    "Mapa y drill-down": (
        "Exploración geoespacial",
        "Analiza la distribución territorial y profundiza en una provincia.",
    ),
    "Métricas": (
        "Métricas de evaluación",
        "Examina el desempeño del modelo y la calidad de la priorización Top-K.",
    ),
    "Explicabilidad": (
        "Explicabilidad del modelo",
        "Identifica las variables con mayor peso en la generación del score.",
    ),
    "Narrativa": (
        "Narrativa automática",
        "Revisa la síntesis textual generada a partir de la salida del sistema.",
    ),
    "Exportación": (
        "Exportación de resultados",
        "Descarga la salida operativa del DSS en formatos reutilizables.",
    ),
    "Ayuda e interpretación": (
        "Ayuda e interpretación",
        "Consulta definiciones, glosario y claves de lectura del dashboard.",
    ),
    "Acerca de": (
        "Acerca del proyecto",
        "Información institucional, técnica y metodológica del sistema.",
    ),
}

SECTION_TO_VIEW = {
    "Mapa y drill-down": VIEW_MAP,
    "Ranking": VIEW_RANKING,
    "Narrativa": VIEW_SUMMARY,
    "Ayuda e interpretación": VIEW_HELP,
    "Acerca de": VIEW_ABOUT,
}

LOGGER = configure_logger()


def request_section(section_name: str) -> None:
    if section_name in SECTION_OPTIONS:
        st.session_state["active_section"] = section_name
        mapped_view = SECTION_TO_VIEW.get(section_name)
        if mapped_view:
            set_selected_view(mapped_view)


def ensure_app_state() -> None:
    ensure_session_state()
    sync_debug_state()

    init_view_state(
        overrides={
            "selected_view": VIEW_MAP,
            "selected_years": [],
            "selected_top_k": 10,
            "normalization_mode": "raw",
        }
    )

    defaults: dict[str, Any] = {
        "analysis_results": None,
        "source_label": None,
        "active_section": "Mapa y drill-down",
        "selected_province": None,
        "selected_years": st.session_state.get("selected_years", []),
        "selected_provinces_filter": [],
        "include_all_years": True,
        "include_all_provinces": True,
        "metric_column": "categoria",
        "source_mode": "Ruta local",
        "geo_mode": "Ruta local",
        "local_path": str(ROOT / "data" / "fallecimientos_provincias.csv"),
        "geo_local_path": str(ROOT / "data" / "rd_provinces.geojson"),
        "show_dss_trace": True,
        "show_top_only": False,
        "top_n": st.session_state.get("selected_top_k", None),
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

    active_section = st.session_state.get("active_section", "Mapa y drill-down")
    mapped_view = SECTION_TO_VIEW.get(active_section)
    if mapped_view:
        set_selected_view(mapped_view)

    if "selected_years" in st.session_state:
        set_selected_years(st.session_state.get("selected_years", []) or [])

    if "top_n" in st.session_state and st.session_state.get("top_n") is not None:
        try:
            set_selected_top_k(int(st.session_state["top_n"]))
        except (TypeError, ValueError):
            pass


def set_selected_province(new_value: str | None) -> bool:
    old_value = st.session_state.get("selected_province")
    if old_value == new_value:
        return False

    st.session_state["selected_province"] = new_value
    return True


def sync_focus_province(valid_options: list[str]) -> None:
    if not valid_options:
        st.session_state["selected_province"] = None
        return

    current = st.session_state.get("selected_province")
    if current not in valid_options:
        st.session_state["selected_province"] = valid_options[0]


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
    st.markdown("### Panel de control")

    with st.container(border=True):
        is_help_active = (
            st.session_state.get("active_section") == "Ayuda e interpretación"
        )
        is_about_active = st.session_state.get("active_section") == "Acerca de"

        shortcut_col1, shortcut_col2 = st.columns(2)

        with shortcut_col1:
            if is_help_active:
                st.button(
                    "Ayuda",
                    width="stretch",
                    key="open_help_section_button_active",
                    disabled=True,
                    type="primary",
                )
            elif st.button("Ayuda", width="stretch", key="open_help_section_button"):
                request_section("Ayuda e interpretación")
                st.rerun()

        with shortcut_col2:
            if is_about_active:
                st.button(
                    "Acerca de",
                    width="stretch",
                    key="open_about_section_button_active",
                    disabled=True,
                    type="primary",
                )
            elif st.button("Acerca de", width="stretch", key="open_about_section_button"):
                request_section("Acerca de")
                st.rerun()

    with st.container(border=True):
        st.markdown("**Datos**")

        source_mode = st.radio(
            "Fuente de datos",
            SOURCE_OPTIONS,
            key="source_mode",
            label_visibility="collapsed",
        )

        local_path = (
            st.text_input("Ruta local del dataset", key="local_path")
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

    with st.container(border=True):
        st.markdown("**Mapa**")

        geo_mode = st.radio(
            "Fuente del mapa",
            GEO_OPTIONS,
            key="geo_mode",
            label_visibility="collapsed",
        )

        geo_local_path = (
            st.text_input("Ruta local del GeoJSON", key="geo_local_path")
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

    render_debug_sidebar()

    with st.container(border=True):
        st.markdown("**Ejecución**")
        st.checkbox("Mostrar trazabilidad DSS", key="show_dss_trace")
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
            source_label = "Dataset local"

        with measure_runtime("pipeline", LOGGER) as runtime_info:
            pipeline_results = process_pipeline(normalized_df)

        pipeline_results["_debug"] = build_pipeline_debug_info(
            input_df=normalized_df,
            runtime_sec=runtime_info.elapsed,
            extra={"source_mode": source_mode, "geo_mode": geo_mode},
        )

        st.session_state["analysis_results"] = pipeline_results
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

        set_selected_years([])
        set_selected_top_k(10)
        set_state("selected_metric", "categoria")
        set_state("normalization_mode", "raw")
        set_last_summary_text(str(pipeline_results.get("narrative_text", "") or ""))
        set_last_export_metadata({})
        set_active_analysis_context({})

        request_section("Mapa y drill-down")
        st.success("Análisis ejecutado correctamente.")
        st.rerun()

    except Exception as exc:
        st.error("No fue posible completar el análisis.")
        st.exception(exc)

results = st.session_state.get("analysis_results")

current_section = st.session_state.get("active_section", "Mapa y drill-down")
if current_section not in SECTION_OPTIONS:
    current_section = "Mapa y drill-down"
    st.session_state["active_section"] = current_section
    set_selected_view(VIEW_MAP)

with st.container(border=True):
    st.markdown("**Navegación**")
    active_section = st.radio(
        "Sección",
        options=SECTION_OPTIONS,
        horizontal=True,
        key="active_section",
        label_visibility="collapsed",
    )

mapped_view = SECTION_TO_VIEW.get(active_section)
if mapped_view:
    set_selected_view(mapped_view)

if not results:
    if active_section == "Ayuda e interpretación":
        header_title, header_caption = SECTION_HEADERS[active_section]
        st.markdown(f"## {header_title}")
        st.caption(header_caption)
        render_help_section(GLOSARIO_DSS)
        st.stop()

    if active_section == "Acerca de":
        header_title, header_caption = SECTION_HEADERS[active_section]
        st.markdown(f"## {header_title}")
        st.caption(header_caption)
        render_about_section()
        st.stop()

    st.info("Configura la fuente de datos y ejecuta el análisis.")
    st.caption(
        "Las secciones de ayuda y de información general están disponibles sin ejecutar el análisis."
    )
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

render_pipeline_metrics(results.get("_debug", {}))
render_session_state_debug()

if debug_flag("debug_show_state"):
    st.write(st.session_state.get("source_label"))
else:
    st.caption(f"Fuente: {source_mode}")

scored_df = results["scored_df"].copy()
metricas_df = results["metricas_df"].copy()
explain_df = results["explain_df"].copy()

render_dataframe_previews(
    {
        "scored_df": scored_df,
        "metricas_df": metricas_df,
        "explain_df": explain_df,
    }
)

header_title, header_caption = SECTION_HEADERS.get(
    active_section,
    ("Sección", "Contenido disponible."),
)
st.markdown(f"## {header_title}")
st.caption(header_caption)

all_years = sorted(scored_df["year"].dropna().astype(int).unique().tolist())
default_year = int(results.get("latest_year", all_years[-1]))

interactive_ctx = build_interactive_context(
    active_section=active_section,
    analytic_sections=ANALYTIC_SECTIONS,
    scored_df=scored_df,
    all_years=all_years,
    default_year=default_year,
    metric_options=METRIC_OPTIONS,
    source_mode=source_mode,
    geo_mode=geo_mode,
)

selected_years = interactive_ctx.selected_years
selected_provinces = interactive_ctx.selected_provinces
metric_column = interactive_ctx.metric_column
top_n = interactive_ctx.top_n
show_top_only = interactive_ctx.show_top_only
filtered_ranking = interactive_ctx.filtered_ranking
province_options = interactive_ctx.province_options
selected_year_label = interactive_ctx.selected_year_label
available_provinces_for_years = interactive_ctx.available_provinces_for_years

render_trace_table(filtered_ranking)

if province_options:
    sync_focus_province(province_options)

render_section(
    SectionRenderContext(
        active_section=active_section,
        results=results,
        filtered_ranking=filtered_ranking,
        metricas_df=metricas_df,
        explain_df=explain_df,
        scored_df=scored_df,
        metric_column=metric_column,
        top_n=top_n,
        show_top_only=show_top_only,
        geo_mode=geo_mode,
        geo_local_path=geo_local_path,
        uploaded_geo=uploaded_geo,
        province_options=province_options,
        selected_years=selected_years,
        selected_year_label=selected_year_label,
        selected_provinces=selected_provinces,
        available_provinces_for_years=available_provinces_for_years,
        project_name=PROJECT_NAME,
        version=VERSION,
        glossary=GLOSARIO_DSS,
        source_label=st.session_state.get("source_label"),
        set_selected_province_fn=set_selected_province,
        build_rule_trace_text_fn=build_rule_trace_text,
        build_recommendation_text_fn=build_recommendation_text,
        show_dss_trace=st.session_state.get("show_dss_trace", True),
    )
)