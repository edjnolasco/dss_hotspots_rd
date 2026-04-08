import sys, json
from pathlib import Path
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.version import PROJECT_NAME, VERSION, AUTHOR
from src.data_sources import OFFICIAL_PROVINCES_URL, read_dataframe_from_bytes, load_local_dataframe, fetch_remote_dataframe, fetch_geojson_text, normalize_official_provinces
from src.pipeline import run_pipeline
from src.map_utils import find_province_property, normalize_geojson_provinces, build_choropleth
from src.exporter import to_csv_bytes, to_excel_bytes

st.set_page_config(page_title=f"{PROJECT_NAME} {VERSION}", layout="wide")
st.title(f"{PROJECT_NAME} {VERSION}")
st.caption(f"Autor: {AUTHOR}")

with st.sidebar:
    st.header("Fuente de datos")
    source_mode = st.radio("Selecciona la fuente", ["Fuente oficial DIGESETT", "Subir CSV/XLSX", "Ruta local"], index=0)
    local_path = st.text_input("Ruta local del dataset", value=str(ROOT / "data" / "fallecimientos_provincias.csv")) if source_mode == "Ruta local" else ""
    uploaded_file = st.file_uploader("Sube el dataset", type=["csv", "xlsx", "xls"]) if source_mode == "Subir CSV/XLSX" else None

    st.header("GeoJSON")
    geo_mode = st.radio("Selecciona la fuente del mapa", ["Intentar descarga remota", "Subir GeoJSON", "Ruta local", "Omitir mapa"], index=0)
    geo_local_path = st.text_input("Ruta local del GeoJSON", value=str(ROOT / "data" / "rd_provincias.geojson")) if geo_mode == "Ruta local" else ""
    uploaded_geo = st.file_uploader("Sube el GeoJSON", type=["geojson", "json"]) if geo_mode == "Subir GeoJSON" else None

    run_clicked = st.button("Ejecutar análisis", type="primary", use_container_width=True)

@st.cache_data(show_spinner=False)
def load_data_remote():
    raw = fetch_remote_dataframe(OFFICIAL_PROVINCES_URL, filename_hint="fallecimientos_provincias.csv")
    return normalize_official_provinces(raw)

@st.cache_data(show_spinner=False)
def load_data_local(path_str: str):
    return normalize_official_provinces(load_local_dataframe(path_str))

@st.cache_data(show_spinner=False)
def process_uploaded_data(file_name: str, file_bytes: bytes):
    return normalize_official_provinces(read_dataframe_from_bytes(file_bytes, filename_hint=file_name))

@st.cache_data(show_spinner=False)
def process_pipeline(df):
    return run_pipeline(df)

def kpi_dashboard(ranking_df):
    top1 = ranking_df.iloc[0]
    fig = go.Figure()
    fig.add_trace(go.Indicator(mode="number", value=1, title={"text": f"<b>Provincia líder</b><br>{top1['provincia']}"}, domain={"row": 0, "column": 0}))
    fig.add_trace(go.Indicator(mode="number", value=float(top1["score_riesgo"]), number={"valueformat": ".3f"}, title={"text": "<b>Score líder</b>"}, domain={"row": 0, "column": 1}))
    fig.add_trace(go.Indicator(mode="number", value=float(top1["pred_fallecidos_next"]), number={"valueformat": ".2f"}, title={"text": "<b>Predicción líder</b>"}, domain={"row": 0, "column": 2}))
    fig.add_trace(go.Indicator(mode="number", value=float(top1["fallecidos_actuales"]), number={"valueformat": ".0f"}, title={"text": "<b>Fallecidos actuales</b>"}, domain={"row": 0, "column": 3}))
    fig.update_layout(grid={"rows": 1, "columns": 4, "pattern": "independent"}, height=220, margin=dict(l=20, r=20, t=10, b=10))
    return fig

