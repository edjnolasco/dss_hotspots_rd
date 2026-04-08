from io import BytesIO
from pathlib import Path
import pandas as pd
import requests
from .province_utils import canonical_province, normalize_text

OFFICIAL_PROVINCES_URL = "http://digesett.gob.do/transparencia/index.php/estadisticas/category/359-datos-abiertos?download=417:fallecimientos-segun-provincia&start=20"
PROVINCES_GEOJSON_URL = "https://raw.githubusercontent.com/jeasoft/provinces_geojson/master/provinces_municipality_summary.geojson"

PROVINCE_SYNONYMS = ["provincia", "provincias", "province"]
YEAR_SYNONYMS = ["año", "ano", "year"]
VALUE_SYNONYMS = ["fallecidos", "fallecimiento", "cantidad", "total_fallecidos", "valor"]

def read_dataframe_from_bytes(content: bytes, filename_hint: str = "dataset.csv") -> pd.DataFrame:
    return pd.read_excel(BytesIO(content)) if filename_hint.lower().endswith((".xlsx", ".xls")) else pd.read_csv(BytesIO(content))

def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    normalized_map = {normalize_text(c): c for c in df.columns}
    for c in candidates:
        if c in normalized_map:
            return normalized_map[c]
    return None

def load_local_dataframe(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    return pd.read_excel(path) if path.suffix.lower() in [".xlsx", ".xls"] else pd.read_csv(path)

def fetch_remote_dataframe(url: str, filename_hint: str = "dataset.csv", timeout: int = 30) -> pd.DataFrame:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return read_dataframe_from_bytes(response.content, filename_hint)

def normalize_official_provinces(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work.columns = [normalize_text(c) for c in work.columns]
    province_col = find_column(work, PROVINCE_SYNONYMS)
    year_col = find_column(work, YEAR_SYNONYMS)
    value_col = find_column(work, VALUE_SYNONYMS)
    if not province_col or not year_col or not value_col:
        raise ValueError("No fue posible identificar columnas equivalentes a provincia, año y fallecidos.")
    out = work[[province_col, year_col, value_col]].copy()
    out.columns = ["provincia", "year", "fallecidos"]
    out["provincia"] = out["provincia"].astype(str).map(canonical_province)
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["fallecidos"] = pd.to_numeric(out["fallecidos"], errors="coerce")
    out = out.dropna(subset=["provincia", "year", "fallecidos"]).copy()
    out["year"] = out["year"].astype(int)
    out["month"] = 1
    out["fecha"] = pd.to_datetime(dict(year=out["year"], month=1, day=1))
    return out.sort_values(["year", "provincia"]).reset_index(drop=True)

def fetch_geojson_text(url: str = PROVINCES_GEOJSON_URL, timeout: int = 30) -> str:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return response.text
