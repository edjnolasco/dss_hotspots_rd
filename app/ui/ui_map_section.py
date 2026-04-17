from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_plotly_events import plotly_events

from src.debug_tools import render_geo_debug_panel, should_debug_map_click
from src.glossary import get_tooltip
from src.province_utils import canonical_province
from ui.ui_map import (
    build_geo_quality_summary,
    build_map_cached,
    load_geojson_source,
    should_accept_map_click,
)
from ui.ui_sections import render_province_drilldown
from ui.ui_theme import get_category_theme


def resolve_clicked_province_from_plotly_event(
    selected_points: list[dict[str, Any]] | None,
    figure: Any,
    matched_df: pd.DataFrame,
) -> str | None:
    if not selected_points:
        return None

    point = selected_points[0] or {}
    curve_number = point.get("curveNumber")
    point_index = point.get("pointIndex")

    if not isinstance(curve_number, int) or not isinstance(point_index, int):
        return None

    try:
        trace = figure.data[curve_number]
    except Exception:
        return None

    customdata = getattr(trace, "customdata", None)
    if customdata is not None:
        try:
            item = customdata[point_index]
            if isinstance(item, str):
                candidate = item.strip()
                if candidate:
                    return candidate
            if isinstance(item, (list, tuple)) and len(item) > 0:
                candidate = str(item[0]).strip()
                if candidate:
                    return candidate
        except Exception:
            pass

    locations = getattr(trace, "locations", None)
    if locations is not None:
        try:
            geo_name = str(locations[point_index]).strip()
            if geo_name and not matched_df.empty:
                match = matched_df.loc[
                    matched_df["geo_match_name"].astype(str).str.strip() == geo_name,
                    "provincia",
                ]
                if not match.empty:
                    return str(match.iloc[0]).strip()
        except Exception:
            pass

    return None


def _normalize_text_value(value: Any) -> str:
    return str(value or "").strip()


def _canonical_value(value: Any) -> str:
    raw = _normalize_text_value(value)
    if not raw:
        return ""
    try:
        return canonical_province(raw)
    except Exception:
        return raw.casefold()


def filter_geojson_for_focus(
    geojson: dict,
    geo_match_name: str | None,
    province_name: str | None,
) -> dict:
    """
    Filtra el GeoJSON para dejar únicamente la geometría de la provincia en foco.
    """
    features = geojson.get("features", [])
    if not features:
        return {"type": "FeatureCollection", "features": []}

    geo_match_name_raw = _normalize_text_value(geo_match_name)
    province_name_raw = _normalize_text_value(province_name)

    geo_match_name_lower = geo_match_name_raw.lower()
    province_name_lower = province_name_raw.lower()

    geo_match_name_canon = _canonical_value(geo_match_name_raw)
    province_name_canon = _canonical_value(province_name_raw)

    exact_geo_match_features = []
    exact_province_features = []
    canonical_features = []

    for feature in features:
        props = feature.get("properties", {}) or {}
        name_1 = _normalize_text_value(props.get("NAME_1", ""))
        name_1_lower = name_1.lower()
        name_1_canon = _canonical_value(name_1)

        if geo_match_name_raw and name_1_lower == geo_match_name_lower:
            exact_geo_match_features.append(feature)
            continue

        if province_name_raw and name_1_lower == province_name_lower:
            exact_province_features.append(feature)
            continue

        if (
            geo_match_name_canon
            and name_1_canon
            and name_1_canon == geo_match_name_canon
        ) or (
            province_name_canon
            and name_1_canon
            and name_1_canon == province_name_canon
        ):
            canonical_features.append(feature)

    if exact_geo_match_features:
        selected = exact_geo_match_features
    elif exact_province_features:
        selected = exact_province_features
    else:
        selected = canonical_features

    return {
        "type": "FeatureCollection",
        "features": selected,
    }


def _resolve_focus_feature_name(focus_geojson: dict) -> str | None:
    features = focus_geojson.get("features", [])
    if not features:
        return None

    try:
        props = features[0].get("properties", {}) or {}
        name_1 = _normalize_text_value(props.get("NAME_1", ""))
        return name_1 or None
    except Exception:
        return None


