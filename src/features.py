import pandas as pd
import numpy as np

def create_features(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["fecha"] = pd.to_datetime(work["fecha"])
    work = work.sort_values(["provincia", "fecha"]).reset_index(drop=True)
    grp = work.groupby("provincia", group_keys=False)
    work["fallecidos_prev_1"] = grp["fallecidos"].shift(1)
    work["fallecidos_prev_2"] = grp["fallecidos"].shift(2)
    work["delta_abs"] = work["fallecidos"] - work["fallecidos_prev_1"]
    work["delta_pct"] = np.where(work["fallecidos_prev_1"].fillna(0) != 0, (work["fallecidos"] - work["fallecidos_prev_1"]) / work["fallecidos_prev_1"], 0.0)
    work["rolling_mean_3"] = grp["fallecidos"].rolling(3, min_periods=1).mean().reset_index(level=0, drop=True)
    work["rolling_std_3"] = grp["fallecidos"].rolling(3, min_periods=1).std().reset_index(level=0, drop=True).fillna(0.0)
    work["cum_mean"] = grp["fallecidos"].expanding().mean().reset_index(level=0, drop=True)
    work["year_index"] = work["year"] - work["year"].min()
    work["month_sin"] = np.sin(2 * np.pi * work["month"] / 12.0)
    work["month_cos"] = np.cos(2 * np.pi * work["month"] / 12.0)
    work["target_next"] = grp["fallecidos"].shift(-1)
    return work
