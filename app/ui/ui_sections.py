from __future__ import annotations

import html
import re
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.exporter import to_csv_bytes, to_excel_bytes
from src.glossary import get_tooltip
from src.narrative import format_executive_narrative

CATEGORY_COLOR_MAP = {
    "Alta prioridad": "#e74c3c",
    "Vigilancia preventiva": "#f39c12",
    "Seguimiento rutinario": "#2ecc71",
    "N/D": "#bdc3c7",
}


def safe_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    safe_df = df.copy().reset_index(drop=True)
    safe_df.columns = [str(col) for col in safe_df.columns]

    seen: dict[str, int] = {}
    normalized_columns: list[str] = []

    for col in safe_df.columns:
        if col not in seen:
            seen[col] = 0
            normalized_columns.append(col)
        else:
            seen[col] += 1
            normalized_columns.append(f"{col}_{seen[col]}")

    safe_df.columns = normalized_columns

    for col in safe_df.columns:
        safe_df[col] = safe_df[col].apply(
            lambda x: x
            if isinstance(x, (str, int, float, bool, type(None), pd.Timestamp))
            else str(x)
        )

    return safe_df


def _normalize_category_value(value: Any) -> str:
    if pd.isna(value):
        return "N/D"

    text = str(value).strip().lower()
    mapping = {
        "alta prioridad": "Alta prioridad",
        "alta": "Alta prioridad",
        "alto": "Alta prioridad",
        "vigilancia preventiva": "Vigilancia preventiva",
        "media": "Vigilancia preventiva",
        "medio": "Vigilancia preventiva",
        "media-alta": "Vigilancia preventiva",
        "seguimiento rutinario": "Seguimiento rutinario",
        "baja": "Seguimiento rutinario",
        "bajo": "Seguimiento rutinario",
    }
    return mapping.get(text, str(value))


def _category_rank(value: Any) -> int:
    text = str(value).strip().lower()
    mapping = {
        "alta prioridad": 3,
        "alta": 3,
        "alto": 3,
        "vigilancia preventiva": 2,
        "media": 2,
        "medio": 2,
        "media-alta": 2,
        "seguimiento rutinario": 1,
        "baja": 1,
        "bajo": 1,
    }
    return mapping.get(text, 0)


def _prepare_category_column(
    df: pd.DataFrame,
    source_col: str = "categoria",
) -> pd.DataFrame:
    prepared = df.copy()
    if source_col in prepared.columns:
        prepared[source_col] = prepared[source_col].apply(_normalize_category_value)
    return prepared


def _safe_key_part(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_\-]+", "", text)
    return text or "na"


def _build_chart_key(prefix: str, *parts: Any) -> str:
    counter_key = "_ui_sections_chart_counter_global"

    if counter_key not in st.session_state:
        st.session_state[counter_key] = 0

    st.session_state[counter_key] += 1
    render_counter = st.session_state[counter_key]

    safe_parts = [_safe_key_part(part) for part in parts]
    return "_".join([_safe_key_part(prefix), *safe_parts, f"r{render_counter}"])


def _build_ranking_signature(df: pd.DataFrame, top_items: int = 5) -> str:
    if df is None or df.empty or "provincia" not in df.columns:
        return "empty"
    provinces = df["provincia"].dropna().astype(str).head(top_items).tolist()
    if not provinces:
        return "empty"
    return "_".join(_safe_key_part(p) for p in provinces)


