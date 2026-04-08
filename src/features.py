from __future__ import annotations

import pandas as pd
import numpy as np


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construye variables derivadas para el DSS a partir del dataset normalizado.

    Requisitos de entrada:
    - provincia
    - year
    - month
    - fecha
    - fallecidos

    Salida:
    - dataframe enriquecido con variables temporales y target_next
    """
    work = df.copy()

    # ------------------------------------------------------------
    # Normalización mínima defensiva
    # ------------------------------------------------------------
    work["provincia"] = work["provincia"].astype(str).str.strip()
    work["year"] = pd.to_numeric(work["year"], errors="coerce")
    work["month"] = pd.to_numeric(work["month"], errors="coerce")
    work["fallecidos"] = pd.to_numeric(work["fallecidos"], errors="coerce")

    work = work.dropna(subset=["provincia", "year", "month", "fallecidos"]).copy()

    work["year"] = work["year"].astype(int)
    work["month"] = work["month"].astype(int)

    # ------------------------------------------------------------
    # Fecha consistente
    # ------------------------------------------------------------
    if "fecha" not in work.columns:
        work["fecha"] = pd.to_datetime(
            dict(year=work["year"], month=work["month"], day=1)
        )
    else:
        work["fecha"] = pd.to_datetime(work["fecha"], errors="coerce")

    work = work.dropna(subset=["fecha"]).copy()

    # ------------------------------------------------------------
    # Orden temporal por provincia
    # ------------------------------------------------------------
    work = work.sort_values(["provincia", "fecha"]).reset_index(drop=True)

    grp = work.groupby("provincia", group_keys=False)

    # ------------------------------------------------------------
    # Variables lag
    # ------------------------------------------------------------
    work["fallecidos_prev_1"] = grp["fallecidos"].shift(1)
    work["fallecidos_prev_2"] = grp["fallecidos"].shift(2)

    # ------------------------------------------------------------
    # Variación absoluta
    # ------------------------------------------------------------
    work["delta_abs"] = work["fallecidos"] - work["fallecidos_prev_1"]

    # ------------------------------------------------------------
    # Variación porcentual
    # Evita división por cero
    # ------------------------------------------------------------
    work["delta_pct"] = np.where(
        work["fallecidos_prev_1"].fillna(0) != 0,
        (work["fallecidos"] - work["fallecidos_prev_1"]) / work["fallecidos_prev_1"],
        0.0,
    )

    # ------------------------------------------------------------
    # Estadísticos móviles
    # ------------------------------------------------------------
    work["rolling_mean_3"] = (
        grp["fallecidos"]
        .rolling(3, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )

    work["rolling_std_3"] = (
        grp["fallecidos"]
        .rolling(3, min_periods=1)
        .std()
        .reset_index(level=0, drop=True)
        .fillna(0.0)
    )

    # ------------------------------------------------------------
    # Promedio acumulado histórico
    # ------------------------------------------------------------
    work["cum_mean"] = (
        grp["fallecidos"]
        .expanding()
        .mean()
        .reset_index(level=0, drop=True)
    )

    # ------------------------------------------------------------
    # Índice temporal
    # ------------------------------------------------------------
    work["year_index"] = work["year"] - work["year"].min()

    # ------------------------------------------------------------
    # Codificación cíclica del mes
    # En tu caso mensual real o anual forzado a month=1
    # ------------------------------------------------------------
    work["month_sin"] = np.sin(2 * np.pi * work["month"] / 12.0)
    work["month_cos"] = np.cos(2 * np.pi * work["month"] / 12.0)

    # ------------------------------------------------------------
    # Target del siguiente período
    # ------------------------------------------------------------
    work["target_next"] = grp["fallecidos"].shift(-1)

    return work