def build_focus_map_figure(
    focus_df: pd.DataFrame,
    focus_geojson: dict,
    metric_column: str,
) -> Any:
    """
    Construye un mapa focalizado solo con la provincia seleccionada.
    """
    if focus_df.empty or not focus_geojson.get("features"):
        return None

    focus_feature_name = _resolve_focus_feature_name(focus_geojson)
    if not focus_feature_name:
        return None

    plot_df = focus_df.head(1).copy()
    plot_df["focus_location_name"] = focus_feature_name

    plot_df["hover_score_riesgo"] = pd.to_numeric(
        plot_df.get("score_riesgo"),
        errors="coerce",
    ).map(lambda x: f"{x:.3f}" if pd.notna(x) else "N/D")

    plot_df["hover_pred_fallecidos_next"] = pd.to_numeric(
        plot_df.get("pred_fallecidos_next"),
        errors="coerce",
    ).map(lambda x: f"{x:.2f}" if pd.notna(x) else "N/D")

    plot_df["hover_delta_abs"] = pd.to_numeric(
        plot_df.get("delta_abs"),
        errors="coerce",
    ).map(lambda x: f"{x:+.2f}" if pd.notna(x) else "N/D")

    plot_df["hover_categoria"] = (
        plot_df.get("categoria", pd.Series(index=plot_df.index))
        .astype(str)
        .replace({"": "N/D"})
    )

    plot_df["hover_ranking_posicion"] = pd.to_numeric(
        plot_df.get("ranking_posicion"),
        errors="coerce",
    ).map(lambda x: f"#{int(x)}" if pd.notna(x) else "N/D")

    if metric_column == "categoria":
        category_rank_map = {
            "Seguimiento rutinario": 1,
            "Vigilancia preventiva": 2,
            "Alta prioridad": 3,
            "N/D": 0,
        }
        plot_df["_focus_color_value"] = (
            plot_df["categoria"].astype(str).map(category_rank_map).fillna(0)
        )
        color_col = "_focus_color_value"
    else:
        color_col = metric_column

    fig = px.choropleth(
        plot_df,
        geojson=focus_geojson,
        locations="focus_location_name",
        featureidkey="properties.NAME_1",
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
    )

    fig.update_geos(
        fitbounds="geojson",
        visible=False,
        showcountries=False,
        showcoastlines=False,
        showland=False,
        showframe=False,
        bgcolor="rgba(0,0,0,0)",
    )

    fig.update_traces(
        marker_line_width=1.8,
        marker_line_color="rgba(255,255,255,0.92)",
        showscale=False,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Score de riesgo: %{customdata[1]}<br>"
            "Predicción siguiente: %{customdata[2]}<br>"
            "Δ abs.: %{customdata[3]}<br>"
            "Categoría DSS: %{customdata[4]}<br>"
            "Posición: %{customdata[5]}"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=360,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        uirevision="focus-map",
        coloraxis_showscale=False,
    )

    return fig


def _build_normalized_map_dataframe(
    filtered_ranking: pd.DataFrame,
    metric_column: str,
    normalize_visual_scale: bool,
) -> tuple[pd.DataFrame, str, str]:
    """
    Devuelve:
    - dataframe a mostrar en el mapa,
    - columna real usada para color,
    - etiqueta amigable para la variable.
    """
    map_df = filtered_ranking.copy()

    friendly_labels = {
        "categoria": "Categoría DSS",
        "score_riesgo": "Score de riesgo",
        "fallecidos_actuales": "Fallecidos actuales",
        "pred_fallecidos_next": "Predicción próxima",
        "delta_pct": "Delta %",
    }

    metric_label = friendly_labels.get(metric_column, metric_column.replace("_", " ").title())

    if metric_column == "categoria":
        return map_df, "categoria", metric_label

    if metric_column == "delta_pct":
        return map_df, "delta_pct", metric_label

    if not normalize_visual_scale:
        return map_df, metric_column, metric_label

    numeric_values = pd.to_numeric(map_df[metric_column], errors="coerce")
    temp_col = f"{metric_label} (normalizado)"

    if numeric_values.notna().any():
        vmin = float(numeric_values.min())
        vmax = float(numeric_values.max())

        if vmin == vmax:
            map_df[temp_col] = 1.0
        else:
            map_df[temp_col] = (numeric_values - vmin) / (vmax - vmin)
    else:
        map_df[temp_col] = 0.0

    return map_df, temp_col, f"{metric_label} (normalizado)"


