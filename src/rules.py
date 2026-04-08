from __future__ import annotations

import pandas as pd


def classify_priority(score: float, delta_abs: float) -> str:
    """
    Clasifica el nivel de prioridad del DSS a partir del score de riesgo
    y de la variación absoluta reciente.

    Reglas:
    - score >= 0.80 -> Alta prioridad
    - score >= 0.55 y delta_abs > 0 -> Vigilancia preventiva
    - en otro caso -> Seguimiento rutinario
    """
    if score >= 0.80:
        return "Alta prioridad"

    if score >= 0.55 and delta_abs > 0:
        return "Vigilancia preventiva"

    return "Seguimiento rutinario"


def apply_rules(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica la lógica DSS sobre un dataframe que ya contiene:
    - score_riesgo
    - delta_abs

    Devuelve el mismo dataframe con la columna:
    - categoria
    """
    out = df.copy()

    if "score_riesgo" not in out.columns:
        raise ValueError("No se encontró la columna 'score_riesgo' en el dataframe.")

    if "delta_abs" not in out.columns:
        raise ValueError("No se encontró la columna 'delta_abs' en el dataframe.")

    out["score_riesgo"] = pd.to_numeric(out["score_riesgo"], errors="coerce").fillna(0.0)
    out["delta_abs"] = pd.to_numeric(out["delta_abs"], errors="coerce").fillna(0.0)

    out["categoria"] = [
        classify_priority(float(score), float(delta))
        for score, delta in zip(out["score_riesgo"], out["delta_abs"])
    ]

    return out
