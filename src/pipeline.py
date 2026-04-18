from __future__ import annotations

from pathlib import Path

import pandas as pd

from .explain import explain_global
from .features import create_features
from .metrics import ranking_metrics
from .model_catalog import DEFAULT_MODEL_KEY, get_model_label
from .modeling import (
    FEATURES,
    evaluate_model,
    model_metadata,
    prepare_training_data,
    score_dataframe,
    temporal_train_test_split,
    train_model,
)
from .narrative import build_narrative
from .rules import apply_rules


def load_province_catalog() -> pd.DataFrame:
    """
    Carga el catálogo oficial de provincias de RD.
    """
    root = Path(__file__).resolve().parents[1]
    catalog_path = root / "data" / "provincias_rd_catalog.csv"

    if not catalog_path.exists():
        raise FileNotFoundError(
            f"No se encontró el catálogo de provincias en: {catalog_path}"
        )

    catalog = pd.read_csv(catalog_path)

    if "provincia" not in catalog.columns:
        raise ValueError(
            "El catálogo de provincias debe tener la columna 'provincia'."
        )

    return catalog[["provincia"]].drop_duplicates().copy()


def run_pipeline(
    normalized_df: pd.DataFrame,
    random_state: int = 42,
    model_key: str = DEFAULT_MODEL_KEY,
) -> dict:
    # ------------------------------------------------------------
    # 1. Feature engineering
    # ------------------------------------------------------------
    feat_df = create_features(normalized_df)

    # ------------------------------------------------------------
    # 2. Preparación del dataset de entrenamiento
    # ------------------------------------------------------------
    trainable_df = prepare_training_data(feat_df)

    # ------------------------------------------------------------
    # 3. Split temporal
    # ------------------------------------------------------------
    train_df, test_df, train_years, test_years = temporal_train_test_split(trainable_df)

    # ------------------------------------------------------------
    # 4. Entrenamiento
    # ------------------------------------------------------------
    fit_df = train_df if not train_df.empty else trainable_df
    model = train_model(
        fit_df,
        model_key=model_key,
        random_state=random_state,
    )

    # ------------------------------------------------------------
    # 5. Evaluación
    # ------------------------------------------------------------
    eval_metrics = evaluate_model(model, test_df)

    # ------------------------------------------------------------
    # 6. Scoring
    # ------------------------------------------------------------
    scored_df = score_dataframe(model, feat_df)

    # ------------------------------------------------------------
    # 7. Reglas DSS
    # ------------------------------------------------------------
    scored_df = apply_rules(scored_df)

    # ------------------------------------------------------------
    # 8. Ranking del último período disponible
    # ------------------------------------------------------------
    latest_year = int(scored_df["year"].max())

    latest_df = scored_df[scored_df["year"] == latest_year].copy()

    ranking_df = (
        latest_df.groupby("provincia", as_index=False)
        .agg(
            pred_fallecidos_next=("pred_fallecidos_next", "mean"),
            score_riesgo=("score_riesgo", "mean"),
            categoria=("categoria", "first"),
            fallecidos_actuales=("fallecidos", "sum"),
        )
        .sort_values("score_riesgo", ascending=False)
        .reset_index(drop=True)
    )

    # ------------------------------------------------------------
    # 9. Expandir a todas las provincias oficiales
    # ------------------------------------------------------------
    catalog_df = load_province_catalog()
    ranking_df = catalog_df.merge(ranking_df, on="provincia", how="left")

    ranking_df["pred_fallecidos_next"] = ranking_df["pred_fallecidos_next"].fillna(0.0)
    ranking_df["score_riesgo"] = ranking_df["score_riesgo"].fillna(0.0)
    ranking_df["fallecidos_actuales"] = ranking_df["fallecidos_actuales"].fillna(0.0)
    ranking_df["categoria"] = ranking_df["categoria"].fillna("Sin datos")

    ranking_df = ranking_df.sort_values(
        ["score_riesgo", "fallecidos_actuales"],
        ascending=[False, False],
    ).reset_index(drop=True)

    # ------------------------------------------------------------
    # 10. Métricas Top-K
    # ------------------------------------------------------------
    metricas_df, pred_rank_df, actual_rank_df = ranking_metrics(scored_df)

    # ------------------------------------------------------------
    # 11. Explicabilidad global
    # ------------------------------------------------------------
    explain_df = explain_global(
        model=model,
        X=fit_df[FEATURES],
        y=fit_df["target_next"],
    )

    # ------------------------------------------------------------
    # 12. Narrativa automática
    # ------------------------------------------------------------
    model_label = get_model_label(model_key)
    narrative_text = build_narrative(
        ranking_df=ranking_df,
        metricas_df=metricas_df,
        latest_year=latest_year,
        model_label=model_label,
    )

    # ------------------------------------------------------------
    # 13. Salida final
    # ------------------------------------------------------------
    metadata = model_metadata(model_key)

    return {
        "feat_df": feat_df,
        "trainable_df": trainable_df,
        "scored_df": scored_df,
        "ranking_df": ranking_df,
        "metricas_df": metricas_df,
        "pred_rank_df": pred_rank_df,
        "actual_rank_df": actual_rank_df,
        "explain_df": explain_df,
        "narrative_text": narrative_text,
        "latest_year": latest_year,
        "train_years": train_years,
        "test_years": test_years,
        "mae": eval_metrics["mae"],
        "rmse": eval_metrics["rmse"],
        "r2": eval_metrics["r2"],
        "model_key": metadata["model_key"],
        "model_label": metadata["model_label"],
        "model": model,
    }