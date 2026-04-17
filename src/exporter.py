from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

import pandas as pd


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """
    Exporta un DataFrame a CSV en bytes UTF-8.
    """
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    """
    Exporta múltiples hojas a un archivo Excel en memoria.
    Mantiene compatibilidad con la implementación previa.
    """
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        for name, df in sheets.items():
            safe_name = sanitize_sheet_name(name)
            export_df = ensure_dataframe(df)
            export_df.to_excel(writer, sheet_name=safe_name, index=False)
    bio.seek(0)
    return bio.read()


def ensure_dataframe(data: pd.DataFrame | list[dict[str, Any]] | dict[str, Any] | None) -> pd.DataFrame:
    """
    Normaliza diferentes estructuras a DataFrame.
    """
    if isinstance(data, pd.DataFrame):
        return data.copy()

    if data is None:
        return pd.DataFrame()

    if isinstance(data, dict):
        return pd.DataFrame([(k, stringify_value(v)) for k, v in data.items()], columns=["clave", "valor"])

    if isinstance(data, list):
        return pd.DataFrame(data)

    return pd.DataFrame({"valor": [stringify_value(data)]})


def stringify_value(value: Any) -> str:
    """
    Convierte valores complejos en texto estable para exportación.
    """
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return "; ".join(f"{k}={v}" for k, v in value.items())
    if value is None:
        return ""
    return str(value)


def sanitize_sheet_name(name: str) -> str:
    """
    Excel limita los nombres de hojas a 31 caracteres y prohíbe ciertos símbolos.
    """
    invalid_chars = ["\\", "/", "*", "[", "]", ":", "?"]
    clean_name = str(name).strip() or "Hoja"

    for char in invalid_chars:
        clean_name = clean_name.replace(char, "-")

    return clean_name[:31]


def build_metadata_dataframe(metadata: dict[str, Any]) -> pd.DataFrame:
    """
    Convierte metadata del análisis en una hoja tabular exportable.
    """
    if not metadata:
        return pd.DataFrame(columns=["clave", "valor"])

    rows = [{"clave": key, "valor": stringify_value(value)} for key, value in metadata.items()]
    return pd.DataFrame(rows, columns=["clave", "valor"])


def build_export_filename(
    *,
    project_name: str,
    extension: str,
    selected_years: list[int] | None = None,
    metric_column: str | None = None,
    normalization_mode: str | None = None,
    prefix: str = "dss_export",
) -> str:
    """
    Genera nombres de archivo consistentes y trazables.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    years = selected_years or []
    if years:
        years_label = f"{min(years)}_{max(years)}"
    else:
        years_label = "sin_rango"

    metric_label = (metric_column or "sin_metrica").strip().replace(" ", "_")
    norm_label = (normalization_mode or "raw").strip().replace(" ", "_")
    project_label = str(project_name).strip().replace(" ", "_")

    return f"{project_label}_{prefix}_{years_label}_{metric_label}_{norm_label}_{timestamp}.{extension.lstrip('.')}"


def build_excel_export(
    *,
    filtered_ranking: pd.DataFrame,
    metricas_df: pd.DataFrame,
    scored_df: pd.DataFrame,
    explain_df: pd.DataFrame,
    metadata: dict[str, Any] | None = None,
    extra_sheets: dict[str, pd.DataFrame] | None = None,
) -> bytes:
    """
    Construye una exportación Excel seria para el DSS con hojas estándar.
    """
    sheets: dict[str, pd.DataFrame] = {
        "Ranking": ensure_dataframe(filtered_ranking),
        "Metricas": ensure_dataframe(metricas_df),
        "Datos": ensure_dataframe(scored_df),
        "Explicabilidad": ensure_dataframe(explain_df),
        "Metadata": build_metadata_dataframe(metadata or {}),
    }

    if extra_sheets:
        for name, df in extra_sheets.items():
            sheets[name] = ensure_dataframe(df)

    return to_excel_bytes(sheets)


def build_export_bundle(
    *,
    filtered_ranking: pd.DataFrame,
    metricas_df: pd.DataFrame,
    scored_df: pd.DataFrame,
    explain_df: pd.DataFrame,
    metadata: dict[str, Any] | None = None,
) -> dict[str, bytes]:
    """
    Devuelve un bundle reutilizable con los artefactos de exportación principales.
    """
    metadata = metadata or {}

    ranking_csv = to_csv_bytes(ensure_dataframe(filtered_ranking))
    metadata_csv = to_csv_bytes(build_metadata_dataframe(metadata))
    excel_bytes = build_excel_export(
        filtered_ranking=filtered_ranking,
        metricas_df=metricas_df,
        scored_df=scored_df,
        explain_df=explain_df,
        metadata=metadata,
    )

    return {
        "ranking_csv": ranking_csv,
        "metadata_csv": metadata_csv,
        "excel_report": excel_bytes,
    }