def _build_map_insight(
    filtered_ranking: pd.DataFrame,
    metric_column: str,
    metric_label: str,
    selected_year_label: str,
    selected_years: list[int],
    show_top_only: bool,
    top_n: int,
    normalize_visual_scale: bool,
) -> str:
    if filtered_ranking.empty:
        return "No hay suficientes datos visibles para generar un insight automático del mapa."

    ranking = filtered_ranking.copy()

    if "categoria" in ranking.columns:
        ranking["categoria"] = ranking["categoria"].astype(str).fillna("N/D")

    top_row = ranking.iloc[0]
    provincia_lider = str(top_row.get("provincia", "N/D"))
    categoria_lider = str(top_row.get("categoria", "N/D"))

    intro = (
        f"Período visible: {selected_year_label}. "
        f"La provincia que lidera el ranking actual es {provincia_lider}, "
        f"clasificada en {categoria_lider}."
    )

    if metric_column == "categoria":
        counts = ranking["categoria"].value_counts(dropna=False)
        alta = int(counts.get("Alta prioridad", 0))
        vigilancia = int(counts.get("Vigilancia preventiva", 0))
        rutina = int(counts.get("Seguimiento rutinario", 0))

        body = (
            f"En la salida DSS se observan {alta} provincias en alta prioridad, "
            f"{vigilancia} en vigilancia preventiva y {rutina} en seguimiento rutinario."
        )
    else:
        values = pd.to_numeric(ranking.get(metric_column), errors="coerce").dropna()

        if values.empty:
            body = (
                f"La variable seleccionada ({metric_label}) no presenta valores suficientes "
                "para interpretar contraste territorial."
            )
        else:
            values_abs = values.abs()
            total_abs = float(values_abs.sum()) if float(values_abs.sum()) > 0 else 0.0
            top3_abs = float(values_abs.head(min(3, len(values_abs))).sum()) if not values_abs.empty else 0.0

            concentration = (top3_abs / total_abs) if total_abs > 0 else 0.0

            if concentration >= 0.45:
                pattern = "alta concentración territorial"
            elif concentration >= 0.30:
                pattern = "concentración intermedia"
            else:
                pattern = "distribución relativamente difusa"

            if metric_column == "delta_pct":
                positivos = int((values > 0).sum())
                negativos = int((values < 0).sum())
                body = (
                    f"La variable {metric_label} muestra {pattern}. "
                    f"Se identifican {positivos} provincias con incremento relativo y "
                    f"{negativos} con reducción relativa."
                )
            else:
                max_value = float(values.max())
                min_value = float(values.min())
                body = (
                    f"La variable {metric_label} presenta {pattern}. "
                    f"El rango visible va desde {min_value:.2f} hasta {max_value:.2f}."
                )

    temporal_text = ""

    is_multi_year = len(selected_years) > 1
    if is_multi_year and "delta_pct" in ranking.columns:
        delta_series = pd.to_numeric(ranking["delta_pct"], errors="coerce").dropna()

        if not delta_series.empty:
            fuertes_alzas = int((delta_series >= 20).sum())
            fuertes_bajas = int((delta_series <= -20).sum())

            delta_num = pd.to_numeric(ranking["delta_pct"], errors="coerce")
            top_up = ranking.loc[delta_num.fillna(float("-inf")).idxmax()]
            top_down = ranking.loc[delta_num.fillna(float("inf")).idxmin()]

            max_up = float(pd.to_numeric(top_up.get("delta_pct"), errors="coerce"))
            max_down = float(pd.to_numeric(top_down.get("delta_pct"), errors="coerce"))

            if fuertes_alzas == 0 and fuertes_bajas == 0:
                temporal_text = (
                    " En la comparación entre años visibles no se observan cambios relativos "
                    "de gran magnitud; el patrón territorial luce relativamente estable."
                )
            else:
                temporal_parts: list[str] = []

                if fuertes_alzas > 0:
                    temporal_parts.append(
                        f"{fuertes_alzas} provincias muestran aumentos relevantes "
                        f"(≥ 20%), destacándose {top_up.get('provincia', 'N/D')} "
                        f"con {max_up:.2f}%"
                    )

                if fuertes_bajas > 0:
                    temporal_parts.append(
                        f"{fuertes_bajas} provincias muestran reducciones relevantes "
                        f"(≤ -20%), destacándose {top_down.get('provincia', 'N/D')} "
                        f"con {max_down:.2f}%"
                    )

                temporal_text = (
                    " En perspectiva temporal, "
                    + "; ".join(temporal_parts)
                    + "."
                )

    context = (
        f"El mapa está mostrando solo el Top-{top_n} visible."
        if show_top_only
        else "El mapa está mostrando todas las provincias visibles según los filtros activos."
    )

    if normalize_visual_scale and metric_column not in {"categoria", "delta_pct"}:
        context += " La escala visual fue normalizada para resaltar diferencias relativas."

    return f"{intro} {body}{temporal_text} {context}"


