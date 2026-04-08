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


# ============================================================
# CONFIGURACIÓN STREAMLIT
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

    st.header("GeoJSON")

    geo_mode = st.radio(
        "Fuente del mapa",
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
        st.file_uploader("Sube GeoJSON", type=["geojson", "json"])
        if geo_mode == "Subir GeoJSON"
        else None
    )

    run_clicked = st.button("Ejecutar análisis", type="primary", use_container_width=True)


# ============================================================
# CACHÉ
# ============================================================

@st.cache_data
def load_data_local(path):
    raw = load_local_dataframe(path)
    return normalize_official_provinces(raw)


@st.cache_data
def process_uploaded_data(name, bytes_):
    raw = read_dataframe_from_bytes(bytes_, filename_hint=name)
    return normalize_official_provinces(raw)


@st.cache_data
def process_pipeline(df):
    return run_pipeline(df)


# ============================================================
# APP
# ============================================================

if run_clicked:
    try:
        # -------------------------
        # DATA
        # -------------------------
        if source_mode == "Fuente oficial DIGESETT":
            st.warning("Modo asistido: descarga manual requerida.")

            st.link_button(
                "Abrir DIGESETT",
                OFFICIAL_PROVINCES_URL,
                use_container_width=True,
            )

            st.info("Descarga el archivo y súbelo manualmente.")
            st.stop()

        elif source_mode == "Subir CSV/XLSX":
            if uploaded_file is None:
                st.error("Debes subir un archivo.")
                st.stop()

            normalized_df = process_uploaded_data(
                uploaded_file.name,
                uploaded_file.getvalue(),
            )
            source_label = uploaded_file.name

        else:
            normalized_df = load_data_local(local_path)
            source_label = local_path

        # -------------------------
        # PIPELINE
        # -------------------------
        results = process_pipeline(normalized_df)

        ranking_df = results["ranking_df"]
        metricas_df = results["metricas_df"]
        explain_df = results["explain_df"]
        scored_df = results["scored_df"]

        st.success("Análisis completado")
        st.write(source_label)

        # ============================================================
        # KPIs ACTUALIZADOS
        # ============================================================
        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric("Año objetivo", results["latest_year"])
        c2.metric("MAE", f"{results['mae']:.3f}" if results["mae"] else "N/D")
        c3.metric("R²", f"{results['r2']:.3f}" if results["r2"] else "N/D")
        c4.metric("Demarcaciones en el ranking", int(ranking_df["provincia"].nunique()))
        c5.metric(
            "Demarcaciones con datos",
            int((ranking_df["categoria"] != "Sin datos").sum())
        )

        st.plotly_chart(kpi_dashboard(ranking_df), use_container_width=True)

        # ============================================================
        # TABS
        # ============================================================
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
            ["Ranking", "Métricas", "Explicabilidad", "Mapa", "Narrativa", "Exportación"]
        )

        with tab1:
            st.dataframe(ranking_df, use_container_width=True)

        with tab2:
            st.dataframe(metricas_df, use_container_width=True)

        with tab3:
            st.dataframe(explain_df, use_container_width=True)

        with tab4:
            if geo_mode == "Omitir mapa":
                st.info("Mapa omitido")
            else:
                geo_source = (
                    geo_local_path
                    if geo_mode == "Ruta local"
                    else uploaded_geo.getvalue().decode("utf-8") if uploaded_geo else None
                )

                if geo_source:
                    map_result = build_rd_choropleth_from_source(
                        ranking_df,
                        geo_source,
                    )

                    if map_result["unmatched_provinces"]:
                        st.warning(map_result["unmatched_provinces"])

                    st.plotly_chart(map_result["figure"], use_container_width=True)

        with tab5:
            st.text_area("Narrativa", results["narrative_text"], height=200)

        with tab6:
            st.download_button(
                "CSV",
                data=to_csv_bytes(ranking_df),
                file_name="ranking.csv",
            )

            st.download_button(
                "Excel",
                data=to_excel_bytes({
                    "ranking": ranking_df,
                    "metricas": metricas_df,
                    "detalle": scored_df,
                    "explicabilidad": explain_df,
                }),
                file_name="resultados.xlsx",
            )

    except Exception as e:
        st.error("Error en ejecución")
        st.exception(e)

else:
    st.info("Configura y ejecuta el análisis.")
