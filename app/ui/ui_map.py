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

RISK_CATEGORY_MAP = {
    "alta prioridad": "Alta prioridad",
    "alta": "Alta prioridad",
    "alto": "Alta prioridad",
    "vigilancia preventiva": "Vigilancia preventiva",
    "media": "Vigilancia preventiva",
    "medio": "Vigilancia preventiva",
    "media alta": "Vigilancia preventiva",
    "media-alta": "Vigilancia preventiva",
    "media_alta": "Vigilancia preventiva",
    "medio alto": "Vigilancia preventiva",
    "medio-alto": "Vigilancia preventiva",
    "seguimiento rutinario": "Seguimiento rutinario",
    "baja": "Seguimiento rutinario",
    "bajo": "Seguimiento rutinario",
    "n/d": "N/D",
    "nd": "N/D",
    "": "N/D",
}

RISK_COLOR_MAP = {
    "Alta prioridad": "#e74c3c",
    "Vigilancia preventiva": "#f39c12",
    "Seguimiento rutinario": "#2ecc71",
    "N/D": "#bdc3c7",
}

RISK_CATEGORY_ORDER = [
    "Seguimiento rutinario",
    "Vigilancia preventiva",
    "Alta prioridad",
]


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

    customdata = point.get("customdata")

    if isinstance(customdata, (list, tuple)):
        for item in customdata:
            candidate = _safe_str(item)
            if candidate:
                canon = canonical_province(candidate)
                if canon:
                    return canon

    elif customdata is not None:
        candidate = _safe_str(customdata)
        if candidate:
            canon = canonical_province(candidate)
            if canon:
                return canon

    for key in ("location", "text", "hovertext"):
        candidate = _safe_str(point.get(key))
        if candidate:
            canon = canonical_province(candidate)
            if canon:
                return canon

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
    matched_df = matched_df.drop_duplicates(subset=["provincia"]).reset_index(drop=True)

    return matched_df, unmatched


def _normalize_risk_category(value: Any) -> str:
    raw = _safe_str(value)
    if not raw:
        return "N/D"

    text = normalize_text(raw)
    if text in RISK_CATEGORY_MAP:
        return RISK_CATEGORY_MAP[text]

    if raw in {"Alta prioridad", "Vigilancia preventiva", "Seguimiento rutinario", "N/D"}:
        return raw

    return raw


def _build_base_geo_layer(
    geo_source: dict[str, Any],
    featureidkey: str,
) -> go.Choropleth:
    features = geo_source.get("features", []) or []
    all_locations: list[str] = []

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
        name="Base",
    )


def _format_hover_number(value: Any, decimals: int = 2, signed: bool = False) -> str:
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return "N/D"
    return f"{float(numeric):+.{decimals}f}" if signed else f"{float(numeric):.{decimals}f}"


def _build_hover_fields(df: pd.DataFrame) -> pd.DataFrame:
    plot_df = df.copy()

    plot_df["hover_score_riesgo"] = plot_df.get(
        "score_riesgo",
        pd.Series(index=plot_df.index),
    ).map(lambda x: _format_hover_number(x, decimals=3, signed=False))

    plot_df["hover_pred_fallecidos_next"] = plot_df.get(
        "pred_fallecidos_next",
        pd.Series(index=plot_df.index),
    ).map(lambda x: _format_hover_number(x, decimals=2, signed=False))

    plot_df["hover_delta_abs"] = plot_df.get(
        "delta_abs",
        pd.Series(index=plot_df.index),
    ).map(lambda x: _format_hover_number(x, decimals=2, signed=True))

    plot_df["hover_categoria"] = (
        plot_df.get("categoria", pd.Series(index=plot_df.index))
        .map(_normalize_risk_category)
        .fillna("N/D")
    )

    plot_df["hover_ranking_posicion"] = plot_df.get(
        "ranking_posicion",
        pd.Series(index=plot_df.index),
    ).map(lambda x: f"#{int(x)}" if pd.notna(pd.to_numeric(x, errors="coerce")) else "N/D")

    return plot_df


def _build_hover_template_full() -> str:
    return (
        "<b>%{customdata[0]}</b><br>"
        "Score de riesgo: %{customdata[1]}<br>"
        "Predicción siguiente: %{customdata[2]}<br>"
        "Δ abs.: %{customdata[3]}<br>"
        "Categoría DSS: %{customdata[4]}<br>"
        "Posición: %{customdata[5]}"
        "<extra></extra>"
    )


