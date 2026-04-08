import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

FEATURES = ["fallecidos","fallecidos_prev_1","fallecidos_prev_2","delta_abs","delta_pct","rolling_mean_3","rolling_std_3","cum_mean","year_index","month_sin","month_cos"]

def prepare_training_data(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.dropna(subset=["target_next"]).copy()
    for c in FEATURES:
        clean[c] = pd.to_numeric(clean[c], errors="coerce").fillna(0.0)
    clean["target_next"] = pd.to_numeric(clean["target_next"], errors="coerce")
    return clean.dropna(subset=["target_next"]).copy()

def temporal_train_test_split(df: pd.DataFrame):
    years = sorted(df["year"].astype(int).unique().tolist())
    if len(years) < 2:
        return df.copy(), pd.DataFrame(columns=df.columns), years, []
    split_year = years[-1]
    train_df = df[df["year"] < split_year].copy()
    test_df = df[df["year"] == split_year].copy()
    if train_df.empty:
        return df.copy(), pd.DataFrame(columns=df.columns), years, []
    return train_df, test_df, sorted(train_df["year"].astype(int).unique().tolist()), [split_year]

def train_model(df_train: pd.DataFrame, random_state: int = 42):
    model = RandomForestRegressor(n_estimators=300, random_state=random_state, n_jobs=-1)
    model.fit(df_train[FEATURES], df_train["target_next"])
    return model

def evaluate_model(model, df_test: pd.DataFrame):
    if df_test.empty:
        return None, None
    preds = model.predict(df_test[FEATURES])
    mae = mean_absolute_error(df_test["target_next"], preds)
    try:
        r2 = r2_score(df_test["target_next"], preds)
    except Exception:
        r2 = None
    return mae, r2

def score_dataframe(model, df_feat: pd.DataFrame) -> pd.DataFrame:
    scored = df_feat.copy()
    for c in FEATURES:
        scored[c] = pd.to_numeric(scored[c], errors="coerce").fillna(0.0)
    scored["pred_fallecidos_next"] = model.predict(scored[FEATURES])
    pred = scored["pred_fallecidos_next"]
    scored["score_riesgo"] = 0.5 if float(pred.max()) == float(pred.min()) else (pred - pred.min()) / (pred.max() - pred.min())
    return scored
