from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score


def run_pipeline(df: pd.DataFrame) -> dict[str, Any]:
    required_cols = {"provincia", "provincia_canonica", "year", "fallecidos"}
    missing = required_cols - set(df.columns)
    if missing:
        raise KeyError(
            f"Faltan columnas requeridas para el pipeline: {sorted(missing)}"
        )

    working = df.copy()

    working["provincia"] = working["provincia"].astype(str).str.strip()
    working["provincia_canonica"] = working["provincia_canonica"].astype(str).str.strip()
    working["year"] = pd.to_numeric(working["year"], errors="coerce")
    working["fallecidos"] = pd.to_numeric(working["fallecidos"], errors="coerce")

    working = working.dropna(
        subset=["provincia", "provincia_canonica", "year", "fallecidos"]
    ).copy()

    working["year"] = working["year"].astype(int)
    working["fallecidos"] = working["fallecidos"].astype(float)

    # Agrupación base estable por provincia canónica y año.
    # Se conserva provincia visible para la UI.
    grouped = (
        working.groupby(["provincia_canonica", "year"], as_index=False)
        .agg(
            fallecidos=("fallecidos", "sum"),
            provincia=("provincia", _pick_display_name),
        )
        .sort_values(["provincia_canonica", "year"])
        .reset_index(drop=True)
    )

    # Features temporales por provincia canónica
    featured = _build_temporal_features(grouped)

    # Predicción por fallback si no hay suficientes datos para modelar
    if featured.empty or featured["year"].nunique() < 2:
        scored_df = _build_fallback_scored_df(grouped)
        mae = None
        r2 = None
        explain_df = _build_fallback_explain_df()
    else:
        scored_df, mae, r2, explain_df = _fit_and_score(featured)

    latest_year = int(scored_df["year"].max())

    metricas_df = _build_metrics_df(scored_df, latest_year)
    narrative_text = _build_narrative_text(
        scored_df=scored_df,
        metricas_df=metricas_df,
        latest_year=latest_year,
        mae=mae,
        r2=r2,
    )

    return {
        "scored_df": scored_df,
        "metricas_df": metricas_df,
        "explain_df": explain_df,
        "narrative_text": narrative_text,
        "mae": mae,
        "r2": r2,
        "latest_year": latest_year,
    }


def _pick_display_name(series: pd.Series) -> str:
    values = (
        series.dropna()
        .astype(str)
        .str.strip()
        .loc[lambda s: s.ne("")]
        .value_counts()
    )
    if values.empty:
        return ""
    return str(values.index[0])


def _build_temporal_features(grouped: pd.DataFrame) -> pd.DataFrame:
    df = grouped.copy()
    df = df.sort_values(["provincia_canonica", "year"]).reset_index(drop=True)

    g = df.groupby("provincia_canonica", group_keys=False)

    df["lag_1"] = g["fallecidos"].shift(1)
    df["lag_2"] = g["fallecidos"].shift(2)
    df["lag_3"] = g["fallecidos"].shift(3)

    df["rolling_mean_2"] = (
        g["fallecidos"].shift(1).rolling(window=2, min_periods=1).mean().reset_index(drop=True)
    )
    df["rolling_mean_3"] = (
        g["fallecidos"].shift(1).rolling(window=3, min_periods=1).mean().reset_index(drop=True)
    )

    df["delta_1"] = df["lag_1"] - df["lag_2"]
    df["delta_2"] = df["lag_2"] - df["lag_3"]

    # Sólo filas entrenables: al menos lag_1
    df_model = df.dropna(subset=["lag_1"]).copy()

    return df_model


