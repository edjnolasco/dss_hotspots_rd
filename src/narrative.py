def build_narrative(ranking_df, metricas_df, latest_year: int) -> str:
    top1 = ranking_df.iloc[0]
    top3 = ", ".join(ranking_df.head(3)["provincia"].tolist())
    hit_k = metricas_df.loc[metricas_df["metrica"] == "HitRate@3", "valor"]
    ndcg_k = metricas_df.loc[metricas_df["metrica"] == "nDCG@3", "valor"]
    hit_k = float(hit_k.iloc[0]) if not hit_k.empty else None
    ndcg_k = float(ndcg_k.iloc[0]) if not ndcg_k.empty else None
    txt = (
        f"Para el período de análisis {latest_year}, el DSS identifica a {top1['provincia']} "
        f"como la provincia con mayor prioridad de intervención, con una categoría de "
        f"'{top1['categoria']}' y un score de riesgo de {float(top1['score_riesgo']):.3f}. "
        f"El grupo de provincias más relevantes del ranking está compuesto por {top3}. "
    )
    if hit_k is not None and ndcg_k is not None:
        txt += f"Desde la perspectiva Top-K, el sistema alcanza un HitRate@3 de {hit_k:.3f} y un nDCG@3 de {ndcg_k:.3f}. "
    txt += "En términos operativos, esta salida facilita la priorización de vigilancia, prevención y asignación de recursos dentro de un proceso de decisión asistida."
    return txt
