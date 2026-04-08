import math
import pandas as pd

def dcg(relevances):
    return sum(rel / math.log2(idx + 2) for idx, rel in enumerate(relevances))

def ranking_metrics(scored_df: pd.DataFrame, k_values=(3, 5)):
    latest_year = int(scored_df["year"].max())
    latest = scored_df[scored_df["year"] == latest_year].copy()
    pred_rank = latest.groupby("provincia", as_index=False)["score_riesgo"].mean().sort_values("score_riesgo", ascending=False)
    actual_rank = latest.groupby("provincia", as_index=False)["fallecidos"].sum().sort_values("fallecidos", ascending=False)
    pred_list = pred_rank["provincia"].tolist()
    actual_list = actual_rank["provincia"].tolist()
    actual_rel_map = {row["provincia"]: float(row["fallecidos"]) for _, row in actual_rank.iterrows()}
    rows = []
    for k in k_values:
        pred_top = pred_list[:k]
        actual_top = set(actual_list[:k])
        hits = sum(1 for p in pred_top if p in actual_top)
        hitrate = hits / max(k, 1)
        pred_rels = [actual_rel_map.get(p, 0.0) for p in pred_top]
        ideal_rels = sorted(actual_rel_map.values(), reverse=True)[:k]
        idcg = dcg(ideal_rels)
        ndcg = dcg(pred_rels) / idcg if idcg > 0 else 0.0
        rows.append({"metrica": f"HitRate@{k}", "valor": round(hitrate, 4)})
        rows.append({"metrica": f"nDCG@{k}", "valor": round(ndcg, 4)})
    return pd.DataFrame(rows), pred_rank, actual_rank
