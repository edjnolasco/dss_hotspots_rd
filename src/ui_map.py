from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.province_utils import canonical_province, normalize_text


GEO_CANDIDATE_KEYS = [
    "NAME_1",
    "name",
    "NAME",
    "provincia",
    "Provincia",
    "PROVINCIA",
    "shapeName",
    "admin1Name",
    "nom_prov",
]

# Normalización robusta de categorías
RISK_CATEGORY_MAP = {
    "baja": "Baja",
    "bajo": "Baja",
    "media": "Media",
    "medio": "Media",
    "media alta": "Media-Alta",
    "media-alta": "Media-Alta",
    "media_alta": "Media-Alta",
    "medio alto": "Media-Alta",
    "medio-alto": "Media-Alta",
    "alta": "Alta",
    "alto": "Alta",
}

RISK_COLOR_MAP = {
    "Baja": "#48c774",
    "Media": "#d4c61c",
    "Media-Alta": "#ff8c42",
    "Alta": "#e74c3c",
}

RISK_CATEGORY_ORDER = ["Baja", "Media", "Media-Alta", "Alta"]


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _extract_feature_name(feature: dict[str, Any]) -> str:
    props = feature.get("properties", {}) or {}

    for key in GEO_CANDIDATE_KEYS:
        value = props.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()

    return ""


def _resolve_featureidkey(geojson_obj: dict[str, Any]) -> str:
    features = geojson_obj.get("features", []) or []
    if not features:
        return "properties.NAME_1"

    props = features[0].get("properties", {}) or {}

    for key in GEO_CANDIDATE_KEYS:
        if key in props:
            return f"properties.{key}"

    return "properties.NAME_1"


def _build_geo_lookup(geojson_obj: dict[str, Any]) -> dict[str, str]:
    lookup: dict[str, str] = {}

    for feature in geojson_obj.get("features", []) or []:
        raw_name = _extract_feature_name(feature)
        if not raw_name:
            continue

        raw_name = raw_name.strip()
        normalized_raw = normalize_text(raw_name)
        canonical_raw = canonical_province(raw_name)

        candidates = {
            raw_name,
            normalized_raw,
            canonical_raw,
            normalize_text(canonical_raw) if canonical_raw else "",
        }

        for candidate in candidates:
            candidate = _safe_str(candidate)
            if candidate:
                lookup[candidate] = raw_name

    return lookup