def _inject_kpi_styles() -> None:
    st.markdown(
        """
        <style>
        .exec-kpi-card {
            border-radius: 16px;
            padding: 14px 16px 12px 16px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            background: linear-gradient(
                180deg,
                rgba(15, 23, 42, 0.92) 0%,
                rgba(15, 23, 42, 0.84) 100%
            );
            min-height: 128px;
        }

        .exec-kpi-label {
            font-size: 0.84rem;
            color: #94a3b8;
            margin-bottom: 0.45rem;
            font-weight: 600;
            letter-spacing: 0.01em;
        }

        .exec-kpi-value {
            font-size: 1.9rem;
            line-height: 1.05;
            font-weight: 800;
            color: #f8fafc;
            margin-bottom: 0.35rem;
        }

        .exec-kpi-subvalue {
            font-size: 0.92rem;
            font-weight: 700;
            color: #cbd5e1;
            margin-bottom: 0.45rem;
        }

        .exec-kpi-caption {
            font-size: 0.83rem;
            line-height: 1.35;
            color: #94a3b8;
        }

        .exec-status-card {
            border-radius: 16px;
            padding: 14px 16px 12px 16px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            background: linear-gradient(
                180deg,
                rgba(15, 23, 42, 0.92) 0%,
                rgba(15, 23, 42, 0.84) 100%
            );
            min-height: 128px;
        }

        .exec-status-title {
            font-size: 0.95rem;
            font-weight: 800;
            color: #f8fafc;
            margin-bottom: 0.75rem;
        }

        .exec-status-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9rem;
            color: #e2e8f0;
            margin-bottom: 0.38rem;
            font-weight: 600;
        }

        .exec-status-dot {
            width: 10px;
            height: 10px;
            border-radius: 999px;
            display: inline-block;
            flex: 0 0 auto;
        }

        .exec-banner {
            border-radius: 16px;
            padding: 14px 16px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            background: linear-gradient(
                90deg,
                rgba(30, 41, 59, 0.95) 0%,
                rgba(15, 23, 42, 0.92) 100%
            );
            margin-top: 0.9rem;
            margin-bottom: 0.9rem;
        }

        .exec-banner-title {
            font-size: 0.9rem;
            font-weight: 700;
            color: #93c5fd;
            margin-bottom: 0.25rem;
        }

        .exec-banner-text {
            font-size: 0.88rem;
            color: #cbd5e1;
            line-height: 1.4;
        }

        .dss-text-desc {
            color: rgba(255, 255, 255, 0.76);
            font-size: 0.93rem;
            line-height: 1.45;
            margin-top: -4px;
            margin-bottom: 12px;
        }

        .dss-text-analytic {
            color: #7cc4ff;
            font-size: 0.95rem;
            line-height: 1.5;
            margin-top: -2px;
            margin-bottom: 14px;
            font-weight: 500;
        }

        .dss-text-analytic strong {
            color: #a8d8ff;
            font-weight: 700;
        }

        .dss-analytic-box {
            border-radius: 12px;
            padding: 12px 14px;
            margin-top: 6px;
            margin-bottom: 14px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            font-size: 0.94rem;
            line-height: 1.45;
        }

        .dss-analytic-box strong {
            font-weight: 700;
        }

        .dss-analytic-high {
            background: rgba(231, 76, 60, 0.12);
            border-left: 4px solid #e74c3c;
            color: #fca5a5;
        }

        .dss-analytic-medium {
            background: rgba(243, 156, 18, 0.12);
            border-left: 4px solid #f39c12;
            color: #fcd34d;
        }

        .dss-analytic-low {
            background: rgba(46, 204, 113, 0.12);
            border-left: 4px solid #2ecc71;
            color: #86efac;
        }

        .dss-analytic-neutral {
            background: rgba(148, 163, 184, 0.12);
            border-left: 4px solid #94a3b8;
            color: #cbd5e1;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _escape(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _format_int(value: Any) -> str:
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "N/D"


def _format_float(value: Any, decimals: int = 3) -> str:
    try:
        return (
            f"{float(value):,.{decimals}f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
    except (TypeError, ValueError):
        return "N/D"


def _build_exec_card_html(
    label: str,
    value: str,
    subvalue: str = "",
    caption: str = "",
) -> str:
    return (
        '<div class="exec-kpi-card">'
        f'<div class="exec-kpi-label">{_escape(label)}</div>'
        f'<div class="exec-kpi-value">{_escape(value)}</div>'
        f'<div class="exec-kpi-subvalue">{_escape(subvalue)}</div>'
        f'<div class="exec-kpi-caption">{_escape(caption)}</div>'
        "</div>"
    )


def _build_status_card_html(
    dataset_loaded: bool,
    pipeline_ok: bool,
    ranking_ok: bool,
    geo_mode: str,
) -> str:
    map_enabled = geo_mode != "Omitir mapa"

    def status_row(text: str, ok: bool) -> str:
        color = "#22c55e" if ok else "#f59e0b"
        return (
            '<div class="exec-status-item">'
            f'<span class="exec-status-dot" style="background:{color};"></span>'
            f"<span>{_escape(text)}</span>"
            "</div>"
        )

    return (
        '<div class="exec-status-card">'
        '<div class="exec-status-title">Estado del sistema</div>'
        f'{status_row("Dataset cargado", dataset_loaded)}'
        f'{status_row("Pipeline ejecutado", pipeline_ok)}'
        f'{status_row("Ranking disponible", ranking_ok)}'
        f'{status_row("Mapa habilitado", map_enabled)}'
        "</div>"
    )


def _render_text_desc(text: str) -> None:
    if not str(text).strip():
        return

    st.markdown(
        f"<div class='dss-text-desc'>{_escape(text)}</div>",
        unsafe_allow_html=True,
    )


def _render_text_analytic(text: str) -> None:
    if not str(text).strip():
        return

    st.markdown(
        f"<div class='dss-text-analytic'>{text}</div>",
        unsafe_allow_html=True,
    )


def _resolve_metric_from_results(results: dict[str, Any], *candidate_keys: str) -> Any:
    for key in candidate_keys:
        if key in results:
            return results.get(key)
    return None


def _get_dss_color_class(categoria: str) -> str:
    cat = str(categoria or "").strip().lower()

    if "alta" in cat:
        return "dss-analytic-high"
    if "vigilancia" in cat or "media" in cat:
        return "dss-analytic-medium"
    if "seguimiento" in cat or "baja" in cat or "bajo" in cat:
        return "dss-analytic-low"
    return "dss-analytic-neutral"


def _render_colored_dss_box(detail: dict[str, Any]) -> None:
    categoria = _normalize_category_value(detail.get("categoria", "N/D"))
    regla = str(detail.get("regla_aplicada", "")).strip() or "N/D"
    color_class = _get_dss_color_class(categoria)

    if detail.get("yoy_abs") is not None:
        yoy_abs = float(detail["yoy_abs"])
        if yoy_abs < 0:
            trend_text = "Se observa una <strong>reducción interanual</strong> en el indicador."
        elif yoy_abs > 0:
            trend_text = "Se observa un <strong>incremento interanual</strong> en el indicador."
        else:
            trend_text = "No se observa <strong>variación interanual relevante</strong>."
    else:
        trend_text = "No hay base suficiente para estimar la <strong>variación interanual</strong>."

    st.markdown(
        (
            f"<div class='dss-analytic-box {color_class}'>"
            f"Clasificación actual: <strong>{categoria}</strong>. "
            f"Regla DSS aplicada: <strong>{_escape(regla)}</strong>. "
            f"{trend_text}"
            f"</div>"
        ),
        unsafe_allow_html=True,
    )


def kpi_dashboard(ranking_df: pd.DataFrame, metric_column: str) -> go.Figure:
    if ranking_df.empty:
        fig = go.Figure()
        fig.update_layout(height=120, margin=dict(l=20, r=20, t=10, b=10))
        return fig

    ranking = ranking_df.copy()
    ranking = _prepare_category_column(ranking)

    if metric_column in ranking.columns:
        if metric_column == "categoria":
            ranking["_metric_sort"] = ranking[metric_column].apply(_category_rank)
        else:
            ranking["_metric_sort"] = pd.to_numeric(
                ranking[metric_column],
                errors="coerce",
            ).fillna(float("-inf"))

        ranking = ranking.sort_values(
            by=["_metric_sort", "provincia"],
            ascending=[False, True],
        ).reset_index(drop=True)

        ranking = ranking.drop(columns=["_metric_sort"])

    top1 = ranking.iloc[0]
    fig = go.Figure()

    fig.add_trace(
        go.Indicator(
            mode="number",
            value=1,
            title={"text": f"Provincia líder<br>{top1['provincia']}"},
            domain={"row": 0, "column": 0},
        )
    )

    fig.add_trace(
        go.Indicator(
            mode="number",
            value=float(top1["score_riesgo"]),
            number={"valueformat": ".3f"},
            title={"text": "Score líder"},
            domain={"row": 0, "column": 1},
        )
    )

    fig.add_trace(
        go.Indicator(
            mode="number",
            value=float(top1["pred_fallecidos_next"]),
            number={"valueformat": ".2f"},
            title={"text": "Predicción líder"},
            domain={"row": 0, "column": 2},
        )
    )

    metric_value = top1.get(metric_column)

    if metric_column == "categoria":
        metric_text = _normalize_category_value(metric_value)
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=0,
                title={
                    "text": (
                        f"{metric_column.replace('_', ' ').title()}"
                        f"<br><b>{metric_text}</b>"
                    )
                },
                number={"font": {"size": 1}},
                domain={"row": 0, "column": 3},
            )
        )
    else:
        try:
            numeric_value = float(metric_value)
        except (TypeError, ValueError):
            numeric_value = 0.0

        fig.add_trace(
            go.Indicator(
                mode="number",
                value=numeric_value,
                number={
                    "valueformat": ".2f"
                    if metric_column != "fallecidos_actuales"
                    else ".0f"
                },
                title={"text": metric_column.replace("_", " ").title()},
                domain={"row": 0, "column": 3},
            )
        )

    fig.update_layout(
        grid={"rows": 1, "columns": 4, "pattern": "independent"},
        height=220,
        margin=dict(l=20, r=20, t=10, b=10),
    )
    return fig


def build_year_ranking(scored_df: pd.DataFrame, selected_year: int) -> pd.DataFrame:
    filtered = scored_df[scored_df["year"] == selected_year].copy()
    if filtered.empty:
        return pd.DataFrame(
            columns=[
                "provincia",
                "pred_fallecidos_next",
                "score_riesgo",
                "categoria",
                "regla_aplicada",
                "justificacion_regla",
                "recomendacion",
                "fallecidos_actuales",
                "delta_abs",
                "delta_pct",
            ]
        )

    agg_dict: dict[str, Any] = {
        "pred_fallecidos_next": ("pred_fallecidos_next", "mean"),
        "score_riesgo": ("score_riesgo", "mean"),
        "categoria": ("categoria", "first"),
    }

    if "regla_aplicada" in filtered.columns:
        agg_dict["regla_aplicada"] = ("regla_aplicada", "first")
    if "justificacion_regla" in filtered.columns:
        agg_dict["justificacion_regla"] = ("justificacion_regla", "first")
    if "recomendacion" in filtered.columns:
        agg_dict["recomendacion"] = ("recomendacion", "first")

    if "fallecidos_actuales" in filtered.columns:
        agg_dict["fallecidos_actuales"] = ("fallecidos_actuales", "sum")
    else:
        agg_dict["fallecidos_actuales"] = ("fallecidos", "sum")

    ranking = (
        filtered.groupby("provincia", as_index=False)
        .agg(**agg_dict)
        .sort_values("score_riesgo", ascending=False)
        .reset_index(drop=True)
    )

    ranking["categoria"] = ranking["categoria"].apply(_normalize_category_value)
    ranking["delta_abs"] = ranking["pred_fallecidos_next"] - ranking["fallecidos_actuales"]
    ranking["delta_pct"] = (
        ranking["delta_abs"] / ranking["fallecidos_actuales"].replace(0, pd.NA)
    ) * 100.0
    ranking["delta_pct"] = ranking["delta_pct"].fillna(0.0)
    ranking["ranking_posicion"] = range(1, len(ranking) + 1)
    return ranking


def apply_interactive_filters(
    ranking_df: pd.DataFrame,
    selected_provinces: list[str],
    top_n: int,
    show_top_only: bool,
) -> pd.DataFrame:
    filtered = ranking_df.copy()

    if selected_provinces:
        filtered = filtered[filtered["provincia"].isin(selected_provinces)].copy()

    if show_top_only:
        filtered = filtered.head(top_n).copy()

    return filtered.reset_index(drop=True)


def build_province_detail_row(
    province_history: pd.DataFrame,
    selected_year: int,
) -> dict[str, Any] | None:
    if province_history.empty:
        return None

    current = province_history[province_history["year"] == selected_year].copy()
    if current.empty:
        return None

    current_row = current.sort_values("year").iloc[-1]
    prev = province_history[province_history["year"] < selected_year].sort_values("year")

    prev_value = float(prev.iloc[-1]["fallecidos"]) if not prev.empty else None
    current_value = float(current_row["fallecidos"])

    if prev_value is None:
        yoy_abs = None
        yoy_pct = None
    else:
        yoy_abs = current_value - prev_value
        yoy_pct = 0.0 if prev_value == 0 else (yoy_abs / prev_value) * 100.0

    explanation_parts: list[str] = []

    categoria = _normalize_category_value(current_row.get("categoria", "N/D"))
    explanation_parts.append(f"clasificación DSS actual: {categoria}")

    regla = str(current_row.get("regla_aplicada", "")).strip()
    if regla:
        explanation_parts.append(f"regla aplicada: {regla}")

    if yoy_abs is not None:
        if yoy_abs > 0:
            explanation_parts.append("incremento respecto al año previo")
        elif yoy_abs < 0:
            explanation_parts.append("reducción respecto al año previo")
        else:
            explanation_parts.append("comportamiento estable frente al año previo")

    return {
        "provincia": current_row["provincia"],
        "year": int(current_row["year"]),
        "fallecidos": current_value,
        "pred_fallecidos_next": float(current_row["pred_fallecidos_next"]),
        "score_riesgo": float(current_row["score_riesgo"]),
        "categoria": categoria,
        "regla_aplicada": str(current_row.get("regla_aplicada", "")).strip(),
        "justificacion_regla": str(current_row.get("justificacion_regla", "")).strip(),
        "recomendacion": str(current_row.get("recomendacion", "")).strip(),
        "yoy_abs": yoy_abs,
        "yoy_pct": yoy_pct,
        "explicacion": " | ".join(explanation_parts),
    }


def render_kpi_summary(
    filtered_ranking: pd.DataFrame,
    metric_column: str,
    results: dict[str, Any],
    selected_year: int,
    geo_mode: str,
) -> None:
    _inject_kpi_styles()

    ranking = filtered_ranking.copy()
    if "categoria" in ranking.columns:
        ranking["categoria"] = ranking["categoria"].apply(_normalize_category_value)

    mae = results.get("mae")
    r2 = results.get("r2")

    visible_count = (
        int(ranking["provincia"].nunique())
        if not ranking.empty and "provincia" in ranking.columns
        else 0
    )

    if not ranking.empty:
        top_row = ranking.iloc[0]
        leader_name = str(top_row.get("provincia", "N/D"))
        leader_score = _format_float(top_row.get("score_riesgo"), 3)
        leader_pred = _format_float(top_row.get("pred_fallecidos_next"), 2)
        leader_category = _normalize_category_value(top_row.get("categoria", "N/D"))
    else:
        leader_name = "N/D"
        leader_score = "N/D"
        leader_pred = "N/D"
        leader_category = "N/D"

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(
            _build_exec_card_html(
                label="Año de análisis",
                value=str(selected_year),
                subvalue=f"{visible_count} provincias visibles",
                caption="Contexto temporal activo para la priorización.",
            ),
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            _build_exec_card_html(
                label="Provincia líder",
                value=leader_name,
                subvalue=leader_category,
                caption="Territorio con mayor prioridad operativa actual.",
            ),
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            _build_exec_card_html(
                label="Score líder",
                value=leader_score,
                subvalue="Máximo score visible",
                caption="Intensidad relativa del riesgo en la salida actual.",
            ),
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            _build_exec_card_html(
                label="Predicción líder",
                value=leader_pred,
                subvalue="Escenario siguiente",
                caption="Estimación esperada para el siguiente período.",
            ),
            unsafe_allow_html=True,
        )

    with c5:
        st.markdown(
            _build_exec_card_html(
                label="Calidad del modelo",
                value=_format_float(mae, 3),
                subvalue=f"R²: {_format_float(r2, 3)}",
                caption="Indicadores globales de ajuste reportados por el pipeline.",
            ),
            unsafe_allow_html=True,
        )

    hitrate_at_3 = _resolve_metric_from_results(results, "HitRate@3", "hitrate_at_3")
    hitrate_at_5 = _resolve_metric_from_results(results, "HitRate@5", "hitrate_at_5")
    precision_at_3 = _resolve_metric_from_results(
        results,
        "Precision@3",
        "precision_at_3",
    )

    top_k_visible = f"Top-{visible_count}" if visible_count > 0 else "N/D"

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    st.markdown("## Priorización DSS")
    _render_text_desc(
        "Resultado operativo del sistema tras combinar el score predictivo con la lógica de reglas."
    )

    st.markdown("## Motor DSS visible")
    _render_text_desc(
        "Secuencia operativa que transforma datos históricos en una salida priorizada interpretable."
    )
    _render_text_analytic(
        (
            f"Período analizado: <strong>{selected_year}</strong>. "
            f"La provincia actualmente priorizada es <strong>{leader_name}</strong>, "
            f"con score <strong>{leader_score}</strong> y categoría "
            f"<strong>{leader_category}</strong>. "
            f"En la evaluación de priorización, "
            f"<strong>HitRate@3 = {_format_float(hitrate_at_3, 3)}</strong>, "
            f"<strong>HitRate@5 = {_format_float(hitrate_at_5, 3)}</strong> y "
            f"<strong>Precision@3 = {_format_float(precision_at_3, 3)}</strong>. "
            f"El ranking visible utiliza <strong>{top_k_visible}</strong> según los filtros activos."
        )
    )

    st.markdown("## Top-K priorizado")
    _render_text_desc(
        "Número de elementos prioritarios que el sistema devuelve como salida principal del ranking."
    )
    _render_text_analytic(
        f"Configuración actual del ranking visible: <strong>{top_k_visible}</strong>."
    )

    st.markdown(
        """
        <div class="exec-banner">
            <div class="exec-banner-title">Lectura ejecutiva</div>
            <div class="exec-banner-text">
                El panel resume la situación visible del ranking actual y destaca la provincia
                que concentra la mayor prioridad operativa bajo la configuración aplicada.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    bottom_left, bottom_right = st.columns([2.2, 1.0])

    with bottom_left:
        st.plotly_chart(
            kpi_dashboard(ranking, metric_column),
            width="stretch",
            key=_build_chart_key(
                "kpi_dashboard",
                metric_column,
                selected_year,
                len(ranking),
                _build_ranking_signature(ranking),
            ),
        )

    with bottom_right:
        st.markdown(
            _build_status_card_html(
                dataset_loaded=True,
                pipeline_ok=True,
                ranking_ok=not ranking.empty,
                geo_mode=geo_mode,
            ),
            unsafe_allow_html=True,
        )


def render_province_drilldown(
    scored_df: pd.DataFrame,
    province_name: str | None,
    selected_year: int,
) -> None:
    if not province_name:
        st.info("No hay provincia seleccionada.")
        return

    province_history = (
        scored_df[scored_df["provincia"] == province_name]
        .sort_values("year")
        .reset_index(drop=True)
    )

    province_history = _prepare_category_column(province_history)

    detail = build_province_detail_row(province_history, selected_year)
    if detail is None:
        st.info("No hay detalle disponible para la provincia seleccionada en el año filtrado.")
        return

    _inject_kpi_styles()

    st.subheader(f"Detalle provincial: {detail['provincia']}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fallecidos", f"{detail['fallecidos']:.0f}")
    c2.metric("Predicción siguiente", f"{detail['pred_fallecidos_next']:.2f}")
    c3.metric("Score de riesgo", f"{detail['score_riesgo']:.3f}")
    c4.metric(
        "Variación interanual",
        "N/D" if detail["yoy_pct"] is None else f"{detail['yoy_pct']:.1f}%",
        None if detail["yoy_abs"] is None else f"{detail['yoy_abs']:+.0f}",
    )

    _render_colored_dss_box(detail)

    analytic_parts: list[str] = [
        f"Año consultado: <strong>{detail['year']}</strong>.",
        f"Categoría DSS: <strong>{detail['categoria']}</strong>.",
        f"Score de riesgo: <strong>{detail['score_riesgo']:.3f}</strong>.",
        f"Predicción siguiente: <strong>{detail['pred_fallecidos_next']:.2f}</strong>.",
    ]

    if detail["yoy_pct"] is not None:
        analytic_parts.append(
            f"Variación interanual: <strong>{detail['yoy_pct']:.1f}%</strong>."
        )

    _render_text_analytic(" ".join(analytic_parts))

    if detail["justificacion_regla"]:
        st.write(f"**Justificación DSS:** {detail['justificacion_regla']}")
    if detail["recomendacion"]:
        st.write(f"**Recomendación DSS:** {detail['recomendacion']}")

    fig_hist = px.line(
        province_history,
        x="year",
        y="fallecidos",
        markers=True,
        title=f"Serie histórica de fallecidos - {detail['provincia']}",
    )
    fig_hist.update_layout(height=360, xaxis_title="Año", yaxis_title="Fallecidos")
    st.plotly_chart(
        fig_hist,
        width="stretch",
        key=_build_chart_key(
            "province_hist",
            detail["provincia"],
            selected_year,
            len(province_history),
            province_history["year"].min() if not province_history.empty else "na",
            province_history["year"].max() if not province_history.empty else "na",
        ),
    )

    detail_cols = [
        col
        for col in [
            "year",
            "fallecidos",
            "pred_fallecidos_next",
            "score_riesgo",
            "categoria",
            "regla_aplicada",
            "justificacion_regla",
            "recomendacion",
        ]
        if col in province_history.columns
    ]
    detail_table = province_history[detail_cols].copy()
    st.dataframe(safe_dataframe(detail_table), width="stretch")


def render_ranking_tab(filtered_ranking: pd.DataFrame, top_n: int) -> None:
    ranking_df = _prepare_category_column(filtered_ranking.copy())

    ranking_df["nivel_visual"] = ranking_df["categoria"].map({
        "Alta prioridad": "🔴 Alta prioridad",
        "Vigilancia preventiva": "🟡 Vigilancia preventiva",
        "Seguimiento rutinario": "🟢 Seguimiento rutinario",
        "N/D": "⚪ N/D",
    }).fillna("⚪ N/D")

    preferred_cols = [
        "ranking_posicion",
        "provincia",
        "nivel_visual",
        "categoria",
        "score_riesgo",
        "pred_fallecidos_next",
        "fallecidos_actuales",
        "delta_abs",
        "delta_pct",
        "regla_aplicada",
        "justificacion_regla",
        "recomendacion",
    ]
    visible_cols = [col for col in preferred_cols if col in ranking_df.columns]

    ranking_table = safe_dataframe(ranking_df[visible_cols])

    def _style_row(row: pd.Series) -> list[str]:
        categoria = str(row.get("categoria", "N/D")).strip()
        color_map = {
            "Alta prioridad": "background-color: rgba(231, 76, 60, 0.16);",
            "Vigilancia preventiva": "background-color: rgba(243, 156, 18, 0.18);",
            "Seguimiento rutinario": "background-color: rgba(46, 204, 113, 0.16);",
            "N/D": "background-color: rgba(189, 195, 199, 0.18);",
        }
        style = color_map.get(categoria, color_map["N/D"])
        return [style] * len(row)

    styled_ranking_table = ranking_table.style.apply(_style_row, axis=1)

    st.dataframe(
        styled_ranking_table,
        width="stretch",
        hide_index=True,
    )

    ranking_signature = _build_ranking_signature(ranking_df)

    fig_rank = px.bar(
        ranking_df.head(min(top_n, len(ranking_df))),
        x="provincia",
        y="score_riesgo",
        color="categoria",
        color_discrete_map=CATEGORY_COLOR_MAP,
        category_orders={
            "categoria": [
                "Seguimiento rutinario",
                "Vigilancia preventiva",
                "Alta prioridad",
            ]
        },
        hover_data=[
            col
            for col in [
                "pred_fallecidos_next",
                "fallecidos_actuales",
                "delta_pct",
                "regla_aplicada",
            ]
            if col in ranking_df.columns
        ],
        title="Ranking de provincias priorizadas",
    )
    fig_rank.update_layout(height=500, xaxis_title="", yaxis_title="Score de riesgo")
    st.plotly_chart(
        fig_rank,
        width="stretch",
        key=_build_chart_key(
            "ranking_bar",
            top_n,
            len(ranking_df),
            ranking_signature,
            ranking_df["score_riesgo"].sum() if "score_riesgo" in ranking_df.columns else "na",
        ),
    )

    fig_scatter = px.scatter(
        ranking_df,
        x="fallecidos_actuales",
        y="pred_fallecidos_next",
        size="score_riesgo",
        color="categoria",
        color_discrete_map=CATEGORY_COLOR_MAP,
        category_orders={
            "categoria": [
                "Seguimiento rutinario",
                "Vigilancia preventiva",
                "Alta prioridad",
            ]
        },
        hover_name="provincia",
        title="Relación entre fallecidos actuales y predicción siguiente",
    )
    fig_scatter.update_layout(height=500)
    st.plotly_chart(
        fig_scatter,
        width="stretch",
        key=_build_chart_key(
            "ranking_scatter",
            top_n,
            len(ranking_df),
            ranking_signature,
            ranking_df["pred_fallecidos_next"].sum()
            if "pred_fallecidos_next" in ranking_df.columns
            else "na",
        ),
    )


def render_metrics_tab(metricas_df: pd.DataFrame) -> None:
    st.dataframe(safe_dataframe(metricas_df), width="stretch")

    fig_metrics = px.bar(
        metricas_df,
        x="metrica",
        y="valor",
        title="Métricas de evaluación Top-K",
    )
    fig_metrics.update_layout(height=400, xaxis_title="", yaxis_title="Valor")
    st.plotly_chart(
        fig_metrics,
        width="stretch",
        key=_build_chart_key(
            "metrics_bar",
            len(metricas_df),
            "_".join(metricas_df["metrica"].astype(str).head(5).tolist())
            if "metrica" in metricas_df.columns
            else "na",
        ),
    )


def render_xai_tab(explain_df: pd.DataFrame) -> None:
    st.dataframe(safe_dataframe(explain_df), width="stretch")

    fig_imp = px.bar(
        explain_df.head(10),
        x="feature",
        y="importance",
        title="Explicabilidad global del modelo",
    )
    fig_imp.update_layout(height=450, xaxis_title="", yaxis_title="Importancia")
    st.plotly_chart(
        fig_imp,
        width="stretch",
        key=_build_chart_key(
            "xai_bar",
            min(10, len(explain_df)),
            len(explain_df),
            "_".join(explain_df["feature"].astype(str).head(5).tolist())
            if "feature" in explain_df.columns
            else "na",
        ),
    )


def render_narrative_tab(narrative_text: str) -> None:
    if not narrative_text or not str(narrative_text).strip():
        st.info("No hay narrativa disponible para este análisis.")
        return

    presentation_mode = st.session_state.get("presentation_mode", False)
    blocks = format_executive_narrative(narrative_text)

    if presentation_mode:
        st.markdown("## Resumen ejecutivo")
        _render_text_desc(
            "Lectura sintetizada de la salida del DSS, orientada a presentación y toma de decisiones."
        )

        with st.container(border=True):
            if blocks["resumen"]:
                st.markdown("### Hallazgo principal")
                st.markdown(blocks["resumen"])
            elif blocks["contexto"]:
                st.markdown("### Hallazgo principal")
                st.markdown(blocks["contexto"])

            if blocks["topk_items"]:
                st.markdown("### Provincias priorizadas")
                for item in blocks["topk_items"]:
                    st.markdown(f"- {item}")
            elif blocks["topk_text"]:
                st.markdown("### Provincias priorizadas")
                st.markdown(blocks["topk_text"])

            if blocks["interpretacion"]:
                st.markdown("### Lectura ejecutiva")
                st.markdown(blocks["interpretacion"])

            if blocks["cierre"]:
                st.markdown("### Recomendación general")
                st.markdown(blocks["cierre"])

        return

    st.markdown("## 🧾 Narrativa ejecutiva")
    _render_text_desc(
        "Síntesis interpretativa del DSS, estructurada para facilitar una lectura ejecutiva sin scroll interno."
    )

    with st.container(border=True):
        if blocks["contexto"]:
            st.markdown("### 📌 Contexto")
            st.markdown(blocks["contexto"])

        if blocks["resumen"]:
            st.markdown("### 📊 Resultado general")
            st.markdown(blocks["resumen"])

        if blocks["topk_items"]:
            st.markdown("### 🎯 Prioridades (Top-K)")
            for item in blocks["topk_items"]:
                st.markdown(f"- {item}")
        elif blocks["topk_text"]:
            st.markdown("### 🎯 Prioridades (Top-K)")
            st.markdown(blocks["topk_text"])

        if blocks["metricas"]:
            st.markdown("### 📈 Desempeño del sistema")
            st.markdown(blocks["metricas"])

        if blocks["interpretacion"]:
            st.markdown("### 🧠 Interpretación")
            st.markdown(blocks["interpretacion"])

        if blocks["cierre"]:
            st.markdown("### ⚠️ Lectura operativa")
            st.markdown(blocks["cierre"])


def render_export_section(
    filtered_ranking: pd.DataFrame,
    metricas_df: pd.DataFrame,
    scored_df: pd.DataFrame,
    explain_df: pd.DataFrame,
    selected_provinces: list[str],
    project_name: str,
    version: str,
    selected_year: int,
) -> None:
    ranking_export_df = filtered_ranking.copy()

    preferred_ranking_cols = [
        "ranking_posicion",
        "provincia",
        "categoria",
        "score_riesgo",
        "pred_fallecidos_next",
        "fallecidos_actuales",
        "delta_abs",
        "delta_pct",
        "regla_aplicada",
        "justificacion_regla",
        "recomendacion",
    ]
    ranking_export_cols = [
        col for col in preferred_ranking_cols if col in ranking_export_df.columns
    ]
    ranking_export_df = ranking_export_df[ranking_export_cols].copy()

    csv_bytes = to_csv_bytes(ranking_export_df)

    detail_export_df = scored_df.copy()
    if selected_provinces:
        detail_export_df = detail_export_df[
            detail_export_df["provincia"].isin(selected_provinces)
        ].copy()

    preferred_detail_cols = [
        "provincia",
        "provincia_canonica",
        "year",
        "fallecidos",
        "fallecidos_actuales",
        "pred_fallecidos_next",
        "score_riesgo",
        "categoria",
        "delta_abs",
        "delta_pct",
        "regla_aplicada",
        "justificacion_regla",
        "recomendacion",
    ]
    detail_export_cols = [
        col for col in preferred_detail_cols if col in detail_export_df.columns
    ]
    detail_export_df = detail_export_df[detail_export_cols].copy()

    xlsx_bytes = to_excel_bytes(
        {
            "ranking_filtrado": ranking_export_df,
            "metricas": metricas_df,
            "detalle": detail_export_df,
            "explicabilidad": explain_df,
        }
    )

    st.download_button(
        "Descargar ranking CSV",
        data=csv_bytes,
        file_name=f"{project_name}_{version}_ranking_{selected_year}.csv",
        mime="text/csv",
        width="stretch",
        key="download_ranking_csv",
    )

    st.download_button(
        "Descargar resultados Excel",
        data=xlsx_bytes,
        file_name=f"{project_name}_{version}_resultados_{selected_year}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
        key="download_results_excel",
    )

    st.caption(
        "La exportación incluye la salida operativa del DSS, incorporando categoría, "
        "regla aplicada, justificación y recomendación cuando estén disponibles."
    )