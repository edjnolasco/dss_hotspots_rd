from __future__ import annotations

import pandas as pd


def build_narrative(
    ranking_df: pd.DataFrame,
    metricas_df: pd.DataFrame,
    latest_year: int,
) -> str:
    """
    Genera una narrativa automática breve a partir del ranking del DSS
    y de las métricas Top-K.

    Requiere en ranking_df:
    - provincia
    - categoria
    - score_riesgo

    Opcionalmente:
    - pred_fallecidos_next

    Requiere en metricas_df:
    - metrica
    - valor
    """
    if ranking_df is None or ranking_df.empty:
        return (
            f"No fue posible generar la narrativa automática para el período {latest_year}, "
            "porque el ranking del DSS no contiene resultados."
        )

    top1 = ranking_df.iloc[0]

    provincia_top = str(top1.get("provincia", "N/D"))
    categoria_top = str(top1.get("categoria", "N/D"))
    score_top = float(top1.get("score_riesgo", 0.0))

    pred_next = top1.get("pred_fallecidos_next", None)
    pred_text = ""
    if pred_next is not None and pd.notna(pred_next):
        pred_text = (
            f" Asimismo, la estimación del modelo para el siguiente período "
            f"se sitúa en {float(pred_next):.2f} fallecidos."
        )

    top3_list = ranking_df.head(3)["provincia"].astype(str).tolist()
    top3 = ", ".join(top3_list) if top3_list else "N/D"

    hitrate_3 = None
    ndcg_3 = None

    if metricas_df is not None and not metricas_df.empty:
        hitrate_match = metricas_df.loc[
            metricas_df["metrica"] == "HitRate@3", "valor"
        ]
        ndcg_match = metricas_df.loc[
            metricas_df["metrica"] == "nDCG@3", "valor"
        ]

        if not hitrate_match.empty:
            hitrate_3 = float(hitrate_match.iloc[0])

        if not ndcg_match.empty:
            ndcg_3 = float(ndcg_match.iloc[0])

    metric_text = ""
    if hitrate_3 is not None and ndcg_3 is not None:
        metric_text = (
            f" Desde la perspectiva de evaluación Top-K, el sistema alcanza un "
            f"HitRate@3 de {hitrate_3:.3f} y un nDCG@3 de {ndcg_3:.3f}, lo que "
            f"sugiere una capacidad razonable para ubicar en posiciones altas "
            f"las provincias más relevantes del período analizado."
        )
    elif hitrate_3 is not None:
        metric_text = (
            f" Desde la perspectiva de evaluación Top-K, el sistema alcanza un "
            f"HitRate@3 de {hitrate_3:.3f}."
        )
    elif ndcg_3 is not None:
        metric_text = (
            f" Desde la perspectiva de evaluación Top-K, el sistema alcanza un "
            f"nDCG@3 de {ndcg_3:.3f}."
        )

    narrative = (
        f"Para el período de análisis {latest_year}, el DSS identifica a "
        f"{provincia_top} como la provincia con mayor prioridad de intervención, "
        f"clasificada en la categoría '{categoria_top}' y con un score de riesgo "
        f"de {score_top:.3f}.{pred_text} "
        f"En términos comparativos, el grupo de provincias más relevantes del ranking "
        f"está compuesto por {top3}.{metric_text} "
        f"En consecuencia, la salida del sistema proporciona una base operativa para "
        f"apoyar la priorización de vigilancia, prevención y asignación de recursos "
        f"dentro de un proceso de decisión asistida."
    )

    return narrative