def _fit_and_score(
    featured: pd.DataFrame,
) -> tuple[pd.DataFrame, float | None, float | None, pd.DataFrame]:
    feature_cols = [
        "year",
        "lag_1",
        "lag_2",
        "lag_3",
        "rolling_mean_2",
        "rolling_mean_3",
        "delta_1",
        "delta_2",
    ]

    # Algunas columnas pueden quedar casi vacías según la profundidad temporal.
    usable_feature_cols = [
        col for col in feature_cols if col in featured.columns and featured[col].notna().any()
    ]

    train_df = featured.copy()
    for col in usable_feature_cols:
        train_df[col] = train_df[col].fillna(train_df[col].median())

    X = train_df[usable_feature_cols]
    y = train_df["fallecidos"]

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=1,
        random_state=42,
    )
    model.fit(X, y)

    y_pred = model.predict(X)
    mae = float(mean_absolute_error(y, y_pred))
    r2 = float(r2_score(y, y_pred))

    scored_df = featured.copy()
    for col in usable_feature_cols:
        scored_df[col] = scored_df[col].fillna(scored_df[col].median())

    scored_df["pred_fallecidos_next"] = model.predict(scored_df[usable_feature_cols])

    scored_df = _decorate_scored_df(scored_df)

    explain_df = pd.DataFrame(
        {
            "feature": usable_feature_cols,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False).reset_index(drop=True)

    return scored_df, mae, r2, explain_df


def _build_fallback_scored_df(grouped: pd.DataFrame) -> pd.DataFrame:
    df = grouped.copy()
    df = df.sort_values(["provincia_canonica", "year"]).reset_index(drop=True)

    g = df.groupby("provincia_canonica", group_keys=False)

    df["lag_1"] = g["fallecidos"].shift(1)
    df["lag_2"] = g["fallecidos"].shift(2)

    # Fallback simple: último valor conocido o promedio simple
    df["pred_fallecidos_next"] = np.where(
        df["lag_1"].notna(),
        df["lag_1"],
        df["fallecidos"],
    )

    scored_df = _decorate_scored_df(df)
    return scored_df


def _decorate_scored_df(scored_df: pd.DataFrame) -> pd.DataFrame:
    df = scored_df.copy()

    df["pred_fallecidos_next"] = pd.to_numeric(
        df["pred_fallecidos_next"], errors="coerce"
    ).fillna(df["fallecidos"])

    # Score relativo por año para mantener comparabilidad visual
    df["score_riesgo"] = (
        df.groupby("year")["pred_fallecidos_next"]
        .transform(_minmax_scale)
        .fillna(0.0)
    )

    df["categoria"] = df["score_riesgo"].apply(_risk_category)

    # Compatibilidad con la app
    df["fallecidos_actuales"] = df["fallecidos"]
    df["delta_abs"] = df["pred_fallecidos_next"] - df["fallecidos_actuales"]
    df["delta_pct"] = np.where(
        df["fallecidos_actuales"] == 0,
        0.0,
        (df["delta_abs"] / df["fallecidos_actuales"]) * 100.0,
    )

    # Orden final estable y visible
    df = df[
        [
            "provincia",
            "provincia_canonica",
            "year",
            "fallecidos",
            "fallecidos_actuales",
            "pred_fallecidos_next",
            "score_riesgo",
            "categoria",
            "delta_abs",
            "delta_pct",
        ]
    ].copy()

    df = df.sort_values(["year", "score_riesgo"], ascending=[True, False]).reset_index(drop=True)
    return df


def _build_metrics_df(scored_df: pd.DataFrame, latest_year: int) -> pd.DataFrame:
    latest = scored_df[scored_df["year"] == latest_year].copy()

    if latest.empty:
        return pd.DataFrame(
            {
                "metrica": ["top_1_score", "top_3_score_promedio", "provincias_analizadas"],
                "valor": [0.0, 0.0, 0.0],
            }
        )

    latest = latest.sort_values("score_riesgo", ascending=False).reset_index(drop=True)

    top_1_score = float(latest.iloc[0]["score_riesgo"])
    top_3_score_promedio = float(latest.head(min(3, len(latest)))["score_riesgo"].mean())
    provincias_analizadas = float(latest["provincia_canonica"].nunique())

    return pd.DataFrame(
        {
            "metrica": [
                "top_1_score",
                "top_3_score_promedio",
                "provincias_analizadas",
            ],
            "valor": [
                top_1_score,
                top_3_score_promedio,
                provincias_analizadas,
            ],
        }
    )


def _build_fallback_explain_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "feature": ["lag_1", "year"],
            "importance": [0.7, 0.3],
        }
    )


def _build_narrative_text(
    scored_df: pd.DataFrame,
    metricas_df: pd.DataFrame,
    latest_year: int,
    mae: float | None,
    r2: float | None,
) -> str:
    latest = (
        scored_df[scored_df["year"] == latest_year]
        .sort_values("score_riesgo", ascending=False)
        .reset_index(drop=True)
    )

    if latest.empty:
        return "No fue posible generar narrativa automática para el período analizado."

    top = latest.iloc[0]
    top3 = latest.head(min(3, len(latest)))["provincia"].tolist()

    mae_text = "N/D" if mae is None else f"{mae:.3f}"
    r2_text = "N/D" if r2 is None else f"{r2:.3f}"

    return (
        f"Para el año {latest_year}, la provincia con mayor prioridad estimada es "
        f"{top['provincia']}, con un score de riesgo de {top['score_riesgo']:.3f} y "
        f"una predicción de {top['pred_fallecidos_next']:.2f} fallecidos. "
        f"Las tres provincias mejor posicionadas en la priorización actual son: "
        f"{', '.join(top3)}. "
        f"El desempeño global del modelo reporta un MAE de {mae_text} y un R² de {r2_text}. "
        f"Esta salida se construye agrupando por provincia canónica para evitar duplicidades "
        f"nominales, pero conservando el nombre visible de provincia para la capa de visualización."
    )


def _minmax_scale(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    s_min = s.min()
    s_max = s.max()

    if pd.isna(s_min) or pd.isna(s_max):
        return pd.Series(np.zeros(len(series)), index=series.index)

    if float(s_max) == float(s_min):
        return pd.Series(np.ones(len(series)) * 0.5, index=series.index)

    return (s - s_min) / (s_max - s_min)


def _risk_category(score: float) -> str:
    if score >= 0.75:
        return "Alta"
    if score >= 0.50:
        return "Media-Alta"
    if score >= 0.25:
        return "Media"
    return "Baja"