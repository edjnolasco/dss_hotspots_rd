from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

from src.province_utils import canonical_province, display_province_name

OFFICIAL_PROVINCES_URL = (
    "https://digesett.gob.do/transparencia/phocadownload/estadisticas/"
    "fallecimientos_por_provincias.csv"
)

REQUEST_TIMEOUT = 30


def fetch_remote_dataframe(
    url: str,
    filename_hint: str | None = None,
    timeout: int = REQUEST_TIMEOUT,
) -> pd.DataFrame:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    content = response.content
    return read_dataframe_from_bytes(
        file_bytes=content,
        filename_hint=filename_hint or url,
    )


def load_local_dataframe(path_str: str) -> pd.DataFrame:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {path_str}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return _read_csv_with_fallbacks(path.read_bytes())

    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)

    raise ValueError(
        f"Formato no soportado para '{path.name}'. "
        "Usa CSV, XLSX o XLS."
    )


def read_dataframe_from_bytes(
    file_bytes: bytes,
    filename_hint: str | None = None,
) -> pd.DataFrame:
    suffix = Path(filename_hint or "").suffix.lower()

    if suffix == ".csv":
        return _read_csv_with_fallbacks(file_bytes)

    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(BytesIO(file_bytes))

    try:
        return _read_csv_with_fallbacks(file_bytes)
    except Exception:
        pass

    try:
        return pd.read_excel(BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(
            "No fue posible interpretar el archivo como CSV o Excel."
        ) from exc


def _read_csv_with_fallbacks(file_bytes: bytes) -> pd.DataFrame:
    attempts: list[dict] = [
        {"sep": ",", "encoding": "utf-8"},
        {"sep": ";", "encoding": "utf-8"},
        {"sep": ",", "encoding": "utf-8-sig"},
        {"sep": ";", "encoding": "utf-8-sig"},
        {"sep": ",", "encoding": "latin-1"},
        {"sep": ";", "encoding": "latin-1"},
    ]

    last_error: Exception | None = None

    for opts in attempts:
        try:
            df = pd.read_csv(BytesIO(file_bytes), **opts)
            if not df.empty and len(df.columns) >= 1:
                return df
        except Exception as exc:
            last_error = exc

    raise ValueError("No fue posible leer el CSV.") from last_error


def normalize_official_provinces(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError("El DataFrame de entrada está vacío.")

    working = df.copy()
    working.columns = [str(col).strip() for col in working.columns]

    province_col = _resolve_column(
        working,
        candidates=[
            "provincia",
            "province",
            "nombre_provincia",
            "prov",
            "region",
        ],
        semantic_hint="provincia",
    )
    year_col = _resolve_column(
        working,
        candidates=[
            "year",
            "anio",
            "año",
            "periodo",
            "period",
        ],
        semantic_hint="year",
    )
    deaths_col = _resolve_column(
        working,
        candidates=[
            "fallecidos",
            "muertes",
            "defunciones",
            "fatalidades",
            "victimas",
            "víctimas",
            "cantidad",
            "total",
        ],
        semantic_hint="fallecidos",
    )

    normalized = pd.DataFrame(
        {
            "provincia_raw": working[province_col].astype(str).str.strip(),
            "year": pd.to_numeric(working[year_col], errors="coerce"),
            "fallecidos": pd.to_numeric(working[deaths_col], errors="coerce"),
        }
    )

    normalized = normalized.dropna(
        subset=["provincia_raw", "year", "fallecidos"]
    ).copy()

    normalized["year"] = normalized["year"].astype(int)
    normalized["fallecidos"] = normalized["fallecidos"].astype(float)

    normalized["provincia_canonica"] = normalized["provincia_raw"].map(canonical_province)
    normalized["provincia"] = normalized["provincia_raw"].map(display_province_name)

    normalized = normalized[
        normalized["provincia"].astype(str).str.strip().ne("")
    ].copy()

    normalized = normalized[
        normalized["provincia_canonica"].astype(str).str.strip().ne("")
    ].copy()

    normalized = (
        normalized.groupby(
            ["provincia", "provincia_canonica", "year"],
            as_index=False,
        )["fallecidos"]
        .sum()
        .sort_values(["year", "provincia"])
        .reset_index(drop=True)
    )

    # Garantías mínimas para el pipeline / CI
    # Dataset anual por provincia: se fija month=1 y fecha=YYYY-01-01.
    normalized["month"] = 1
    normalized["fecha"] = pd.to_datetime(
        dict(year=normalized["year"], month=normalized["month"], day=1),
        errors="coerce",
    )

    # Orden estable de columnas principales
    ordered_cols = [
        "provincia",
        "provincia_canonica",
        "year",
        "month",
        "fecha",
        "fallecidos",
    ]
    remaining_cols = [c for c in normalized.columns if c not in ordered_cols]
    normalized = normalized[ordered_cols + remaining_cols].copy()

    return normalized.reset_index(drop=True)


def _resolve_column(
    df: pd.DataFrame,
    candidates: list[str],
    semantic_hint: str | None = None,
) -> str:
    normalized_map = {
        _normalize_column_name(col): col
        for col in df.columns
    }

    for candidate in candidates:
        norm_candidate = _normalize_column_name(candidate)
        if norm_candidate in normalized_map:
            return normalized_map[norm_candidate]

    if semantic_hint:
        hint = _normalize_column_name(semantic_hint)

        partial_matches = [
            original
            for norm, original in normalized_map.items()
            if hint in norm
        ]
        if len(partial_matches) == 1:
            return partial_matches[0]

    raise KeyError(
        f"No fue posible identificar una columna compatible. "
        f"Columnas disponibles: {list(df.columns)}"
    )


def _normalize_column_name(value: str) -> str:
    text = str(value).strip().lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    for ch in [" ", "-", ".", "/", "\\", "(", ")", "[", "]", "{", "}", ":"]:
        text = text.replace(ch, "_")

    while "__" in text:
        text = text.replace("__", "_")

    return text.strip("_")