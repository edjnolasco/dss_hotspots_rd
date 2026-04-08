from __future__ import annotations

import math
import pandas as pd


def dcg(relevances: list[float]) -> float:
    """
    Discounted Cumulative Gain.
    """
    return sum(rel / math.log2(idx + 2) for idx, rel in enumerate(relevances))


def ranking_metrics(
    scored_df: pd.DataFrame,
    k_values: tuple[int, ...] = (3, 5),
):
    """
    Calcula métricas de evaluación Top-K a partir del dataframe scored_df.

    Requisitos en scored_df:
    - provincia
    - year
    - score_riesgo
    - fallecidos

    Devuelve:
    - metricas_df
    - pred_rank_df
    - actual_rank_df
    """
    required_cols = {"provincia", "year", "score_riesgo", "fallecidos"}
    missing = required_cols - set(scored_df.columns)
    if missing:
        raise ValueError(
            f"Faltan columnas requeridas en scored_df para calcular métricas: {missing}"
        )

    latest_year = int(scored_df["year"].max())
    latest = scored_df[scored_df["year"] == latest_year].copy()

    if latest.empty:
        raise ValueError("No hay datos del último año para calcular métricas.")

    # ------------------------------------------------------------
    # Ranking predicho
    # ------------------------------------------------------------
    pred_rank_df = (
        latest.groupby("provincia", as_index=False)["score_riesgo"]
        .mean()
        .sort_values("score_riesgo", ascending=False)
        .reset_index(drop=True)
    )

    # ------------------------------------------------------------
    # Ranking real
    # ------------------------------------------------------------
    actual_rank_df = (
        latest.groupby("provincia", as_index=False)["fallecidos"]
        .sum()
        .sort_values("fallecidos", ascending=False)
        .reset_index(drop=True)
    )

    pred_list = pred_rank_df["provincia"].tolist()
    actual_list = actual_rank_df["provincia"].tolist()

    actual_relevance_map = {
        row["provincia"]: float(row["fallecidos"])
        for _, row in actual_rank_df.iterrows()
    }

    rows = []

    for k in k_values:
        if k <= 0:
            continue

        pred_top = pred_list[:k]
        actual_top = set(actual_list[:k])

        # --------------------------------------------------------
        # HitRate@K
        # --------------------------------------------------------
        hits = sum(1 for province in pred_top if province in actual_top)
        hitrate = hits / max(k, 1)

        # --------------------------------------------------------
        # nDCG@K
        # --------------------------------------------------------
        pred_relevances = [actual_relevance_map.get(province, 0.0) for province in pred_top]
        ideal_relevances = sorted(actual_relevance_map.values(), reverse=True)[:k]

        ideal_dcg = dcg(ideal_relevances)
        ndcg = dcg(pred_relevances) / ideal_dcg if ideal_dcg > 0 else 0.0

        rows.append(
            {
                "metrica": f"HitRate@{k}",
                "valor": round(hitrate, 4),
            }
        )
        rows.append(
            {
                "metrica": f"nDCG@{k}",
                "valor": round(ndcg, 4),
            }
        )

    metricas_df = pd.DataFrame(rows)

    return metricas_df, pred_rank_df, actual_rank_df
