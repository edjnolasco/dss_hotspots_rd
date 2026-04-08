import pandas as pd

def explain_global(model, X: pd.DataFrame) -> pd.DataFrame:
    try:
        import shap
        sample = X.head(min(200, len(X))).copy()
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(sample)
        if isinstance(shap_values, list):
            shap_values = shap_values[0]
        return pd.DataFrame({"feature": sample.columns, "importance": abs(shap_values).mean(axis=0)}).sort_values("importance", ascending=False).reset_index(drop=True)
    except Exception:
        if hasattr(model, "feature_importances_"):
            return pd.DataFrame({"feature": list(X.columns), "importance": list(model.feature_importances_)}).sort_values("importance", ascending=False).reset_index(drop=True)
        return pd.DataFrame(columns=["feature", "importance"])
