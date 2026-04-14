from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.data_sources import (  # noqa: E402
    OFFICIAL_PROVINCES_URL,
    fetch_remote_dataframe,
    load_local_dataframe,
    normalize_official_provinces,
    read_dataframe_from_bytes,
)
from src.exporter import to_csv_bytes, to_excel_bytes  # noqa: E402
from src.map_utils import build_rd_choropleth_from_source  # noqa: E402
from src.pipeline import run_pipeline  # noqa: E402
from src.version import AUTHOR, PROJECT_NAME, VERSION  # noqa: E402


# ============================================================
# CONFIGURACIÓN STREAMLIT
# ============================================================
st.set_page_config(page_title=f"{PROJECT_NAME} {VERSION}", layout="wide")
st.title(f"{PROJECT_NAME} {VERSION}")
st.caption(f"Autor: {AUTHOR}")


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

    selection = None
    if isinstance(event, dict):
        selection = event.get("selection")
    else:
        selection = getattr(event, "selection", None)

    if not selection:
        return None

    points = selection.get("points", [])
    if not points:
        return None

    point = points[0]

    for key in ("location", "x", "label", "hovertext"):
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
with st.sidebar:
    st.header("Fuente de datos")
    source_mode = st.radio(
        "Selecciona la fuente",
        ["Subir CSV/XLSX", "Ruta local", "Fuente oficial DIGESETT"],
        index=0,
    )

    local_path = (
        st.text_input(
            "Ruta local del dataset",
            value=str(ROOT / "data" / "fallecimientos_provincias.csv"),
        )
        if source_mode == "Ruta local"
        else ""
    )

    uploaded_file = (
        st.file_uploader("Sube el dataset", type=["csv", "xlsx", "xls"])
        if source_mode == "Subir CSV/XLSX"
        else None
    )

    st.header("GeoJSON")
    geo_mode = st.radio(
        "Selecciona la fuente del mapa",
        ["Ruta local", "Subir GeoJSON", "Omitir mapa"],
        index=0,
    )

    geo_local_path = (
        st.text_input(
            "Ruta local del GeoJSON",
            value=str(ROOT / "data" / "rd_provinces.geojson"),
        )
        if geo_mode == "Ruta local"
        else ""
    )

    uploaded_geo = (
        st.file_uploader("Sube el GeoJSON", type=["geojson", "json"])
        if geo_mode == "Subir GeoJSON"
        else None
    )

    run_clicked = st.button("Ejecutar análisis", type="primary", use_container_width=True)


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
if run_clicked:
    try:
        if source_mode == "Fuente oficial DIGESETT":
            try:
                normalized_df = load_data_remote()
                source_label = "Fuente oficial DIGESETT"
            except Exception:
                st.error(
                    "La fuente oficial DIGESETT rechazó la descarga remota (HTTP 403 o acceso restringido). "
                    "Usa la opción 'Subir CSV/XLSX' con el archivo oficial descargado manualmente."
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
        st.session_state["selected_province"] = None
        st.success("Análisis ejecutado correctamente.")

    except Exception as exc:
        st.error("No fue posible completar el análisis.")
        st.exception(exc)


# ============================================================
# APP PRINCIPAL
# ============================================================
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
top_n = fcol4.slider("Top-N", min_value=3, max_value=max(3, len(available_provinces_for_year)), value=min(10, max(3, len(available_provinces_for_year))))

show_top_only = st.checkbox("Mostrar solo Top-N en ranking y mapa", value=False)

base_year_ranking = build_year_ranking(scored_df, selected_year)
filtered_ranking = apply_interactive_filters(
    base_year_ranking,
    selected_provinces=selected_provinces,
    top_n=top_n,
    show_top_only=show_top_only,
)

if filtered_ranking.empty:
    st.warning("No hay datos disponibles con la combinación actual de filtros.")    
    st.stop()

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
    if geo_mode == "Omitir mapa":
        st.info("Mapa omitido.")
    else:
        try:
            if geo_mode == "Ruta local":
                geo_source = geo_local_path
            else:
                if uploaded_geo is None:
                    st.info("Sube un archivo GeoJSON.")
                    geo_source = None
                else:
                    geo_source = uploaded_geo.getvalue().decode("utf-8")

            if geo_source is not None:
                map_result = build_rd_choropleth_from_source(
                    filtered_ranking,
                    geo_source,
                    province_column="provincia",
                    color_column=metric_column,
                    title=f"Mapa nacional por provincia - {selected_year}",
                )

                left_map_col, right_focus_col = st.columns([1.6, 1.0])

                with left_map_col:
                    st.markdown("### Vista nacional")

                    figure = map_result["figure"]
                    figure.update_layout(clickmode="event+select")

                    event = st.plotly_chart(
                        figure,
                        use_container_width=True,
                        on_select="rerun",
                        key=f"rd_map_{selected_year}_{metric_column}_{show_top_only}_{top_n}",
                    )

                    clicked_province = extract_selected_province(event, filtered_ranking)
                    if clicked_province:
                        st.session_state["selected_province"] = clicked_province

                    coverage, unmatched_count = build_geo_quality_summary(
                        filtered_ranking,
                        map_result.get("unmatched_provinces", []),
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

                province_options = filtered_ranking["provincia"].tolist()

                with right_focus_col:
                    st.markdown("### Vista focalizada")

                    default_index = (
                        province_options.index(st.session_state["selected_province"])
                        if st.session_state["selected_province"] in province_options
                        else 0
                    )

                    selected_province = st.selectbox(
                        "Provincia seleccionada",
                        options=province_options,
                        index=default_index,
                    )
                    st.session_state["selected_province"] = selected_province

                    clear_selection = st.button("Limpiar selección", use_container_width=True)
                    if clear_selection:
                        st.session_state["selected_province"] = None
                        selected_province = province_options[0]

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

                st.markdown("---")
                render_province_drilldown(scored_df, selected_province, selected_year)

        except Exception as exc:
            st.warning(f"No fue posible generar el mapa: {exc}")


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
