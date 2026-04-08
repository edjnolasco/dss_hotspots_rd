from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import plotly.express as px

from .province_utils import canonical_province, normalize_text


# ============================================================
# CONFIGURACIÓN DE PROPIEDADES CANDIDATAS
# ============================================================

PROVINCE_PROPERTY_CANDIDATES = [
    "NAME_1",      # GADM
    "name",
    "Name",
    "provincia",
    "Provincia",
    "province",
    "nombre",
]


# ============================================================
# CARGA DE GEOJSON
# ============================================================

def load_geojson(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    """
    Carga un GeoJSON desde:
    - ruta local
    - texto JSON
    - diccionario ya cargado
    """
    if isinstance(source, dict):
        return source

    path = Path(str(source))
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Si no es archivo, intentar parsearlo como texto JSON
    return json.loads(str(source))


# ============================================================
# DETECCIÓN DE LA PROPIEDAD DE PROVINCIA
# ============================================================

def find_province_property(geojson: dict[str, Any]) -> str | None:
    """
    Intenta detectar automáticamente la propiedad que contiene el nombre
    de la provincia dentro de cada feature.
    """
    features = geojson.get("features", [])
    if not features:
        return None

    props = features[0].get("properties", {})
    if not props:
        return None

    # Prioridad exacta
    for candidate in PROVINCE_PROPERTY_CANDIDATES:
        if candidate in props:
            return candidate

    # Búsqueda normalizada defensiva
    normalized_map = {normalize_text(k): k for k in props.keys()}
    for candidate in PROVINCE_PROPERTY_CANDIDATES:
        normalized_candidate = normalize_text(candidate)
        if normalized_candidate in normalized_map:
            return normalized_map[normalized_candidate]

    return None


# ============================================================
# NORMALIZACIÓN DEL GEOJSON
# ============================================================

def normalize_geojson_provinces(
    geojson: dict[str, Any],
    province_property: str,
) -> dict[str, Any]:
    """
    Normaliza los nombres de provincias dentro del GeoJSON para mejorar
    el matching con el dataset.
    """
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        if province_property in props and props[province_property] is not None:
            props[province_property] = canonical_province(props[province_property])

    return geojson


# ============================================================
# VALIDACIÓN DE MATCH ENTRE RANKING Y GEOJSON
# ============================================================

def extract_geojson_province_names(
    geojson: dict[str, Any],
    province_property: str,
) -> set[str]:
    """
    Extrae el conjunto de nombres de provincia presentes en el GeoJSON.
    """
    names: set[str] = set()

    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        if province_property in props and props[province_property] is not None:
            names.add(canonical_province(props[province_property]))

    return names


def get_unmatched_provinces(
    ranking_df,
    geojson: dict[str, Any],
    province_property: str,
    ranking_column: str = "provincia",
) -> list[str]:
    """
    Devuelve las provincias del ranking que no encontraron correspondencia
    en el GeoJSON.
    """
    ranking_names = {
        canonical_province(x)
        for x in ranking_df[ranking_column].dropna().astype(str).tolist()
    }

    geojson_names = extract_geojson_province_names(geojson, province_property)

    return sorted(name for name in ranking_names if name not in geojson_names)


# ============================================================
# PREPARACIÓN DEL RANKING PARA MAPA
# ============================================================

def prepare_ranking_for_map(
    ranking_df,
    province_column: str = "provincia",
):
    """
    Normaliza la columna de provincia del ranking para maximizar el matching.
    """
    out = ranking_df.copy()
    out[province_column] = out[province_column].astype(str).apply(canonical_province)
    return out


# ============================================================
# CONSTRUCCIÓN DEL MAPA
# ============================================================

def build_choropleth(
    ranking_df,
    geojson: dict[str, Any],
    province_property: str,
    province_column: str = "provincia",
    color_column: str = "score_riesgo",
    title: str = "Mapa de riesgo por provincia",
):
    """
    Construye el mapa coroplético con Plotly.
    """
    fig = px.choropleth(
        ranking_df,
        geojson=geojson,
        locations=province_column,
        featureidkey=f"properties.{province_property}",
        color=color_column,
        hover_name=province_column,
        hover_data={
            "pred_fallecidos_next": ":.2f"
            if "pred_fallecidos_next" in ranking_df.columns
            else False,
            "score_riesgo": ":.3f"
            if "score_riesgo" in ranking_df.columns
            else False,
            "categoria": True if "categoria" in ranking_df.columns else False,
            "fallecidos_actuales": True
            if "fallecidos_actuales" in ranking_df.columns
            else False,
        },
        title=title,
    )

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        height=720,
        margin=dict(l=0, r=0, t=50, b=0),
    )

    return fig


# ============================================================
# FUNCIÓN DE ALTO NIVEL PARA USO DIRECTO
# ============================================================

def build_rd_choropleth_from_source(
    ranking_df,
    geojson_source: str | Path | dict[str, Any],
    province_column: str = "provincia",
    color_column: str = "score_riesgo",
    title: str = "Mapa de riesgo por provincia",
):
    """
    Flujo completo:
    1. Carga GeoJSON
    2. Detecta propiedad provincial
    3. Normaliza provincias del GeoJSON
    4. Normaliza provincias del ranking
    5. Devuelve figura y provincias sin match
    """
    geojson = load_geojson(geojson_source)

    province_property = find_province_property(geojson)
    if not province_property:
        raise ValueError(
            "No se pudo identificar la propiedad de provincia en el GeoJSON. "
            "Para GADM se espera 'NAME_1'."
        )

    geojson = normalize_geojson_provinces(geojson, province_property)
    ranking_prepared = prepare_ranking_for_map(ranking_df, province_column=province_column)
    unmatched = get_unmatched_provinces(
        ranking_prepared,
        geojson,
        province_property,
        ranking_column=province_column,
    )

    fig = build_choropleth(
        ranking_prepared,
        geojson,
        province_property=province_property,
        province_column=province_column,
        color_column=color_column,
        title=title,
    )

    return {
        "figure": fig,
        "geojson": geojson,
        "province_property": province_property,
        "ranking_df": ranking_prepared,
        "unmatched_provinces": unmatched,
    }
