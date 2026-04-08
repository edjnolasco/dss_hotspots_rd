from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.version import PROJECT_NAME, VERSION, AUTHOR
from src.data_sources import (
    OFFICIAL_PROVINCES_URL,
    read_dataframe_from_bytes,
    load_local_dataframe,
    normalize_official_provinces,
)
from src.pipeline import run_pipeline
from src.map_utils import build_rd_choropleth_from_source
from src.exporter import to_csv_bytes, to_excel_bytes
from src.validation import validate_province_coverage


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(page_title=f"{PROJECT_NAME} {VERSION}", layout="wide")
st.title(f"{PROJECT_NAME} {VERSION}")
st.caption(f"Autor: {AUTHOR}")


# ============================================================
# KPI DASHBOARD
# ============================================================

def kpi_dashboard(ranking_df):
    top1 = ranking_df.iloc[0]

    fig = go.Figure()

    fig.add_trace(go.Indicator(
        mode="number",
        value=1,
        title={"text": f"<b>Provincia líder</b><br>{top1['provincia']}"},
        domain={"row": 0, "column": 0},
    ))

    fig.add_trace(go.Indicator(
        mode="number",
        value=float(top1["score_riesgo"]),
        number={"valueformat": ".3f"},
        title={"text": "<b>Score líder</b>"},
        domain={"row": 0, "column": 1},
    ))

    fig.add_trace(go.Indicator(
        mode="number",
        value=float(top1["pred_fallecidos_next"]),
        number={"valueformat": ".2f"},
        title={"text": "<b>Predicción líder</b>"},
        domain={"row": 0, "column": 2},
    ))

    fig.add_trace(go.Indicator(
        mode="number",
        value=float(top1["fallecidos_actuales"]),
        number={"valueformat": ".0f"},
        title={"text": "<b>Fallecidos actuales</b>"},
        domain={"row": 0, "column": 3},
    ))

    fig.update_layout(
        grid={"rows": 1, "columns": 4, "pattern": "independent"},
        height=220,
        margin=dict(l=20, r=20, t=10, b=10),
    )

    return fig


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

    st.header("Mapa")

    geo_mode = st.radio(
        "Fuente del GeoJSON",
        ["Ruta local", "Subir GeoJSON", "Omitir mapa"],
        index=0,
    )

    geo_local_path = (
        st.text_input(
            "Ruta GeoJSON",
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
# CACHE
# ============================================================

@st.cache_data(show_spinner=False)
def load_data_local(path):
    raw = load_local_dataframe(path)
    return normalize_official_provinces(raw)


@st.cache_data(show_spinner=False)
def process_uploaded_data(name, content):
    raw = read_dataframe_from_bytes(content, filename_hint=name)
    return normalize_official_provinces(raw)


@st.cache_data(show_spinner=False)
def process_pipeline(df):
    return run_pipeline(df)


# ============================================================
# APP
# ============================================================

if run_clicked:
    try:
        # --------------------------------------------------------
        # Carga de datos
        # --------------------------------------------------------
        if source_mode == "Fuente oficial DIGESETT":
            st.warning(
                "La fuente oficial DIGESETT funciona en modo asistido, porque el servidor "
                "puede rechazar descargas automáticas desde scripts."
            )

            st.link_button(
                "Abrir recurso oficial DIGESETT",
                OFFICIAL_PROVINCES_URL,
                use_container_width=True,
            )

            st.info(
                "Descarga el archivo oficial y luego vuelve a la aplicación para usar "
                "'Subir CSV/XLSX' o 'Ruta local'."
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

        # --------------------------------------------------------
        # Validación territorial
        # --------------------------------------------------------
        coverage = validate_province_coverage(normalized_df)

        if coverage["is_complete"]:
            st.success(
                f"Cobertura territorial completa: {coverage['observed_count']} de "
                f"{coverage['expected_count']} demarcaciones."
            )
        else:
            st.warning(
                f"Cobertura territorial parcial: {coverage['observed_count']} de "
                f"{coverage['expected_count']} demarcaciones."
            )

            if coverage["missing_provinces"]:
                with st.expander("Ver demarcaciones faltantes"):
                    st.write(coverage["missing_provinces"])

            if coverage["extra_provinces"]:
                with st.expander("Ver nombres no reconocidos en el dataset"):
                    st.write(coverage["extra_provinces"])

        # --------------------------------------------------------
        # Pipeline
        # --------------------------------------------------------
        results = process_pipeline(normalized_df)

        ranking_df = results["ranking_df"]
        metricas_df = results["metricas_df"]
        explain_df = results["explain_df"]
        scored_df = results["scored_df"]

        st.success("Análisis completado correctamente.")
        st.write(source_label)

        # --------------------------------------------------------
        # KPIs
        # --------------------------------------------------------
        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric("Año objetivo", results["latest_year"])
        c2.metric("MAE", f"{results['mae']:.3f}" if results["mae"] is not None else "N/D")
        c3.metric("R²", f"{results['r2']:.3f}" if results["r2"] is not None else "N/D")
        c4.metric("Demarcaciones en el ranking", int(ranking_df["provincia"].nunique()))
        c5.metric(
            "Demarcaciones con datos",
            int((ranking_df["categoria"] != "Sin datos").sum())
        )

        st.plotly_chart(kpi_dashboard(ranking_df), use_container_width=True)

        # --------------------------------------------------------
        # Tabs
        # --------------------------------------------------------
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
            ["Ranking", "Métricas", "Explicabilidad", "Mapa", "Narrativa", "Exportación"]
        )

        with tab1:
            st.dataframe(ranking_df, use_container_width=True)

            fig_rank = px.bar(
                ranking_df.head(min(15, len(ranking_df))),
                x="provincia",
                y="score_riesgo",
                color="categoria",
                hover_data=["pred_fallecidos_next", "fallecidos_actuales"],
                title="Ranking de provincias priorizadas",
            )
            fig_rank.update_layout(
                height=500,
                xaxis_title="",
                yaxis_title="Score de riesgo",
            )
            st.plotly_chart(fig_rank, use_container_width=True)

            fig_scatter = px.scatter(
                ranking_df,
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
            st.dataframe(metricas_df, use_container_width=True)

            fig_metrics = px.bar(
                metricas_df,
                x="metrica",
                y="valor",
                title="Métricas de evaluación Top-K",
            )
            fig_metrics.update_layout(
                height=400,
                xaxis_title="",
                yaxis_title="Valor",
            )
            st.plotly_chart(fig_metrics, use_container_width=True)

        with tab3:
            st.dataframe(explain_df, use_container_width=True)

            fig_imp = px.bar(
                explain_df.head(10),
                x="feature",
                y="importance",
                title="Explicabilidad global del modelo",
            )
            fig_imp.update_layout(
                height=450,
                xaxis_title="",
                yaxis_title="Importancia",
            )
            st.plotly_chart(fig_imp, use_container_width=True)

        with tab4:
            if geo_mode == "Omitir mapa":
                st.info("Mapa omitido.")
            else:
                try:
                    if geo_mode == "Ruta local":
                        geo_source = geo_local_path
                    else:
                        geo_source = uploaded_geo.getvalue().decode("utf-8") if uploaded_geo else None

                    if geo_source is None:
                        st.info("Debes proporcionar un GeoJSON para visualizar el mapa.")
                    else:
                        map_result = build_rd_choropleth_from_source(
                            ranking_df,
                            geo_source,
                            province_column="provincia",
                            color_column="score_riesgo",
                            title="Mapa de riesgo por provincia",
                        )

                        if map_result["unmatched_provinces"]:
                            st.warning(
                                "Provincias sin correspondencia en el GeoJSON: "
                                f"{map_result['unmatched_provinces']}"
                            )

                        st.plotly_chart(map_result["figure"], use_container_width=True)

                except Exception as e:
                    st.warning(f"No fue posible generar el mapa: {e}")

        with tab5:
            st.text_area("Narrativa", results["narrative_text"], height=200)

        with tab6:
            st.download_button(
                "Descargar ranking CSV",
                data=to_csv_bytes(ranking_df),
                file_name=f"{PROJECT_NAME}_{VERSION}_ranking.csv",
                mime="text/csv",
                use_container_width=True,
            )

            st.download_button(
                "Descargar resultados Excel",
                data=to_excel_bytes({
                    "ranking": ranking_df,
                    "metricas": metricas_df,
                    "detalle": scored_df,
                    "explicabilidad": explain_df,
                }),
                file_name=f"{PROJECT_NAME}_{VERSION}_resultados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    except Exception as e:
        st.error("Error en ejecución.")
        st.exception(e)

else:
    st.info("Configura la fuente de datos y ejecuta el análisis.")
    st.markdown("### Fuente oficial prevista")
    st.code(OFFICIAL_PROVINCES_URL)
    st.markdown("### Nota sobre DIGESETT")
    st.write(
        "La opción 'Fuente oficial DIGESETT' funciona en modo asistido: abre el recurso oficial "
        "para que descargues el archivo manualmente y luego lo uses en 'Subir CSV/XLSX' o 'Ruta local'."
    )
    st.markdown("### GeoJSON esperado")
    st.code(str(ROOT / "data" / "rd_provinces.geojson"))
