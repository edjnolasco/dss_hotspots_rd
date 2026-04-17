from __future__ import annotations

import pandas as pd
import streamlit as st


def get_metric_value(metricas_df: pd.DataFrame, metric_name: str) -> float | None:
    """
    Recupera una métrica escalar desde metricas_df por nombre.

    Parameters
    ----------
    metricas_df : pd.DataFrame
        DataFrame con columnas 'metrica' y 'valor'.
    metric_name : str
        Nombre de la métrica a recuperar.

    Returns
    -------
    float | None
        Valor convertido a float si existe y es válido; en caso contrario, None.
    """
    if metricas_df is None or metricas_df.empty:
        return None

    if "metrica" not in metricas_df.columns or "valor" not in metricas_df.columns:
        return None

    row = metricas_df.loc[metricas_df["metrica"] == metric_name, "valor"]
    if row.empty:
        return None

    try:
        return float(row.iloc[0])
    except Exception:
        return None


def render_decision_engine_summary(
    filtered_ranking: pd.DataFrame,
    metricas_df: pd.DataFrame,
    top_n: int,
    selected_year_label: str,
) -> None:
    """
    Renderiza un resumen visible del motor DSS.

    Parameters
    ----------
    filtered_ranking : pd.DataFrame
        Ranking filtrado actualmente visible en la app.
    metricas_df : pd.DataFrame
        DataFrame de métricas de evaluación.
    top_n : int
        Valor Top-N activo en la interfaz.
    selected_year_label : str
        Etiqueta del período seleccionado.
    """
    st.markdown("### Motor DSS visible")

    c1, c2, c3, c4 = st.columns(4)
    c1.info("1. Datos históricos por provincia")
    c2.info("2. Modelo predictivo → score de riesgo")
    c3.info("3. Reglas DSS → categoría operativa")
    c4.info("4. Ranking Top-K → priorización")

    if filtered_ranking is None or filtered_ranking.empty:
        st.info("No hay datos disponibles para resumir el motor DSS.")
        return

    top_row = filtered_ranking.iloc[0]
    hit3 = get_metric_value(metricas_df, "hitrate_at_3")
    hit5 = get_metric_value(metricas_df, "hitrate_at_5")
    precision3 = get_metric_value(metricas_df, "precision_at_3")

    score_value = pd.to_numeric(top_row.get("score_riesgo", None), errors="coerce")
    score_text = "N/D" if pd.isna(score_value) else f"{float(score_value):.3f}"

    categoria_text = str(top_row.get("categoria", "N/D"))
    provincia_text = str(top_row.get("provincia", "N/D"))

    hit3_text = "N/D" if hit3 is None else f"{hit3:.3f}"
    hit5_text = "N/D" if hit5 is None else f"{hit5:.3f}"
    precision3_text = "N/D" if precision3 is None else f"{precision3:.3f}"

    st.caption(
        f"Período analizado: {selected_year_label}. "
        f"La provincia actualmente priorizada en la salida del DSS es {provincia_text}, "
        f"con score {score_text} y categoría '{categoria_text}'. "
        f"En la evaluación de priorización, HitRate@3 = {hit3_text}, HitRate@5 = {hit5_text} "
        f"y Precision@3 = {precision3_text}. El ranking visible usa Top-{top_n} según los filtros activos."
    )