@st.cache_data(show_spinner=False)
def _load_geojson_from_path(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el GeoJSON en: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def _load_geojson_from_bytes(file_bytes: bytes) -> dict[str, Any]:
    return json.loads(file_bytes.decode("utf-8"))


def load_geojson_source(
    geo_mode: str,
    geo_local_path: str,
    uploaded_geo: Any,
) -> dict[str, Any] | None:
    if geo_mode == "Omitir mapa":
        return None

    if geo_mode == "Ruta local":
        if not geo_local_path:
            return None
        return _load_geojson_from_path(geo_local_path)

    if geo_mode == "Subir GeoJSON":
        if uploaded_geo is None:
            return None
        return _load_geojson_from_bytes(uploaded_geo.getvalue())

    return None


def build_geo_quality_summary(
    base_ranking_df: pd.DataFrame,
    unmatched_provinces: list[str],
) -> tuple[float, int]:
    total = int(len(base_ranking_df)) if base_ranking_df is not None else 0
    unmatched_count = len(unmatched_provinces)

    if total <= 0:
        return 0.0, unmatched_count

    matched = max(total - unmatched_count, 0)
    return (matched / total) * 100.0, unmatched_count


def should_accept_map_click(clicked_province: str | None) -> bool:
    return bool(clicked_province and str(clicked_province).strip())


def extract_selected_province_from_click(
    selected_points: list[dict[str, Any]] | None,
    fallback_df: pd.DataFrame,
) -> str | None:
    if not selected_points:
        return None

    point = selected_points[0] or {}

    valid_provinces: set[str] = set()
    if "provincia" in fallback_df.columns:
        valid_provinces = set(
            fallback_df["provincia"].dropna().astype(str).str.strip().tolist()
        )

    candidate_fields = [
        point.get("customdata"),
        point.get("location"),
        point.get("hovertext"),
        point.get("text"),
        point.get("x"),
        point.get("y"),
    ]

    for candidate in candidate_fields:
        if isinstance(candidate, (list, tuple)) and candidate:
            candidate = candidate[0]

        if candidate is None:
            continue

        candidate_str = _safe_str(candidate)
        if not candidate_str:
            continue

        candidate_canonical = canonical_province(candidate_str)

        if candidate_canonical and (
            not valid_provinces or candidate_canonical in valid_provinces
        ):
            return candidate_canonical

        candidate_normalized = normalize_text(candidate_str)
        for province in valid_provinces:
            if normalize_text(province) == candidate_normalized:
                return province

    point_index = point.get("pointIndex")
    if isinstance(point_index, int) and not fallback_df.empty:
        if 0 <= point_index < len(fallback_df):
            province = fallback_df.iloc[point_index].get("provincia")
            if province:
                return str(province).strip()

    return None


def _resolve_geo_match_name(province_name: str, geo_lookup: dict[str, str]) -> str | None:
    raw = _safe_str(province_name)
    if not raw:
        return None

    canonical = canonical_province(raw)
    normalized_raw = normalize_text(raw)
    normalized_canonical = normalize_text(canonical) if canonical else ""

    candidates = [raw, canonical, normalized_raw, normalized_canonical]

    for candidate in candidates:
        candidate = _safe_str(candidate)
        if candidate and candidate in geo_lookup:
            return geo_lookup[candidate]

    return None


def _prepare_map_dataframe(
    df_map: pd.DataFrame,
    geo_source: dict[str, Any],
) -> tuple[pd.DataFrame, list[str]]:
    if df_map is None or df_map.empty:
        return df_map.copy(), []

    if "provincia" not in df_map.columns:
        raise KeyError("El DataFrame del mapa no contiene la columna 'provincia'.")

    df = df_map.copy()
    df["provincia"] = df["provincia"].astype(str).str.strip()
    df["provincia_canon"] = df["provincia"].map(canonical_province)

    geo_lookup = _build_geo_lookup(geo_source)
    df["geo_match_name"] = df["provincia"].map(
        lambda x: _resolve_geo_match_name(x, geo_lookup)
    )

    unmatched = sorted(
        df.loc[df["geo_match_name"].isna(), "provincia"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    matched_df = df[df["geo_match_name"].notna()].copy()
    matched_df = matched_df.sort_values(["provincia"]).reset_index(drop=True)

    return matched_df, unmatched


def _build_hover_template_numeric(color_col: str) -> str:
    return (
        "<b>%{customdata[0]}</b><br>"
        + f"{color_col}: %{{z}}"
        + "<extra></extra>"
    )


def _normalize_risk_category(value: Any) -> str:
    text = normalize_text(value)
    return RISK_CATEGORY_MAP.get(text, _safe_str(value))


def _build_base_geo_layer(
    geo_source: dict[str, Any],
    featureidkey: str,
) -> go.Choropleth:
    features = geo_source.get("features", []) or []
    all_locations = []

    for feature in features:
        raw_name = _extract_feature_name(feature)
        if raw_name:
            all_locations.append(raw_name)

    return go.Choropleth(
        geojson=geo_source,
        locations=all_locations,
        z=[0] * len(all_locations),
        featureidkey=featureidkey,
        colorscale=[[0.0, "#d9d9d9"], [1.0, "#d9d9d9"]],
        showscale=False,
        marker_line_color="white",
        marker_line_width=0.7,
        hoverinfo="skip",
        name="Sin datos",
    )


def _build_categorical_trace(
    subset: pd.DataFrame,
    geo_source: dict[str, Any],
    featureidkey: str,
    category_name: str,
) -> go.Choropleth:
    color = RISK_COLOR_MAP[category_name]
    return go.Choropleth(
        geojson=geo_source,
        locations=subset["geo_match_name"].tolist(),
        z=[1] * len(subset),
        featureidkey=featureidkey,
        colorscale=[[0.0, color], [1.0, color]],
        showscale=False,
        marker_line_color="white",
        marker_line_width=0.7,
        customdata=subset[["provincia", "categoria_normalizada"]].values,
        hovertemplate="<b>%{customdata[0]}</b><br>categoria: %{customdata[1]}<extra></extra>",
        name=category_name,
    )


@st.cache_data(show_spinner=False)
def build_map_cached(
    df_map: pd.DataFrame,
    geo_source: dict[str, Any],
    color_col: str,
    title: str,
    selected_province: str | None = None,
) -> dict[str, Any]:
    matched_df, unmatched_provinces = _prepare_map_dataframe(
        df_map=df_map,
        geo_source=geo_source,
    )

    featureidkey = _resolve_featureidkey(geo_source)

    figure = go.Figure()
    figure.add_trace(_build_base_geo_layer(geo_source, featureidkey))

    if matched_df.empty:
        figure.update_geos(fitbounds="locations", visible=False)
        figure.update_layout(
            title=title,
            margin=dict(l=0, r=0, t=60, b=0),
            height=620,
            clickmode="event+select",
        )
        figure.add_annotation(
            text="No hay datos geográficos válidos para mostrar.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
        return {
            "figure": figure,
            "matched_df": matched_df,
            "unmatched_provinces": unmatched_provinces,
        }

    if color_col not in matched_df.columns:
        raise KeyError(f"La columna '{color_col}' no existe en el DataFrame del mapa.")

    plot_df = matched_df.copy()
    plot_df["is_selected"] = False
    if selected_province:
        selected_canonical = canonical_province(selected_province)
        plot_df["is_selected"] = (
            plot_df["provincia"].map(canonical_province) == selected_canonical
        )

    is_categorical_risk = color_col == "categoria"

    if is_categorical_risk:
        plot_df["categoria_normalizada"] = plot_df[color_col].map(_normalize_risk_category)

        for category_name in RISK_CATEGORY_ORDER:
            subset = plot_df[plot_df["categoria_normalizada"] == category_name].copy()
            if subset.empty:
                continue
            figure.add_trace(
                _build_categorical_trace(
                    subset=subset,
                    geo_source=geo_source,
                    featureidkey=featureidkey,
                    category_name=category_name,
                )
            )
    else:
        choropleth = px.choropleth(
            plot_df,
            geojson=geo_source,
            locations="geo_match_name",
            featureidkey=featureidkey,
            color=color_col,
            hover_name="provincia",
            custom_data=["provincia"],
            title=title,
        )

        choropleth.update_traces(
            marker_line_width=0.7,
            marker_line_color="white",
            hovertemplate=_build_hover_template_numeric(color_col),
        )

        for trace in choropleth.data:
            figure.add_trace(trace)

    if selected_province:
        selected_df = plot_df[plot_df["is_selected"]].copy()
        if not selected_df.empty:
            outline = go.Choropleth(
                geojson=geo_source,
                locations=selected_df["geo_match_name"].tolist(),
                z=[1] * len(selected_df),
                featureidkey=featureidkey,
                colorscale=[
                    [0.0, "rgba(0,0,0,0.01)"],
                    [1.0, "rgba(0,0,0,0.01)"],
                ],
                showscale=False,
                hoverinfo="skip",
                marker_line_width=4.5,
                marker_line_color="#000000",
                marker_opacity=0.35,
                name="Selección",
            )
            figure.add_trace(outline)

    figure.update_geos(
        fitbounds="locations",
        visible=False,
    )

    layout_kwargs = dict(
        margin=dict(l=0, r=0, t=60, b=0),
        height=620,
        clickmode="event+select",
        legend=dict(
            title="Nivel de riesgo",
            orientation="v",
        ),
    )

    if not is_categorical_risk:
        layout_kwargs["legend_title_text"] = color_col

    figure.update_layout(**layout_kwargs)

    return {
        "figure": figure,
        "matched_df": matched_df,
        "unmatched_provinces": unmatched_provinces,
    }