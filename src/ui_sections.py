from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.exporter import to_csv_bytes, to_excel_bytes

FULL_WIDTH = "stretch"

CATEGORY_COLOR_MAP = {
    "Alta": "#e74c3c",
    "Media": "#d4c61c",
    "Baja": "#48c774",
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
        "alta": "Alta",
        "alto": "Alta",
        "media": "Media",
        "medio": "Media",
        "baja": "Baja",
        "bajo": "Baja",
    }
    return mapping.get(text, str(value))


def _category_rank(value: Any) -> int:
    text = str(value).strip().lower()
    mapping = {
        "alta": 3,
        "alto": 3,
        "media": 2,
        "medio": 2,
        "baja": 1,
        "bajo": 1,
    }
    return mapping.get(text, 0)


def _prepare_category_column(df: pd.DataFrame, source_col: str = "categoria") -> pd.DataFrame:
    prepared = df.copy()
    if source_col in prepared.columns:
        prepared[source_col] = prepared[source_col].apply(_normalize_category_value)
    return prepared


def kpi_dashboard(ranking_df: pd.DataFrame, metric_column: str) -> go.Figure:
    if ranking_df.empty:
        fig = go.Figure()
        fig.update_layout(height=120, margin=dict(l=20, r=20, t=10, b=10))
        return fig

    ranking = ranking_df.copy()

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
                "fallecidos_actuales",
                "delta_abs",
                "delta_pct",
            ]
        )

    ranking = (
        filtered.groupby("provincia", as_index=False)
        .agg(
            pred_fallecidos_next=("pred_fallecidos_next", "mean"),
            score_riesgo=("score_riesgo", "mean"),
            categoria=("categoria", "first"),
            fallecidos_actuales=("fallecidos", "sum"),
        )
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

    if float(current_row["score_riesgo"]) >= 0.75:
        explanation_parts.append("score de riesgo elevado")
    elif float(current_row["score_riesgo"]) >= 0.50:
        explanation_parts.append("score de riesgo medio-alto")
    else:
        explanation_parts.append("score de riesgo moderado")

    if yoy_abs is not None:
        if yoy_abs > 0:
            explanation_parts.append("incremento respecto al año previo")
        elif yoy_abs < 0:
            explanation_parts.append("reducción respecto al año previo")
        else:
            explanation_parts.append("comportamiento estable frente al año previo")

    explanation_parts.append(
        f"clasificación actual: {_normalize_category_value(current_row['categoria'])}"
    )

    return {
        "provincia": current_row["provincia"],
        "year": int(current_row["year"]),
        "fallecidos": current_value,
        "pred_fallecidos_next": float(current_row["pred_fallecidos_next"]),
        "score_riesgo": float(current_row["score_riesgo"]),
        "categoria": _normalize_category_value(current_row["categoria"]),
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
    summary_left, summary_right = st.columns([2, 1])

    with summary_left:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Año de análisis", selected_year)
        c2.metric("Provincias visibles", int(filtered_ranking["provincia"].nunique()))
        c3.metric("MAE", f"{results['mae']:.3f}" if results["mae"] is not None else "N/D")
        c4.metric("R²", f"{results['r2']:.3f}" if results["r2"] is not None else "N/D")

        st.plotly_chart(
            kpi_dashboard(filtered_ranking, metric_column),
            width=FULL_WIDTH,
        )

    with summary_right:
        st.markdown("### Estado del sistema")
        st.success("Dataset cargado")
        st.success("Pipeline ejecutado")
        st.success("Ranking generado")
        if geo_mode == "Omitir mapa":
            st.info("Mapa omitido por configuración")
        else:
            st.info("Mapa habilitado")


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

    st.caption(detail["explicacion"])

    fig_hist = px.line(
        province_history,
        x="year",
        y="fallecidos",
        markers=True,
        title=f"Serie histórica de fallecidos - {detail['provincia']}",
    )
    fig_hist.update_layout(height=360, xaxis_title="Año", yaxis_title="Fallecidos")
    st.plotly_chart(fig_hist, width=FULL_WIDTH)

    detail_table = province_history[
        ["year", "fallecidos", "pred_fallecidos_next", "score_riesgo", "categoria"]
    ].copy()
    st.dataframe(safe_dataframe(detail_table), width=FULL_WIDTH)


def render_ranking_tab(filtered_ranking: pd.DataFrame, top_n: int) -> None:
    ranking_df = _prepare_category_column(filtered_ranking)

    st.dataframe(safe_dataframe(ranking_df), width=FULL_WIDTH)

    fig_rank = px.bar(
        ranking_df.head(min(top_n, len(ranking_df))),
        x="provincia",
        y="score_riesgo",
        color="categoria",
        color_discrete_map=CATEGORY_COLOR_MAP,
        category_orders={"categoria": ["Baja", "Media", "Alta"]},
        hover_data=["pred_fallecidos_next", "fallecidos_actuales", "delta_pct"],
        title="Ranking de provincias priorizadas",
    )
    fig_rank.update_layout(height=500, xaxis_title="", yaxis_title="Score de riesgo")
    st.plotly_chart(fig_rank, width=FULL_WIDTH)

    fig_scatter = px.scatter(
        ranking_df,
        x="fallecidos_actuales",
        y="pred_fallecidos_next",
        size="score_riesgo",
        color="categoria",
        color_discrete_map=CATEGORY_COLOR_MAP,
        category_orders={"categoria": ["Baja", "Media", "Alta"]},
        hover_name="provincia",
        title="Relación entre fallecidos actuales y predicción siguiente",
    )
    fig_scatter.update_layout(height=500)
    st.plotly_chart(fig_scatter, width=FULL_WIDTH)


def render_metrics_tab(metricas_df: pd.DataFrame) -> None:
    st.dataframe(safe_dataframe(metricas_df), width=FULL_WIDTH)

    fig_metrics = px.bar(
        metricas_df,
        x="metrica",
        y="valor",
        title="Métricas de evaluación Top-K",
    )
    fig_metrics.update_layout(height=400, xaxis_title="", yaxis_title="Valor")
    st.plotly_chart(fig_metrics, width=FULL_WIDTH)


def render_xai_tab(explain_df: pd.DataFrame) -> None:
    st.dataframe(safe_dataframe(explain_df), width=FULL_WIDTH)

    fig_imp = px.bar(
        explain_df.head(10),
        x="feature",
        y="importance",
        title="Explicabilidad global del modelo",
    )
    fig_imp.update_layout(height=450, xaxis_title="", yaxis_title="Importancia")
    st.plotly_chart(fig_imp, width=FULL_WIDTH)


def render_narrative_tab(narrative_text: str) -> None:
    st.text_area(
        "Narrativa automática",
        narrative_text,
        height=180,
        key="narrative_text_area",
    )


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
    csv_bytes = to_csv_bytes(filtered_ranking)

    detail_export_df = scored_df.copy()
    if selected_provinces:
        detail_export_df = detail_export_df[
            detail_export_df["provincia"].isin(selected_provinces)
        ].copy()

    xlsx_bytes = to_excel_bytes(
        {
            "ranking_filtrado": filtered_ranking,
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
        width=FULL_WIDTH,
        key="download_ranking_csv",
    )

    st.download_button(
        "Descargar resultados Excel",
        data=xlsx_bytes,
        file_name=f"{project_name}_{version}_resultados_{selected_year}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width=FULL_WIDTH,
        key="download_results_excel",
    )