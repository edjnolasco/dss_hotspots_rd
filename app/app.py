from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

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
from src.pipeline import run_pipeline  # noqa: E402
from src.state import ensure_session_state, reset_selection_state  # noqa: E402
from src.ui_about import render_about_section  # noqa: E402
from src.ui_help import render_help_section  # noqa: E402
from src.ui_sections import (  # noqa: E402
    apply_interactive_filters,
    build_year_ranking,
    render_export_section,
    render_metrics_tab,
    render_narrative_tab,
    render_ranking_tab,
    render_xai_tab,
)
from src.version import AUTHOR, PROJECT_NAME, VERSION  # noqa: E402
from src.ui_overview import render_overview_section  # noqa: E402
from src.ui_ranking_section import render_ranking_section  # noqa: E402
from src.ui_map_section import render_map_section  # noqa: E402

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

LOGGER = configure_logger()


def request_section(section_name: str) -> None:
    if section_name in SECTION_OPTIONS:
        st.session_state["active_section"] = section_name


def ensure_app_state() -> None:
    ensure_session_state()
    sync_debug_state()

    defaults: dict[str, Any] = {
        "analysis_results": None,
        "source_label": None,
        "active_section": "Mapa y drill-down",
        "selected_province": None,
        "selected_years": [],
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
        return min(9, num_items)
    return min(max(current_value, 3), num_items)


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
            else:
                if st.button(
                    "Ayuda",
                    width="stretch",
                    key="open_help_section_button",
                ):
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
            else:
                if st.button(
                    "Acerca de",
                    width="stretch",
                    key="open_about_section_button",
                ):
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

    with st.container(border=True):
        st.markdown("**Mapa**")

        geo_mode = st.radio(
            "Fuente del mapa",
            GEO_OPTIONS,
            key="geo_mode",
            label_visibility="collapsed",
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

    render_debug_sidebar()

    with st.container(border=True):
        st.markdown("**Ejecución**")

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
            source_label = "Dataset local"

        with measure_runtime("pipeline", LOGGER) as runtime_info:
            pipeline_results = process_pipeline(normalized_df)

        pipeline_results["_debug"] = build_pipeline_debug_info(
            input_df=normalized_df,
            runtime_sec=runtime_info.elapsed,
            extra={
                "source_mode": source_mode,
                "geo_mode": geo_mode,
            },
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

with st.container(border=True):
    st.markdown("**Navegación**")
    active_section = st.radio(
        "Sección",
        options=SECTION_OPTIONS,
        horizontal=True,
        key="active_section",
        label_visibility="collapsed",
    )

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

selected_years: list[int] = []
selected_provinces: list[str] = []
metric_column = st.session_state.get("metric_column", "categoria")
top_n = st.session_state.get("top_n", 0) or 0
show_top_only = st.session_state.get("show_top_only", False)
filtered_ranking = pd.DataFrame()
province_options: list[str] = []
selected_year_label = ""

if active_section in ANALYTIC_SECTIONS:
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

    render_trace_table(filtered_ranking)

    province_options = sorted(filtered_ranking["provincia"].dropna().astype(str).unique().tolist())
    sync_focus_province(province_options)

    selected_year_label = (
        str(selected_years[0])
        if len(selected_years) == 1
        else f"{min(selected_years)}–{max(selected_years)}"
    )
else:
    selected_years = all_years
    selected_provinces = []
    selected_year_label = str(all_years[-1]) if all_years else ""

if active_section == "Ranking":
    render_ranking_section(
        filtered_ranking=filtered_ranking,
        top_n=top_n,
        show_dss_trace=st.session_state.get("show_dss_trace", True),
    )
    render_ranking_tab(filtered_ranking=filtered_ranking, top_n=top_n)

elif active_section == "Mapa y drill-down":
    topk_clicked = render_overview_section(
        filtered_ranking=filtered_ranking,
        metric_column=metric_column,
        results=results,
        selected_year=max(selected_years),
        geo_mode=geo_mode,
        metricas_df=metricas_df,
        top_n=top_n,
        selected_year_label=selected_year_label,
        set_selected_province_fn=set_selected_province,
        show_dss_trace=st.session_state.get("show_dss_trace", True),
    )

    if topk_clicked:
        st.rerun()

    render_map_section(
        geo_mode=geo_mode,
        geo_local_path=geo_local_path,
        uploaded_geo=uploaded_geo,
        filtered_ranking=filtered_ranking,
        metric_column=metric_column,
        selected_year_label=selected_year_label,
        show_top_only=show_top_only,
        top_n=top_n,
        province_options=province_options,
        scored_df=scored_df,
        selected_years=selected_years,
        set_selected_province_fn=set_selected_province,
        build_rule_trace_text_fn=build_rule_trace_text,
        build_recommendation_text_fn=build_recommendation_text,
    )

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

elif active_section == "Ayuda e interpretación":
    render_help_section(GLOSARIO_DSS)

elif active_section == "Acerca de":
    render_about_section()