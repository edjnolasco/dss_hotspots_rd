import pandas as pd

def classify_priority(score: float, delta_abs: float) -> str:
    if score >= 0.80:
        return "Alta prioridad"
    if score >= 0.55 and delta_abs > 0:
        return "Vigilancia preventiva"
    return "Seguimiento rutinario"

def apply_rules(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["categoria"] = [classify_priority(float(score), float(delta) if pd.notna(delta) else 0.0) for score, delta in zip(out["score_riesgo"], out["delta_abs"])]
    return out
