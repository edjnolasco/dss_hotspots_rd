from __future__ import annotations

import pandas as pd

from .model_catalog import MODEL_SPECS
from .modeling import evaluate_model, prepare_training_data, temporal_train_test_split, train_model
from .features import create_features


def benchmark_models(
    normalized_df: pd.DataFrame,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Ejecuta benchmark rápido sobre todos los modelos disponibles.
    Retorna un DataFrame ordenado por MAE ascendente y luego RMSE ascendente.
    """
    feat_df = create_features(normalized_df)
    trainable_df = prepare_training_data(feat_df)
    train_df, test_df, train_years, test_years = temporal_train_test_split(trainable_df)

    fit_df = train_df if not train_df.empty else trainable_df

    rows: list[dict[str, object]] = []

    for model_key, spec in MODEL_SPECS.items():
        try:
            model = train_model(
                fit_df,
                model_key=model_key,
                random_state=random_state,
            )
            metrics = evaluate_model(model, test_df)

            rows.append(
                {
                    "model_key": model_key,
                    "model_label": spec.label,
                    "family": spec.family,
                    "mae": metrics["mae"],
                    "rmse": metrics["rmse"],
                    "r2": metrics["r2"],
                    "train_years": ", ".join(map(str, train_years)) if train_years else "",
                    "test_years": ", ".join(map(str, test_years)) if test_years else "",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "model_key": model_key,
                    "model_label": spec.label,
                    "family": spec.family,
                    "mae": None,
                    "rmse": None,
                    "r2": None,
                    "train_years": ", ".join(map(str, train_years)) if train_years else "",
                    "test_years": ", ".join(map(str, test_years)) if test_years else "",
                    "error": str(exc),
                }
            )

    result = pd.DataFrame(rows)

    if "mae" in result.columns:
        result = result.sort_values(
            by=["mae", "rmse"],
            ascending=[True, True],
            na_position="last",
        ).reset_index(drop=True)

    return result