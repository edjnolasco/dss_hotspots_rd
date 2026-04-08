from __future__ import annotations

import pandas as pd


def explain_global(model, X: pd.DataFrame) -> pd.DataFrame:
    """
    Genera explicabilidad global del modelo.

    Prioridad:
    1. SHAP (si está disponible y funciona)
    2. feature_importances_ del modelo
    3. DataFrame vacío si no hay soporte

    Retorna un DataFrame con columnas:
    - feature
    - importance
    """
    if X is None or X.empty:
        return pd.DataFrame(columns=["feature", "importance"])

    # ------------------------------------------------------------
    # Intento principal: SHAP
    # ------------------------------------------------------------
    try:
        import shap

        sample = X.head(min(200, len(X))).copy()

        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(sample)

        # SHAP puede devolver lista o array según el modelo
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

    # ------------------------------------------------------------
    # Fallback: feature_importances_
    # ------------------------------------------------------------
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

    # ------------------------------------------------------------
    # Último recurso: vacío
    # ------------------------------------------------------------
    return pd.DataFrame(columns=["feature", "importance"])
