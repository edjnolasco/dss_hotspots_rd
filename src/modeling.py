from __future__ import annotations

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

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

def temporal_train_test_split(df: pd.DataFrame):
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
# ENTRENAMIENTO
# ============================================================

def train_model(df_train: pd.DataFrame, random_state: int = 42) -> RandomForestRegressor:
    """
    Entrena un RandomForestRegressor sobre las FEATURES definidas.
    """
    model = RandomForestRegressor(
        n_estimators=300,
        random_state=random_state,
        n_jobs=-1,
    )

    model.fit(df_train[FEATURES], df_train["target_next"])
    return model


# ============================================================
# EVALUACIÓN
# ============================================================

def evaluate_model(model, df_test: pd.DataFrame):
    """
    Evalúa el modelo sobre el conjunto de prueba temporal.
    Devuelve:
    - mae
    - r2
    Si no hay test válido, devuelve (None, None)
    """
    if df_test.empty:
        return None, None

    preds = model.predict(df_test[FEATURES])
    mae = mean_absolute_error(df_test["target_next"], preds)

    try:
        r2 = r2_score(df_test["target_next"], preds)
    except Exception:
        r2 = None

    return mae, r2


# ============================================================
# SCORING
# ============================================================

def score_dataframe(model, df_feat: pd.DataFrame) -> pd.DataFrame:
    """
    Genera predicción para todo el dataframe transformado
    y calcula score_riesgo normalizado en [0,1].
    """
    scored = df_feat.copy()

    for col in FEATURES:
        scored[col] = pd.to_numeric(scored[col], errors="coerce").fillna(0.0)

    scored["pred_fallecidos_next"] = model.predict(scored[FEATURES])

    pred = scored["pred_fallecidos_next"]

    if float(pred.max()) == float(pred.min()):
        scored["score_riesgo"] = 0.5
    else:
        scored["score_riesgo"] = (pred - pred.min()) / (pred.max() - pred.min())

    return scored
