from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
<<<<<<< HEAD
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
=======
import streamlit as st
from streamlit_plotly_events import plotly_events

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR if (APP_DIR / "src").exists() else APP_DIR.parent
>>>>>>> ad52dd7 (feat: improve DSS UI interaction, map rendering and category normalization)

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.data_sources import (  # noqa: E402
    OFFICIAL_PROVINCES_URL,
    fetch_remote_dataframe,
    load_local_dataframe,
    normalize_official_provinces,
    read_dataframe_from_bytes,
)
<<<<<<< HEAD
from src.exporter import to_csv_bytes, to_excel_bytes  # noqa: E402
from src.map_utils import build_rd_choropleth_from_source  # noqa: E402
from src.pipeline import run_pipeline  # noqa: E402
from src.version import AUTHOR, PROJECT_NAME, VERSION  # noqa: E402


# ============================================================
# CONFIGURACIÓN STREAMLIT
# ============================================================
=======
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


>>>>>>> ad52dd7 (feat: improve DSS UI interaction, map rendering and category normalization)
st.set_page_config(page_title=f"{PROJECT_NAME} {VERSION}", layout="wide")
st.title(f"{PROJECT_NAME} {VERSION}")
st.caption(f"Autor: {AUTHOR}")

ensure_app_state()

<<<<<<< HEAD
# ============================================================
# ESTADO DE SESIÓN
# ============================================================
for key, default in {
    "analysis_results": None,
    "source_label": None,
    "selected_province": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ============================================================
# UTILIDADES
# ============================================================
def kpi_dashboard(ranking_df: pd.DataFrame, metric_column: str) -> go.Figure:
    """Construye el tablero KPI superior a partir del ranking filtrado."""
    if ranking_df.empty:
        fig = go.Figure()
        fig.update_layout(height=120, margin=dict(l=20, r=20, t=10, b=10))
        return fig

    top1 = ranking_df.iloc[0]
    fig = go.Figure()

    fig.add_trace(
        go.Indicator(
            mode="number",
            value=1,
            title={"text": f"Provincia líder<br>{top1['provincia']}"},
            domain={"row": 0, "column": 0},
        )
    )
    fig.add_trace(
        go.Indicator(
            mode="number",
            value=float(top1["score_riesgo"]),
            number={"valueformat": ".3f"},
            title={"text": "Score líder"},
            domain={"row": 0, "column": 1},
        )
    )
    fig.add_trace(
        go.Indicator(
            mode="number",
            value=float(top1["pred_fallecidos_next"]),
            number={"valueformat": ".2f"},
            title={"text": "Predicción líder"},
            domain={"row": 0, "column": 2},
        )
    )
    fig.add_trace(
        go.Indicator(
            mode="number",
            value=float(top1[metric_column]),
            number={"valueformat": ".2f" if metric_column != "fallecidos_actuales" else ".0f"},
            title={"text": metric_column.replace("_", " ").title()},
            domain={"row": 0, "column": 3},
        )
    )
    fig.update_layout(
        grid={"rows": 1, "columns": 4, "pattern": "independent"},
        height=220,
        margin=dict(l=20, r=20, t=10, b=10),
    )
    return fig


def build_year_ranking(scored_df: pd.DataFrame, selected_year: int) -> pd.DataFrame:
    """Agrega el scoring al nivel provincia para el año seleccionado."""
    filtered = scored_df[scored_df["year"] == selected_year].copy()
    if filtered.empty:
        return pd.DataFrame(
            columns=[
                "provincia",
                "pred_fallecidos_next",
                "score_riesgo",
                "categoria",
                "fallecidos_actuales",
                "delta_abs",
                "delta_pct",
            ]
        )

    ranking = (
        filtered.groupby("provincia", as_index=False)
        .agg(
            pred_fallecidos_next=("pred_fallecidos_next", "mean"),
            score_riesgo=("score_riesgo", "mean"),
            categoria=("categoria", "first"),
            fallecidos_actuales=("fallecidos", "sum"),
        )
        .sort_values("score_riesgo", ascending=False)
        .reset_index(drop=True)
    )

    ranking["delta_abs"] = ranking["pred_fallecidos_next"] - ranking["fallecidos_actuales"]
    ranking["delta_pct"] = (
        ranking["delta_abs"] / ranking["fallecidos_actuales"].replace(0, pd.NA)
    ) * 100.0
    ranking["delta_pct"] = ranking["delta_pct"].fillna(0.0)
    ranking["ranking_posicion"] = range(1, len(ranking) + 1)
    return ranking


def apply_interactive_filters(
    ranking_df: pd.DataFrame,
    selected_provinces: list[str],
    top_n: int,
    show_top_only: bool,
) -> pd.DataFrame:
    """Aplica filtros de provincias y Top-N a la vista agregada."""
    filtered = ranking_df.copy()

    if selected_provinces:
        filtered = filtered[filtered["provincia"].isin(selected_provinces)].copy()

    if show_top_only:
        filtered = filtered.head(top_n).copy()

    return filtered.reset_index(drop=True)


def build_geo_quality_summary(
    base_ranking_df: pd.DataFrame,
    unmatched_provinces: list[str],
) -> tuple[float, int]:
    total = int(base_ranking_df["provincia"].nunique())
    unmatched = len(unmatched_provinces)
    coverage = 0.0 if total == 0 else ((total - unmatched) / total) * 100.0
    return coverage, unmatched


def extract_selected_province(event: Any, fallback_df: pd.DataFrame) -> str | None:
    """
    Intenta identificar la provincia seleccionada desde el evento Plotly.
    Soporta los formatos más comunes devueltos por st.plotly_chart(..., on_select="rerun").
    """
    if not event:
        return None

    selection = event.get("selection") if isinstance(event, dict) else getattr(event, "selection", None)
    if not selection:
        return None

    points = selection.get("points", [])
    if not points:
        return None

    point = points[0]

    customdata = point.get("customdata")
    if isinstance(customdata, (list, tuple)) and len(customdata) > 0:
        first = customdata[0]
        if isinstance(first, str) and first.strip():
            return first

    for key in ("location", "hovertext", "label", "x", "text"):
        value = point.get(key)
        if isinstance(value, str) and value.strip():
            return value

    point_index = point.get("point_index")
    if isinstance(point_index, int) and 0 <= point_index < len(fallback_df):
        return str(fallback_df.iloc[point_index]["provincia"])

    return None


def build_province_detail_row(
    province_history: pd.DataFrame,
    selected_year: int,
) -> dict[str, Any] | None:
    if province_history.empty:
        return None

    current = province_history[province_history["year"] == selected_year].copy()
    if current.empty:
        return None

    current_row = current.sort_values("year").iloc[-1]
    prev = province_history[province_history["year"] < selected_year].sort_values("year")

    prev_value = float(prev.iloc[-1]["fallecidos"]) if not prev.empty else None
    current_value = float(current_row["fallecidos"])

    if prev_value is None:
        yoy_abs = None
        yoy_pct = None
    else:
        yoy_abs = current_value - prev_value
        yoy_pct = 0.0 if prev_value == 0 else (yoy_abs / prev_value) * 100.0

    explanation_parts: list[str] = []

    if float(current_row["score_riesgo"]) >= 0.75:
        explanation_parts.append("score de riesgo elevado")
    elif float(current_row["score_riesgo"]) >= 0.50:
        explanation_parts.append("score de riesgo medio-alto")
    else:
        explanation_parts.append("score de riesgo moderado")

    if yoy_abs is not None:
        if yoy_abs > 0:
            explanation_parts.append("incremento respecto al año previo")
        elif yoy_abs < 0:
            explanation_parts.append("reducción respecto al año previo")
        else:
            explanation_parts.append("comportamiento estable frente al año previo")

    explanation_parts.append(f"clasificación actual: {current_row['categoria']}")

    return {
        "provincia": current_row["provincia"],
        "year": int(current_row["year"]),
        "fallecidos": current_value,
        "pred_fallecidos_next": float(current_row["pred_fallecidos_next"]),
        "score_riesgo": float(current_row["score_riesgo"]),
        "categoria": str(current_row["categoria"]),
        "yoy_abs": yoy_abs,
        "yoy_pct": yoy_pct,
        "explicacion": " | ".join(explanation_parts),
    }


def render_province_drilldown(scored_df: pd.DataFrame, province_name: str, selected_year: int) -> None:
    """Renderiza el panel drill-down para la provincia seleccionada."""
    if not province_name:
        st.info("Selecciona una provincia en el mapa o en el selector para ver el drill-down.")
        return

    province_history = (
        scored_df[scored_df["provincia"] == province_name]
        .sort_values("year")
        .reset_index(drop=True)
    )

    detail = build_province_detail_row(province_history, selected_year)
    if detail is None:
        st.info("No hay detalle disponible para la provincia seleccionada en el año filtrado.")
        return

    st.subheader(f"Detalle provincial: {detail['provincia']}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fallecidos", f"{detail['fallecidos']:.0f}")
    c2.metric("Predicción siguiente", f"{detail['pred_fallecidos_next']:.2f}")
    c3.metric("Score de riesgo", f"{detail['score_riesgo']:.3f}")
    c4.metric(
        "Variación interanual",
        "N/D" if detail["yoy_pct"] is None else f"{detail['yoy_pct']:.1f}%",
        None if detail["yoy_abs"] is None else f"{detail['yoy_abs']:+.0f}",
    )

    st.caption(detail["explicacion"])

    fig_hist = px.line(
        province_history,
        x="year",
        y="fallecidos",
        markers=True,
        title=f"Serie histórica de fallecidos - {detail['provincia']}",
    )
    fig_hist.update_layout(height=360, xaxis_title="Año", yaxis_title="Fallecidos")
    st.plotly_chart(fig_hist, use_container_width=True)

    detail_table = province_history[
        ["year", "fallecidos", "pred_fallecidos_next", "score_riesgo", "categoria"]
    ].copy()
    st.dataframe(detail_table, use_container_width=True)


# ============================================================
# SIDEBAR
# ============================================================
=======

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


>>>>>>> ad52dd7 (feat: improve DSS UI interaction, map rendering and category normalization)
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
<<<<<<< HEAD
        ["Ruta local", "Subir GeoJSON", "Omitir mapa"],
        index=0,
=======
        GEO_OPTIONS,
        key="geo_mode",
>>>>>>> ad52dd7 (feat: improve DSS UI interaction, map rendering and category normalization)
    )

    geo_local_path = (
        st.text_input(
            "Ruta local del GeoJSON",
<<<<<<< HEAD
            value=str(ROOT / "data" / "rd_provinces.geojson"),
=======
            key="geo_local_path",
>>>>>>> ad52dd7 (feat: improve DSS UI interaction, map rendering and category normalization)
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

<<<<<<< HEAD

# ============================================================
# CACHÉ
# ============================================================
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


# ============================================================
# CARGA Y ANÁLISIS
# ============================================================
=======
    run_clicked = st.button(
        "Ejecutar análisis",
        type="primary",
        width=FULL_WIDTH,
        key="run_analysis_button",
    )

>>>>>>> ad52dd7 (feat: improve DSS UI interaction, map rendering and category normalization)
if run_clicked:
    try:
        if source_mode == "Fuente oficial DIGESETT":
            try:
                normalized_df = load_data_remote()
                source_label = "Fuente oficial DIGESETT"
            except Exception:
                st.error(
<<<<<<< HEAD
                    "La fuente oficial DIGESETT rechazó la descarga remota (HTTP 403 o acceso restringido). "
                    "Usa la opción 'Subir CSV/XLSX' con el archivo oficial descargado manualmente."
=======
                    "La fuente oficial DIGESETT rechazó la descarga remota "
                    "(HTTP 403 o acceso restringido). Usa la opción "
                    "'Subir CSV/XLSX' con el archivo oficial descargado manualmente."
>>>>>>> ad52dd7 (feat: improve DSS UI interaction, map rendering and category normalization)
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
<<<<<<< HEAD
        st.session_state["selected_province"] = None
        st.success("Análisis ejecutado correctamente.")

    except Exception as exc:
        st.error("No fue posible completar el análisis.")
        st.exception(exc)


# ============================================================
# APP PRINCIPAL
# ============================================================
results = st.session_state.get("analysis_results")

=======

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

>>>>>>> ad52dd7 (feat: improve DSS UI interaction, map rendering and category normalization)
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

<<<<<<< HEAD
years = sorted(scored_df["year"].dropna().astype(int).unique().tolist())
default_year = int(results.get("latest_year", years[-1]))

st.markdown("## Exploración interactiva")

fcol1, fcol2, fcol3, fcol4 = st.columns([1.0, 1.4, 1.0, 1.0])

selected_year = fcol1.selectbox("Año", years, index=years.index(default_year))
available_provinces_for_year = sorted(
    scored_df[scored_df["year"] == selected_year]["provincia"].dropna().unique().tolist()
)
selected_provinces = fcol2.multiselect(
    "Provincias",
    options=available_provinces_for_year,
    default=[],
    placeholder="Todas las provincias",
)
metric_column = fcol3.selectbox(
    "Variable del mapa",
    options=["score_riesgo", "fallecidos_actuales", "pred_fallecidos_next", "delta_pct"],
    index=0,
)
top_n = fcol4.slider(
    "Top-N",
    min_value=3,
    max_value=max(3, len(available_provinces_for_year)),
    value=min(10, max(3, len(available_provinces_for_year))),
)

show_top_only = st.checkbox("Mostrar solo Top-N en ranking y mapa", value=False)

base_year_ranking = build_year_ranking(scored_df, selected_year)
filtered_ranking = apply_interactive_filters(
    base_year_ranking,
=======
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
>>>>>>> ad52dd7 (feat: improve DSS UI interaction, map rendering and category normalization)
    selected_provinces=selected_provinces,
    top_n=top_n,
    show_top_only=show_top_only,
)

if filtered_ranking.empty:
    st.warning("No hay datos disponibles con la combinación actual de filtros.")
    st.stop()

<<<<<<< HEAD
summary_left, summary_right = st.columns([2, 1])

with summary_left:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Año de análisis", selected_year)
    c2.metric("Provincias visibles", int(filtered_ranking["provincia"].nunique()))
    c3.metric("MAE", f"{results['mae']:.3f}" if results["mae"] is not None else "N/D")
    c4.metric("R²", f"{results['r2']:.3f}" if results["r2"] is not None else "N/D")

    st.plotly_chart(kpi_dashboard(filtered_ranking, metric_column), use_container_width=True)

with summary_right:
    st.markdown("### Estado del sistema")
    st.success("Dataset cargado")
    st.success("Pipeline ejecutado")
    st.success("Ranking generado")
    if geo_mode == "Omitir mapa":
        st.info("Mapa omitido por configuración")
    else:
        st.info("Mapa habilitado")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Ranking", "Mapa y drill-down", "Métricas", "Explicabilidad", "Narrativa", "Exportación"]
)

with tab1:
    st.dataframe(filtered_ranking, use_container_width=True)

    fig_rank = px.bar(
        filtered_ranking.head(min(top_n, len(filtered_ranking))),
        x="provincia",
        y="score_riesgo",
        color="categoria",
        hover_data=["pred_fallecidos_next", "fallecidos_actuales", "delta_pct"],
        title="Ranking de provincias priorizadas",
    )
    fig_rank.update_layout(height=500, xaxis_title="", yaxis_title="Score de riesgo")
    st.plotly_chart(fig_rank, use_container_width=True)

    fig_scatter = px.scatter(
        filtered_ranking,
        x="fallecidos_actuales",
        y="pred_fallecidos_next",
        size="score_riesgo",
        color="categoria",
        hover_name="provincia",
        title="Relación entre fallecidos actuales y predicción siguiente",
    )
    fig_scatter.update_layout(height=500)
    st.plotly_chart(fig_scatter, use_container_width=True)

with tab2:
    selected_province = st.session_state.get("selected_province")

=======
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
>>>>>>> ad52dd7 (feat: improve DSS UI interaction, map rendering and category normalization)
    if geo_mode == "Omitir mapa":
        st.info("Mapa omitido.")
    else:
        try:
<<<<<<< HEAD
            if geo_mode == "Ruta local":
                geo_source = geo_local_path
            else:
                if uploaded_geo is None:
                    st.info("Sube un archivo GeoJSON.")
                    geo_source = None
                else:
                    geo_source = uploaded_geo.getvalue().decode("utf-8")

            if geo_source is not None:
                province_options = filtered_ranking["provincia"].tolist()
                if selected_province not in province_options:
                    selected_province = None
                    st.session_state["selected_province"] = None
=======
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
>>>>>>> ad52dd7 (feat: improve DSS UI interaction, map rendering and category normalization)

                left_map_col, right_focus_col = st.columns([1.6, 1.0])

                with left_map_col:
                    st.markdown("### Vista nacional")

<<<<<<< HEAD
                    map_result = build_rd_choropleth_from_source(
                        filtered_ranking,
                        geo_source,
                        province_column="provincia",
                        color_column=metric_column,
                        title=f"Mapa nacional por provincia - {selected_year}",
                    )

                    figure = map_result["figure"]
                    figure.update_layout(clickmode="event+select")

                    event = st.plotly_chart(
                        figure,
                        use_container_width=True,
                        on_select="rerun",
                        key=f"rd_map_{selected_year}_{metric_column}_{show_top_only}_{top_n}",
                    )

                    clicked_province = extract_selected_province(event, filtered_ranking)
                    if clicked_province and clicked_province in province_options:
                        st.session_state["selected_province"] = clicked_province
                        selected_province = clicked_province

                    coverage, unmatched_count = build_geo_quality_summary(
                        filtered_ranking,
                        map_result.get("unmatched_provinces", []),
=======
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
>>>>>>> ad52dd7 (feat: improve DSS UI interaction, map rendering and category normalization)
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

<<<<<<< HEAD
                with right_focus_col:
                    st.markdown("### Vista focalizada")

                    select_options = ["-- Sin selección --"] + province_options
                    current_value = st.session_state.get("selected_province")
                    current_index = (
                        select_options.index(current_value)
                        if current_value in province_options
                        else 0
                    )

                    selected_option = st.selectbox(
                        "Provincia seleccionada",
                        options=select_options,
                        index=current_index,
                        key="province_selectbox_drilldown",
                    )

                    if selected_option == "-- Sin selección --":
                        selected_province = None
                        st.session_state["selected_province"] = None
                    else:
                        selected_province = selected_option
                        st.session_state["selected_province"] = selected_option

                    if st.button("Limpiar selección", use_container_width=True):
                        st.session_state["selected_province"] = None
                        st.rerun()

                    if selected_province:
                        focus_df = filtered_ranking[
                            filtered_ranking["provincia"] == selected_province
                        ].copy()

                        focus_map_result = build_rd_choropleth_from_source(
                            focus_df,
                            geo_source,
                            province_column="provincia",
                            color_column=metric_column,
                            title=f"Provincia en foco - {selected_province} ({selected_year})",
                        )

                        focus_figure = focus_map_result["figure"]
                        focus_figure.update_layout(
                            height=520,
                            margin=dict(l=10, r=10, t=50, b=10),
                        )
                        st.plotly_chart(focus_figure, use_container_width=True)

                        if not focus_df.empty:
                            province_row = focus_df.iloc[0]
                            st.metric("Provincia en foco", province_row["provincia"])
                            st.metric("Categoría", str(province_row["categoria"]))
                            st.metric("Score actual", f"{float(province_row['score_riesgo']):.3f}")
                    else:
                        st.info("Haz click en una provincia del mapa nacional o selecciónala en el desplegable.")

                st.markdown("---")
                render_province_drilldown(scored_df, selected_province, selected_year)
=======
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
>>>>>>> ad52dd7 (feat: improve DSS UI interaction, map rendering and category normalization)

        except Exception as exc:
            st.warning(f"No fue posible generar el mapa: {exc}")

<<<<<<< HEAD

with tab3:
    st.dataframe(metricas_df, use_container_width=True)

    fig_metrics = px.bar(
        metricas_df,
        x="metrica",
        y="valor",
        title="Métricas de evaluación Top-K",
    )
    fig_metrics.update_layout(height=400, xaxis_title="", yaxis_title="Valor")
    st.plotly_chart(fig_metrics, use_container_width=True)

with tab4:
    st.dataframe(explain_df, use_container_width=True)

    fig_imp = px.bar(
        explain_df.head(10),
        x="feature",
        y="importance",
        title="Explicabilidad global del modelo",
    )
    fig_imp.update_layout(height=450, xaxis_title="", yaxis_title="Importancia")
    st.plotly_chart(fig_imp, use_container_width=True)

with tab5:
    st.text_area(
        "Narrativa automática",
        results["narrative_text"],
        height=180,
    )

with tab6:
    csv_bytes = to_csv_bytes(filtered_ranking)

    detail_export_df = scored_df.copy()
    if selected_provinces:
        detail_export_df = detail_export_df[detail_export_df["provincia"].isin(selected_provinces)].copy()

    xlsx_bytes = to_excel_bytes(
        {
            "ranking_filtrado": filtered_ranking,
            "metricas": metricas_df,
            "detalle": detail_export_df,
            "explicabilidad": explain_df,
        }
    )

    st.download_button(
        "Descargar ranking CSV",
        data=csv_bytes,
        file_name=f"{PROJECT_NAME}_{VERSION}_ranking_{selected_year}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.download_button(
        "Descargar resultados Excel",
        data=xlsx_bytes,
        file_name=f"{PROJECT_NAME}_{VERSION}_resultados_{selected_year}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
=======
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
>>>>>>> ad52dd7 (feat: improve DSS UI interaction, map rendering and category normalization)