if run_clicked:
    try:
        if source_mode == "Fuente oficial DIGESETT":
            normalized_df = load_data_remote()
            source_label = "Fuente oficial DIGESETT"
        elif source_mode == "Subir CSV/XLSX":
            if uploaded_file is None:
                st.error("Debes subir un archivo.")
                st.stop()
            normalized_df = process_uploaded_data(uploaded_file.name, uploaded_file.getvalue())
            source_label = f"Archivo subido: {uploaded_file.name}"
        else:
            normalized_df = load_data_local(local_path)
            source_label = f"Ruta local: {local_path}"

        results = process_pipeline(normalized_df)
        ranking_df = results["ranking_df"]
        metricas_df = results["metricas_df"]
        explain_df = results["explain_df"]
        scored_df = results["scored_df"]

        st.success("Análisis ejecutado correctamente.")
        st.write(source_label)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Año objetivo", results["latest_year"])
        c2.metric("MAE", f"{results['mae']:.3f}" if results["mae"] is not None else "N/D")
        c3.metric("R²", f"{results['r2']:.3f}" if results["r2"] is not None else "N/D")
        c4.metric("Provincias evaluadas", int(ranking_df["provincia"].nunique()))
        st.plotly_chart(kpi_dashboard(ranking_df), use_container_width=True)

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Ranking", "Métricas", "Explicabilidad", "Mapa", "Narrativa", "Exportación"])

        with tab1:
            st.dataframe(ranking_df, use_container_width=True)
            fig_rank = px.bar(ranking_df.head(min(15, len(ranking_df))), x="provincia", y="score_riesgo", color="categoria", hover_data=["pred_fallecidos_next", "fallecidos_actuales"], title="Ranking de provincias priorizadas")
            fig_rank.update_layout(height=500, xaxis_title="", yaxis_title="Score de riesgo")
            st.plotly_chart(fig_rank, use_container_width=True)

        with tab2:
            st.dataframe(metricas_df, use_container_width=True)
            fig_metrics = px.bar(metricas_df, x="metrica", y="valor", title="Métricas de evaluación Top-K")
            fig_metrics.update_layout(height=400, xaxis_title="", yaxis_title="Valor")
            st.plotly_chart(fig_metrics, use_container_width=True)

        with tab3:
            st.dataframe(explain_df, use_container_width=True)
            fig_imp = px.bar(explain_df.head(10), x="feature", y="importance", title="Explicabilidad global del modelo")
            fig_imp.update_layout(height=450, xaxis_title="", yaxis_title="Importancia")
            st.plotly_chart(fig_imp, use_container_width=True)

        with tab4:
            if geo_mode == "Omitir mapa":
                st.info("Mapa omitido.")
            else:
                try:
                    if geo_mode == "Intentar descarga remota":
                        geojson_text = fetch_geojson_text()
                    elif geo_mode == "Subir GeoJSON":
                        if uploaded_geo is None:
                            st.info("Sube un archivo GeoJSON.")
                            geojson_text = None
                        else:
                            geojson_text = uploaded_geo.getvalue().decode("utf-8")
                    else:
                        geojson_text = Path(geo_local_path).read_text(encoding="utf-8")
                    if geojson_text:
                        geojson = json.loads(geojson_text)
                        province_property = find_province_property(geojson)
                        if not province_property:
                            st.error("No se pudo identificar la propiedad de provincia en el GeoJSON.")
                        else:
                            geojson = normalize_geojson_provinces(geojson, province_property)
                            st.plotly_chart(build_choropleth(ranking_df, geojson, province_property), use_container_width=True)
                except Exception as e:
                    st.warning(f"No fue posible generar el mapa: {e}")

        with tab5:
            st.text_area("Narrativa automática", results["narrative_text"], height=180)

        with tab6:
            csv_bytes = to_csv_bytes(ranking_df)
            xlsx_bytes = to_excel_bytes({"ranking": ranking_df, "metricas": metricas_df, "detalle": scored_df, "explicabilidad": explain_df})
            st.download_button("Descargar ranking CSV", data=csv_bytes, file_name=f"{PROJECT_NAME}_{VERSION}_ranking.csv", mime="text/csv", use_container_width=True)
            st.download_button("Descargar resultados Excel", data=xlsx_bytes, file_name=f"{PROJECT_NAME}_{VERSION}_resultados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    except Exception as e:
        st.error("No fue posible completar el análisis.")
        st.exception(e)
else:
    st.info("Configura la fuente de datos y ejecuta el análisis.")
