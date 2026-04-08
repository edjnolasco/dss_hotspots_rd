from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import plotly.express as px

from .province_utils import canonical_province, normalize_text, province_key


PROVINCE_PROPERTY_CANDIDATES = [
    "NAME_1",   # GADM
    "name",
    "Name",
    "provincia",
    "Provincia",
    "province",
    "nombre",
]


def load_geojson(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        return source

    path = Path(str(source))
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    return json.loads(str(source))


def find_province_property(geojson: dict[str, Any]) -> str | None:
    features = geojson.get("features", [])
    if not features:
        return None

    props = features[0].get("properties", {})
    if not props:
        return None

    for candidate in PROVINCE_PROPERTY_CANDIDATES:
        if candidate in props:
            return candidate

    normalized_map = {normalize_text(k): k for k in props.keys()}
    for candidate in PROVINCE_PROPERTY_CANDIDATES:
        norm_candidate = normalize_text(candidate)
        if norm_candidate in normalized_map:
            return normalized_map[norm_candidate]

    return None


def normalize_geojson_provinces(
    geojson: dict[str, Any],
    province_property: str,
) -> dict[str, Any]:
    """
    Agrega dos campos al GeoJSON:
    - province_name: nombre canónico bonito
    - province_key: clave técnica para matching
    """
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        if province_property in props and props[province_property] is not None:
            canon = canonical_province(props[province_property])
            props["province_name"] = canon
            props["province_key"] = province_key(canon)

    return geojson


def extract_geojson_province_keys(
    geojson: dict[str, Any],
) -> set[str]:
    keys: set[str] = set()

    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        key = props.get("province_key")
        if key:
            keys.add(str(key))

    return keys


def get_unmatched_provinces(
    ranking_df,
    geojson: dict[str, Any],
    ranking_key_column: str = "provincia_key",
) -> list[str]:
    ranking_keys = {
        str(x)
        for x in ranking_df[ranking_key_column].dropna().astype(str).tolist()
    }

    geojson_keys = extract_geojson_province_keys(geojson)

    missing_keys = sorted(key for key in ranking_keys if key not in geojson_keys)

    if not missing_keys:
        return []

    # devolver nombres bonitos si existen
    if "provincia" in ranking_df.columns:
        subset = ranking_df[ranking_df[ranking_key_column].isin(missing_keys)]
        return sorted(subset["provincia"].astype(str).unique().tolist())

    return missing_keys


def prepare_ranking_for_map(
    ranking_df,
    province_column: str = "provincia",
):
    out = ranking_df.copy()
    out[province_column] = out[province_column].astype(str).apply(canonical_province)
    out["provincia_key"] = out[province_column].astype(str).apply(province_key)
    return out


def build_choropleth(
    ranking_df,
    geojson: dict[str, Any],
    color_column: str = "score_riesgo",
    title: str = "Mapa de riesgo por provincia",
):
    fig = px.choropleth(
        ranking_df,
        geojson=geojson,
        locations="provincia_key",
        featureidkey="properties.province_key",
        color=color_column,
        hover_name="provincia",
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
            "provincia_key": False,
        },
        title=title,
    )

    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        height=720,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig


def build_rd_choropleth_from_source(
    ranking_df,
    geojson_source: str | Path | dict[str, Any],
    province_column: str = "provincia",
    color_column: str = "score_riesgo",
    title: str = "Mapa de riesgo por provincia",
):
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
        ranking_key_column="provincia_key",
    )

    fig = build_choropleth(
        ranking_prepared,
        geojson,
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
