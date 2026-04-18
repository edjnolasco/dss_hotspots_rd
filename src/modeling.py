from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

from .model_catalog import DEFAULT_MODEL_KEY, get_model_label


# ============================================================
# FEATURES DEL MODELO
# ============================================================

FEATURES = [
    "fallecidos",
    "fallecidos_prev_1",
    "fallecidos_prev_2",
    "delta_abs",
    "delta_pct",
    "rolling_mean_3",
    "rolling_std_3",
    "cum_mean",
    "year_index",
    "month_sin",
    "month_cos",
]


# ============================================================
# PREPARACIÓN DE DATOS
# ============================================================

def prepare_training_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra observaciones válidas para entrenamiento:
    - requiere target_next
    - convierte features a numérico
    - rellena features faltantes con 0.0
    """
    clean = df.dropna(subset=["target_next"]).copy()

    for col in FEATURES:
        clean[col] = pd.to_numeric(clean[col], errors="coerce").fillna(0.0)

    clean["target_next"] = pd.to_numeric(clean["target_next"], errors="coerce")
    clean = clean.dropna(subset=["target_next"]).copy()

    return clean


# ============================================================
# SPLIT TEMPORAL
# ============================================================

def temporal_train_test_split(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, list[int], list[int]]:
    """
    Divide temporalmente:
    - train = todos los años menos el último
    - test = último año
    """
    years = sorted(df["year"].dropna().astype(int).unique().tolist())

    if len(years) < 2:
        return df.copy(), pd.DataFrame(columns=df.columns), years, []

    split_year = years[-1]
    train_df = df[df["year"] < split_year].copy()
    test_df = df[df["year"] == split_year].copy()

    if train_df.empty:
        return df.copy(), pd.DataFrame(columns=df.columns), years, []

    return (
        train_df,
        test_df,
        sorted(train_df["year"].astype(int).unique().tolist()),
        [split_year],
    )


# ============================================================
# FACTORY
# ============================================================

def build_model(
    model_key: str = DEFAULT_MODEL_KEY,
    random_state: int = 42,
) -> Any:
    """
    Construye el modelo solicitado.
    Todos los modelos son de regresión para no romper el pipeline actual.
    """
    if model_key == "random_forest":
        return RandomForestRegressor(
            n_estimators=400,
            max_depth=None,
            min_samples_leaf=1,
            random_state=random_state,
            n_jobs=-1,
        )

    if model_key == "extra_trees":
        return ExtraTreesRegressor(
            n_estimators=400,
            max_depth=None,
            min_samples_leaf=1,
            random_state=random_state,
            n_jobs=-1,
        )

    if model_key == "gradient_boosting":
        return GradientBoostingRegressor(
            n_estimators=250,
            learning_rate=0.05,
            max_depth=3,
            random_state=random_state,
        )

    if model_key == "hist_gradient_boosting":
        return HistGradientBoostingRegressor(
            learning_rate=0.05,
            max_depth=6,
            max_iter=300,
            random_state=random_state,
        )

    if model_key == "svr_rbf":
        return Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "model",
                    SVR(
                        kernel="rbf",
                        C=3.0,
                        gamma="scale",
                        epsilon=0.1,
                    ),
                ),
            ]
        )

    raise ValueError(
        f"Modelo no soportado: {model_key}. "
        f"Modelos válidos: random_forest, extra_trees, "
        f"gradient_boosting, hist_gradient_boosting, svr_rbf."
    )


# ============================================================
# ENTRENAMIENTO
# ============================================================

def train_model(
    df_train: pd.DataFrame,
    model_key: str = DEFAULT_MODEL_KEY,
    random_state: int = 42,
) -> Any:
    """
    Entrena el modelo seleccionado sobre las FEATURES definidas.
    """
    model = build_model(model_key=model_key, random_state=random_state)
    model.fit(df_train[FEATURES], df_train["target_next"])
    return model


# ============================================================
# EVALUACIÓN
# ============================================================

def evaluate_model(model: Any, df_test: pd.DataFrame) -> dict[str, float | None]:
    """
    Evalúa el modelo sobre el conjunto de prueba temporal.

    Retorna:
    - mae
    - rmse
    - r2

    Si no hay test válido, devuelve None en métricas.
    """
    if df_test.empty:
        return {"mae": None, "rmse": None, "r2": None}

    y_true = df_test["target_next"]
    y_pred = model.predict(df_test[FEATURES])

    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))

    try:
        r2 = r2_score(y_true, y_pred)
    except Exception:
        r2 = None

    return {"mae": float(mae), "rmse": rmse, "r2": r2}


# ============================================================
# SCORING
# ============================================================

def score_dataframe(model: Any, df_feat: pd.DataFrame) -> pd.DataFrame:
    """
    Genera predicción para todo el dataframe transformado y calcula
    score_riesgo normalizado en [0,1].
    """
    scored = df_feat.copy()

    for col in FEATURES:
        scored[col] = pd.to_numeric(scored[col], errors="coerce").fillna(0.0)

    scored["pred_fallecidos_next"] = model.predict(scored[FEATURES])

    pred = scored["pred_fallecidos_next"].astype(float)

    if float(pred.max()) == float(pred.min()):
        scored["score_riesgo"] = 0.5
    else:
        scored["score_riesgo"] = (pred - pred.min()) / (pred.max() - pred.min())

    return scored


# ============================================================
# METADATA
# ============================================================

def model_metadata(model_key: str) -> dict[str, str]:
    """Metadatos legibles del modelo usado."""
    return {
        "model_key": model_key,
        "model_label": get_model_label(model_key),
    }