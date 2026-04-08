from __future__ import annotations

from .features import create_features
from .modeling import (
    FEATURES,
    prepare_training_data,
    temporal_train_test_split,
    train_model,
    evaluate_model,
    score_dataframe,
)
from .rules import apply_rules
from .metrics import ranking_metrics
from .explain import explain_global
from .narrative import build_narrative


def run_pipeline(normalized_df, random_state: int = 42) -> dict:
    """
    Ejecuta el flujo completo del DSS:

    1. Ingeniería de características
    2. Preparación de datos de entrenamiento
    3. Split temporal
    4. Entrenamiento del modelo
    5. Evaluación
    6. Scoring
    7. Aplicación de reglas
    8. Construcción de ranking
    9. Métricas Top-K
    10. Explicabilidad global
    11. Narrativa automática

    Retorna un diccionario con todos los artefactos necesarios
    para la app Streamlit.
    """

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
    model = train_model(fit_df, random_state=random_state)

    # ------------------------------------------------------------
    # 5. Evaluación
    # ------------------------------------------------------------
    mae, r2 = evaluate_model(model, test_df)

    # ------------------------------------------------------------
    # 6. Scoring sobre todo el conjunto transformado
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
    # 9. Métricas Top-K
    # ------------------------------------------------------------
    metricas_df, pred_rank_df, actual_rank_df = ranking_metrics(scored_df)

    # ------------------------------------------------------------
    # 10. Explicabilidad global
    # ------------------------------------------------------------
    explain_df = explain_global(model, fit_df[FEATURES])

    # ------------------------------------------------------------
    # 11. Narrativa automática
    # ------------------------------------------------------------
    narrative_text = build_narrative(ranking_df, metricas_df, latest_year)

    # ------------------------------------------------------------
    # 12. Salida final
    # ------------------------------------------------------------
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
        "mae": mae,
        "r2": r2,
    }