def _build_categorical_trace(
    subset: pd.DataFrame,
    geo_source: dict[str, Any],
    featureidkey: str,
    category_name: str,
) -> go.Choropleth:
    color = RISK_COLOR_MAP.get(category_name, RISK_COLOR_MAP["N/D"])

    subset = _build_hover_fields(subset.copy())
    subset["provincia_click"] = subset["provincia"].astype(str).str.strip()

    customdata = list(
        zip(
            subset["provincia_click"],
            subset["hover_score_riesgo"],
            subset["hover_pred_fallecidos_next"],
            subset["hover_delta_abs"],
            subset["hover_categoria"],
            subset["hover_ranking_posicion"],
            strict=False,
        )
    )

    return go.Choropleth(
        geojson=geo_source,
        locations=subset["geo_match_name"].tolist(),
        z=[1] * len(subset),
        featureidkey=featureidkey,
        colorscale=[[0.0, color], [1.0, color]],
        showscale=False,
        marker_line_color="white",
        marker_line_width=0.7,
        customdata=customdata,
        hovertemplate=_build_hover_template_full(),
        name=category_name,
    )


def _build_numeric_map_figure(
    plot_df: pd.DataFrame,
    geo_source: dict[str, Any],
    featureidkey: str,
    color_col: str,
    title: str,
):
    numeric_series = pd.to_numeric(plot_df[color_col], errors="coerce")

    if numeric_series.notna().any():
        vmin = float(numeric_series.min())
        vmax = float(numeric_series.max())
    else:
        vmin, vmax = 0.0, 1.0

    if vmin == vmax:
        vmax = vmin + 1e-6

    is_diverging = color_col == "delta_pct"

    if is_diverging:
        abs_max = float(numeric_series.abs().max()) if numeric_series.notna().any() else 1.0
        abs_max = abs_max if abs_max > 0 else 1.0
        range_color = (-abs_max, abs_max)
        color_scale = "RdYlGn_r"
    else:
        range_color = (vmin, vmax)
        color_scale = "Turbo"

    choropleth = px.choropleth(
        plot_df,
        geojson=geo_source,
        locations="geo_match_name",
        featureidkey=featureidkey,
        color=color_col,
        hover_name="provincia",
        custom_data=[
            "provincia",
            "hover_score_riesgo",
            "hover_pred_fallecidos_next",
            "hover_delta_abs",
            "hover_categoria",
            "hover_ranking_posicion",
        ],
        title=title,
        color_continuous_scale=color_scale,
        range_color=range_color,
    )

    colorbar_title = color_col.replace("_", " ").title()
    if color_col == "delta_pct":
        colorbar_title = "Delta %"

    choropleth.update_traces(
        marker_line_width=0.7,
        marker_line_color="white",
        hovertemplate=_build_hover_template_full(),
    )

    choropleth.update_layout(
        coloraxis_colorbar=dict(
            title=colorbar_title,
            thickness=18,
            len=0.78,
            y=0.5,
            yanchor="middle",
            outlinewidth=0,
            tickfont=dict(size=11, color="#cbd5e1"),
            titlefont=dict(size=12, color="#e2e8f0"),
        )
    )

    return choropleth


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

        nd_subset = plot_df[
            ~plot_df["categoria_normalizada"].isin(RISK_CATEGORY_ORDER)
        ].copy()

        if not nd_subset.empty:
            nd_subset["categoria_normalizada"] = "N/D"
            figure.add_trace(
                _build_categorical_trace(
                    subset=nd_subset,
                    geo_source=geo_source,
                    featureidkey=featureidkey,
                    category_name="N/D",
                )
            )
    else:
        plot_df = _build_hover_fields(plot_df)

        numeric_fig = _build_numeric_map_figure(
            plot_df=plot_df,
            geo_source=geo_source,
            featureidkey=featureidkey,
            color_col=color_col,
            title=title,
        )

        for trace in numeric_fig.data:
            figure.add_trace(trace)

        if hasattr(numeric_fig.layout, "coloraxis") and numeric_fig.layout.coloraxis:
            figure.update_layout(coloraxis=numeric_fig.layout.coloraxis)

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
        bgcolor="rgba(0,0,0,0)",
    )

    layout_kwargs = dict(
        title=title,
        margin=dict(l=0, r=0, t=60, b=0),
        height=620,
        clickmode="event+select",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            title="Nivel de riesgo DSS",
            orientation="v",
        ),
    )

    if not is_categorical_risk:
        layout_kwargs["legend_title_text"] = color_col.replace("_", " ").title()

    figure.update_layout(**layout_kwargs)

    return {
        "figure": figure,
        "matched_df": matched_df,
        "unmatched_provinces": unmatched_provinces,
    }