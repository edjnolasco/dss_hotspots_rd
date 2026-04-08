import plotly.express as px
from .province_utils import canonical_province, normalize_text

def find_province_property(geojson: dict) -> str | None:
    if not geojson.get("features"):
        return None
    props = geojson["features"][0].get("properties", {})
    normalized = {normalize_text(k): k for k in props.keys()}
    for candidate in ["provincia", "province", "name", "nombre"]:
        if candidate in normalized:
            return normalized[candidate]
    return None

def normalize_geojson_provinces(geojson: dict, province_property: str) -> dict:
    for feat in geojson.get("features", []):
        props = feat.get("properties", {})
        if province_property in props:
            props[province_property] = canonical_province(props[province_property])
    return geojson

def build_choropleth(ranking_df, geojson: dict, province_property: str):
    fig = px.choropleth(
        ranking_df, geojson=geojson, featureidkey=f"properties.{province_property}",
        locations="provincia", color="score_riesgo", hover_name="provincia",
        hover_data={"pred_fallecidos_next": ":.2f", "score_riesgo": ":.3f", "categoria": True, "fallecidos_actuales": True},
        title="Mapa de riesgo por provincia",
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(height=700, margin=dict(l=0, r=0, t=50, b=0))
    return fig