def _render_comparison_panel(
    filtered_ranking: pd.DataFrame,
    focus_province: str,
    compare_province: str,
) -> None:
    if not focus_province or not compare_province or focus_province == compare_province:
        return

    left_df = filtered_ranking[filtered_ranking["provincia"] == focus_province].copy()
    right_df = filtered_ranking[filtered_ranking["provincia"] == compare_province].copy()

    if left_df.empty or right_df.empty:
        return

    left = left_df.iloc[0]
    right = right_df.iloc[0]

    st.markdown("### Comparación provincial")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"**{focus_province}**")
        st.metric("Score de riesgo", f"{float(left['score_riesgo']):.3f}")
        st.metric("Predicción próxima", f"{float(left['pred_fallecidos_next']):.2f}")
        st.metric("Δ abs.", f"{float(pd.to_numeric(left.get('delta_abs', 0.0), errors='coerce')):+.2f}")
        st.metric(
            "Posición",
            "N/D" if pd.isna(left.get("ranking_posicion")) else f"#{int(left['ranking_posicion'])}",
        )
        st.caption(f"Categoría DSS: {left.get('categoria', 'N/D')}")

    with c2:
        st.markdown(f"**{compare_province}**")
        st.metric("Score de riesgo", f"{float(right['score_riesgo']):.3f}")
        st.metric("Predicción próxima", f"{float(right['pred_fallecidos_next']):.2f}")
        st.metric("Δ abs.", f"{float(pd.to_numeric(right.get('delta_abs', 0.0), errors='coerce')):+.2f}")
        st.metric(
            "Posición",
            "N/D" if pd.isna(right.get("ranking_posicion")) else f"#{int(right['ranking_posicion'])}",
        )
        st.caption(f"Categoría DSS: {right.get('categoria', 'N/D')}")

    score_diff = float(left["score_riesgo"]) - float(right["score_riesgo"])
    pred_diff = float(left["pred_fallecidos_next"]) - float(right["pred_fallecidos_next"])

    if score_diff > 0:
        lead_text = f"{focus_province} presenta mayor intensidad relativa de riesgo."
    elif score_diff < 0:
        lead_text = f"{compare_province} presenta mayor intensidad relativa de riesgo."
    else:
        lead_text = "Ambas provincias presentan intensidad relativa de riesgo equivalente."

    st.markdown(
        f"""
        <div style="
            border-radius: 12px;
            padding: 12px 14px;
            margin-top: 6px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            background: rgba(30, 41, 59, 0.35);
        ">
            <strong>Lectura comparativa:</strong>
            {lead_text}
            Diferencia de score: <strong>{score_diff:+.3f}</strong>.
            Diferencia de predicción próxima: <strong>{pred_diff:+.2f}</strong>.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_map_section(
    *,
    geo_mode: str,
    geo_local_path: str,
    uploaded_geo: Any,
    filtered_ranking: pd.DataFrame,
    metric_column: str,
    selected_year_label: str,
    show_top_only: bool,
    top_n: int,
    province_options: list[str],
    scored_df: pd.DataFrame,
    selected_years: list[int],
    set_selected_province_fn: Callable[[str | None], bool],
    build_rule_trace_text_fn: Callable[[pd.Series], str],
    build_recommendation_text_fn: Callable[[pd.Series], str],
) -> None:
    if geo_mode == "Omitir mapa":
        st.info("Mapa omitido.")
        return

    try:
        geo_source = load_geojson_source(
            geo_mode=geo_mode,
            geo_local_path=geo_local_path,
            uploaded_geo=uploaded_geo,
        )

        if geo_source is None:
            st.info("Sube un archivo GeoJSON.")
            return

        normalize_visual_scale = st.checkbox(
            "Normalización visual opcional",
            value=False,
            key="normalize_visual_scale_map",
            help=(
                "Reescala visualmente la variable numérica entre 0 y 1 para resaltar "
                "diferencias relativas entre provincias. No altera el ranking ni los valores reales. "
                "No se aplica a Categoría DSS ni a Delta %."
            ),
        )

        map_display_df, map_color_col, map_metric_label = _build_normalized_map_dataframe(
            filtered_ranking=filtered_ranking,
            metric_column=metric_column,
            normalize_visual_scale=normalize_visual_scale,
        )

        selected_province = st.session_state.get("selected_province")

        map_result = build_map_cached(
            df_map=map_display_df,
            geo_source=geo_source,
            color_col=map_color_col,
            title=f"Mapa nacional por provincia - {selected_year_label}",
            selected_province=selected_province,
        )

        left_map_col, right_focus_col = st.columns([1.45, 1.15])

        with left_map_col:
            with st.container(border=True):
                st.markdown("### Vista nacional")
                st.caption(
                    f"Distribución espacial de la variable seleccionada: {map_metric_label}."
                )

                figure = map_result["figure"]
                selected_points = plotly_events(
                    figure,
                    click_event=True,
                    select_event=False,
                    hover_event=False,
                    override_height=620,
                    key=(
                        f"plotly_click_map_{selected_year_label}_{metric_column}_"
                        f"{show_top_only}_{top_n}_{len(province_options)}_"
                        f"{normalize_visual_scale}"
                    ),
                )

                clicked_province = resolve_clicked_province_from_plotly_event(
                    selected_points=selected_points,
                    figure=figure,
                    matched_df=map_result["matched_df"],
                )

                if clicked_province:
                    clicked_province = str(clicked_province).strip()

                normalized_options = {str(p).strip(): p for p in province_options}

                if clicked_province in normalized_options:
                    clicked_province = normalized_options[clicked_province]
                else:
                    clicked_province = None

                debug_map_click = should_debug_map_click()

                if debug_map_click:
                    st.write("selected_points:", selected_points)
                    st.write("clicked_province:", clicked_province)

                if clicked_province and should_accept_map_click(clicked_province):
                    current_selected = st.session_state.get("selected_province")
                    if str(current_selected).strip() != str(clicked_province).strip():
                        if set_selected_province_fn(clicked_province):
                            st.rerun()

                if debug_map_click:
                    with st.expander("Debug del clic del mapa", expanded=False):
                        st.write("selected_points:", selected_points)
                        st.write("clicked_province:", clicked_province)
                        st.write("province_options:", province_options)
                        matched_preview = map_result["matched_df"].copy()
                        debug_cols = [
                            col
                            for col in [
                                "provincia",
                                "provincia_canon",
                                "geo_match_name",
                                map_color_col,
                            ]
                            if col in matched_preview.columns
                        ]
                        if debug_cols:
                            st.dataframe(
                                matched_preview[debug_cols],
                                width="stretch",
                            )
                        else:
                            st.dataframe(
                                matched_preview.head(10),
                                width="stretch",
                            )

                coverage, unmatched_count = build_geo_quality_summary(
                    base_ranking_df=filtered_ranking,
                    unmatched_provinces=map_result.get("unmatched_provinces", []),
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

                render_geo_debug_panel(
                    coverage=coverage,
                    unmatched_count=unmatched_count,
                    unmatched_provinces=unmatched_provinces,
                    matched_df=map_result["matched_df"],
                    metric_column=map_color_col,
                )

                map_insight = _build_map_insight(
                    filtered_ranking=filtered_ranking,
                    metric_column=metric_column,
                    metric_label=map_metric_label,
                    selected_year_label=selected_year_label,
                    selected_years=selected_years,
                    show_top_only=show_top_only,
                    top_n=top_n,
                    normalize_visual_scale=normalize_visual_scale,
                )

                st.markdown(
                    f"""
                    <div style="
                        border-radius: 12px;
                        padding: 12px 14px;
                        margin-top: 8px;
                        border: 1px solid rgba(148, 163, 184, 0.18);
                        background: rgba(30, 41, 59, 0.32);
                    ">
                        <strong>Insight automático del mapa:</strong> {map_insight}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.caption(
                    "Haz clic sobre una provincia en el mapa nacional para actualizar la vista focalizada y dejarla marcada."
                )

        with right_focus_col:
            with st.container(border=True):
                st.markdown("### Vista focalizada")
                st.caption(
                    "Detalle ejecutivo de la provincia actualmente seleccionada."
                )

                current_selected = st.session_state.get("selected_province")
                if current_selected not in province_options and province_options:
                    current_selected = province_options[0]
                    st.session_state["selected_province"] = current_selected

                if province_options:
                    widget_focus = st.session_state.get("province_focus_selectbox")
                    if widget_focus not in province_options:
                        st.session_state["province_focus_selectbox"] = current_selected

                province_from_ui = st.selectbox(
                    "Provincia en foco",
                    options=province_options,
                    key="province_focus_selectbox",
                )

                if province_from_ui != st.session_state.get("selected_province"):
                    st.session_state["selected_province"] = province_from_ui

                clear_selection = st.button(
                    "Restablecer foco",
                    width="stretch",
                    key="clear_province_selection",
                )
                if clear_selection and province_options:
                    default_focus = province_options[0]
                    st.session_state["selected_province"] = default_focus
                    st.rerun()

                comparison_enabled = st.checkbox(
                    "Modo comparación",
                    value=False,
                    key="comparison_mode_enabled",
                )

                compare_province = None
                if comparison_enabled:
                    compare_candidates = [
                        p for p in province_options
                        if p != st.session_state.get("selected_province")
                    ]
                    if compare_candidates:
                        compare_province = st.selectbox(
                            "Provincia a comparar",
                            options=compare_candidates,
                            key="province_compare_selectbox",
                        )

                selected_focus_name = st.session_state.get("selected_province")

                focus_df = filtered_ranking[
                    filtered_ranking["provincia"] == selected_focus_name
                ].copy()

                if focus_df.empty and province_options:
                    fallback_province = province_options[0]
                    st.session_state["selected_province"] = fallback_province
                    focus_df = filtered_ranking[
                        filtered_ranking["provincia"] == fallback_province
                    ].copy()
                    selected_focus_name = fallback_province

                geo_match_name = None
                if not focus_df.empty and "geo_match_name" in focus_df.columns:
                    geo_match_name = str(focus_df.iloc[0].get("geo_match_name", "")).strip()

                focus_geojson = filter_geojson_for_focus(
                    geojson=geo_source,
                    geo_match_name=geo_match_name,
                    province_name=selected_focus_name,
                )

                st.markdown(
                    f"<div style='margin-bottom:6px; font-weight:600;'>"
                    f"Provincia en foco - {selected_focus_name} ({selected_year_label})"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                st.markdown(
                    """
                    <style>
                    div[data-testid="stPlotlyChart"] {
                        animation: fadeFocusIn 0.25s ease-in-out;
                    }

                    @keyframes fadeFocusIn {
                        from {
                            opacity: 0.35;
                            transform: translateY(4px);
                        }
                        to {
                            opacity: 1;
                            transform: translateY(0);
                        }
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                focus_figure = build_focus_map_figure(
                    focus_df=focus_df,
                    focus_geojson=focus_geojson,
                    metric_column=metric_column,
                )

                focus_chart_placeholder = st.empty()

                if focus_figure is not None:
                    with focus_chart_placeholder.container():
                        with st.spinner("Actualizando vista focalizada..."):
                            st.plotly_chart(
                                focus_figure,
                                width="stretch",
                                config={"displaylogo": False},
                                key=(
                                    f"focus_map_{selected_focus_name}_"
                                    f"{selected_year_label}_{metric_column}"
                                ),
                            )
                else:
                    with focus_chart_placeholder.container():
                        st.info(
                            "No fue posible construir el mapa focalizado con la provincia seleccionada. "
                            "Se mantienen las métricas y la trazabilidad."
                        )

                    if should_debug_map_click():
                        with st.expander("Debug de vista focalizada", expanded=False):
                            st.write("selected_focus_name:", selected_focus_name)
                            st.write("geo_match_name:", geo_match_name)
                            st.write(
                                "selected_focus_canon:",
                                _canonical_value(selected_focus_name),
                            )
                            geo_names = [
                                str(
                                    (feature.get("properties", {}) or {}).get("NAME_1", "")
                                ).strip()
                                for feature in geo_source.get("features", [])
                            ]
                            debug_df = pd.DataFrame(
                                {
                                    "NAME_1": geo_names,
                                    "NAME_1_canon": [
                                        _canonical_value(name) for name in geo_names
                                    ],
                                }
                            )
                            st.dataframe(debug_df, width="stretch")

                if not focus_df.empty:
                    province_row = focus_df.iloc[0]

                    categoria = str(province_row.get("categoria", "N/D")).strip() or "N/D"
                    badge = get_category_theme(categoria)

                    st.markdown(
                        f"""
                        <div style="margin-bottom: 10px;">
                            <div style="font-size: 2rem; font-weight: 700; line-height: 1.1; margin-bottom: 10px;">
                                {province_row['provincia']}
                            </div>
                            <div style="
                                display: inline-block;
                                padding: 8px 12px;
                                border-radius: 999px;
                                border: 1px solid {badge['border']};
                                background: {badge['badge_bg']};
                                color: {badge['badge_text']};
                                font-weight: 600;
                                font-size: 0.95rem;
                            ">
                                {badge['label']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.caption(get_tooltip("Categoría DSS"))

                    m1, m2 = st.columns(2)
                    m3, m4 = st.columns(2)

                    m1.metric(
                        "Score actual",
                        f"{float(province_row['score_riesgo']):.3f}",
                        help=get_tooltip("Score actual"),
                    )

                    m2.metric(
                        "Predicción próxima",
                        f"{float(province_row['pred_fallecidos_next']):.2f}",
                        help=get_tooltip("Predicción próxima"),
                    )

                    delta_abs = float(
                        pd.to_numeric(province_row.get("delta_abs", 0.0), errors="coerce")
                    )
                    m3.metric(
                        "Δ abs.",
                        f"{delta_abs:+.2f}",
                        help=get_tooltip("Δ abs."),
                    )

                    ranking_pos = province_row.get("ranking_posicion", None)
                    ranking_text = "N/D" if pd.isna(ranking_pos) else f"#{int(ranking_pos)}"
                    m4.metric(
                        "Posición",
                        ranking_text,
                        help=get_tooltip("Posición"),
                    )

                    if comparison_enabled and compare_province:
                        _render_comparison_panel(
                            filtered_ranking=filtered_ranking,
                            focus_province=selected_focus_name,
                            compare_province=compare_province,
                        )

                    with st.container(border=True):
                        st.markdown("**Trazabilidad de la decisión**")

                        regla_text = str(province_row.get("regla_aplicada", "")).strip()
                        just_text = str(province_row.get("justificacion_regla", "")).strip()
                        rec_text = str(province_row.get("recomendacion", "")).strip()

                        if regla_text:
                            st.write(f"**Regla aplicada:** {regla_text}")

                        if just_text:
                            st.write(f"**Justificación:** {just_text}")
                        else:
                            st.write(build_rule_trace_text_fn(province_row))

                        if rec_text:
                            st.write(f"**Recomendación:** {rec_text}")
                        else:
                            st.write(build_recommendation_text_fn(province_row))

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("---")

        drill_year = int(max(selected_years))
        render_province_drilldown(
            scored_df=scored_df[scored_df["year"].isin(selected_years)].copy(),
            province_name=st.session_state["selected_province"],
            selected_year=drill_year,
        )

    except Exception as exc:
        st.warning(f"No fue posible generar el mapa: {exc}")