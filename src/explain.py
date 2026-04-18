from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.inspection import permutation_importance


def explain_global(
    model: Any,
    X: pd.DataFrame,
    y: pd.Series | None = None,
) -> pd.DataFrame:
    """
    Genera explicabilidad global del modelo.

    Prioridad:
    1. SHAP TreeExplainer si aplica
    2. feature_importances_ si existe
    3. permutation importance como fallback general
    4. DataFrame vacío si no hay soporte
    """
    if X is None or X.empty:
        return pd.DataFrame(columns=["feature", "importance"])

    try:
        import shap  # type: ignore

        sample = X.head(min(200, len(X))).copy()
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(sample)

        if isinstance(shap_values, list):
            shap_values = shap_values[0]

        explain_df = pd.DataFrame(
            {
                "feature": sample.columns,
                "importance": abs(shap_values).mean(axis=0),
            }
        ).sort_values("importance", ascending=False)

        return explain_df.reset_index(drop=True)
    except Exception:
        pass

    try:
        if hasattr(model, "feature_importances_"):
            explain_df = pd.DataFrame(
                {
                    "feature": list(X.columns),
                    "importance": list(model.feature_importances_),
                }
            ).sort_values("importance", ascending=False)

            return explain_df.reset_index(drop=True)
    except Exception:
        pass

    try:
        if y is not None:
            sample_X = X.head(min(300, len(X))).copy()
            sample_y = y.head(min(300, len(y))).copy()

            result = permutation_importance(
                estimator=model,
                X=sample_X,
                y=sample_y,
                n_repeats=10,
                random_state=42,
                n_jobs=1,
            )

            explain_df = pd.DataFrame(
                {
                    "feature": list(sample_X.columns),
                    "importance": list(result.importances_mean),
                }
            ).sort_values("importance", ascending=False)

            return explain_df.reset_index(drop=True)
    except Exception:
        pass

    return pd.DataFrame(columns=["feature", "importance"])