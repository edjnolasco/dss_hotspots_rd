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
    )

    return fig


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("Fuente de datos")

    source_mode = st.radio(
        "Fuente",
        ["Subir CSV/XLSX", "Ruta local", "Fuente oficial DIGESETT"],
    )

    local_path = st.text_input(
        "Ruta local",
        value=str(ROOT / "data" / "fallecimientos_provincias.csv"),
    )

    uploaded_file = st.file_uploader("Archivo", type=["csv", "xlsx"])

    st.header("Mapa")

    geo_mode = st.radio(
        "GeoJSON",
        ["Ruta local", "Subir", "Omitir"],
    )

    geo_local_path = st.text_input(
        "Ruta GeoJSON",
        value=str(ROOT / "data" / "rd_provinces.geojson"),
    )

    uploaded_geo = st.file_uploader("GeoJSON", type=["geojson", "json"])

    debug_map = st.checkbox("Modo depuración mapa", value=False)

    run_clicked = st.button("Ejecutar", use_container_width=True)


# ============================================================
# CACHE
# ============================================================

@st.cache_data
def load_data_local(path):
    raw = load_local_dataframe(path)
    return normalize_official_provinces(raw)


@st.cache_data
def process_uploaded(name, content):
    raw = read_dataframe_from_bytes(content, filename_hint=name)
    return normalize_official_provinces(raw)


@st.cache_data
def process_pipeline(df):
    return run_pipeline(df)


# ============================================================
# APP
# ============================================================

if run_clicked:

    if source_mode == "Subir CSV/XLSX":
        if uploaded_file is None:
            st.error("Sube un archivo")
            st.stop()
        df = process_uploaded(uploaded_file.name, uploaded_file.getvalue())

    elif source_mode == "Ruta local":
        df = load_data_local(local_path)

    else:
        st.link_button("Abrir DIGESETT", OFFICIAL_PROVINCES_URL)
        st.stop()

    # VALIDACIÓN
    coverage = validate_province_coverage(df)

    if coverage["is_complete"]:
        st.success(f"32/32 demarcaciones")
    else:
        st.warning(f"{coverage['observed_count']}/32 demarcaciones")

    results = process_pipeline(df)
    ranking_df = results["ranking_df"]

    # KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Año", results["latest_year"])
    c2.metric("MAE", f"{results['mae']:.3f}" if results["mae"] else "N/D")
    c3.metric("R²", f"{results['r2']:.3f}" if results["r2"] else "N/D")
    c4.metric("Demarcaciones", ranking_df["provincia"].nunique())
    c5.metric("Con datos", (ranking_df["categoria"] != "Sin datos").sum())

    st.plotly_chart(kpi_dashboard(ranking_df), use_container_width=True)

    # ============================================================
    # MAPA + DEBUG
    # ============================================================

    if geo_mode != "Omitir":

        if geo_mode == "Ruta local":
            geo_source = geo_local_path
        else:
            geo_source = uploaded_geo.getvalue().decode("utf-8") if uploaded_geo else None

        if geo_source:

            map_result = build_rd_choropleth_from_source(
                ranking_df,
                geo_source,
            )

            if map_result["unmatched_provinces"]:
                st.warning(map_result["unmatched_provinces"])

            st.plotly_chart(map_result["figure"], use_container_width=True)

            # ============================
            # 🔍 DEPURACIÓN
            # ============================
            if debug_map:

                st.subheader("Depuración GeoJSON")

                geo_features = map_result["geojson"].get("features", [])
                rows = []

                for f in geo_features:
                    props = f.get("properties", {})
                    raw_name = props.get(map_result["province_property"])

                    rows.append({
                        "raw_name": raw_name,
                        "repr": repr(raw_name),
                        "province_name": props.get("province_name"),
                        "province_key": props.get("province_key"),
                    })

                st.dataframe(rows, use_container_width=True)

                st.subheader("Provincias del ranking")
                st.write(sorted(ranking_df["provincia"].unique().tolist()))

else:
    st.info("Ejecuta el análisis")
