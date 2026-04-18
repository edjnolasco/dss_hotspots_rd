from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import math
import re

import pandas as pd


PROVINCE_CANDIDATES = (
    "provincia",
    "province",
    "nombre_provincia",
    "name",
    "name_1",
)

SCORE_CANDIDATES = (
    "risk_score",
    "score",
    "puntaje",
    "indice_riesgo",
    "risk_index",
    "priority_score",
)

RANK_CANDIDATES = (
    "rank",
    "ranking",
    "posicion",
    "position",
)

FATALITIES_CANDIDATES = (
    "fallecidos",
    "fatalities",
    "deaths",
    "muertes",
)

YEAR_CANDIDATES = (
    "year",
    "anio",
    "año",
)

TREND_CANDIDATES = (
    "trend",
    "tendencia",
    "trend_label",
)

RULES_CANDIDATES = (
    "rule_trigger_count",
    "rules_triggered",
    "cantidad_reglas",
    "reglas_activadas",
)

EXPECTED_TOP_K_KEYS = (
    "top_k_accuracy",
    "topk_accuracy",
    "hit_rate_at_k",
    "hitrate_at_k",
    "hit_rate",
)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def _as_dataframe(obj: Any) -> pd.DataFrame:
    if isinstance(obj, pd.DataFrame):
        return obj.copy()

    if obj is None:
        return pd.DataFrame()

    if isinstance(obj, list):
        try:
            return pd.DataFrame(obj)
        except Exception:
            return pd.DataFrame()

    return pd.DataFrame()


def _find_first_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    if df.empty:
        return None

    normalized = {str(col).strip().lower(): col for col in df.columns}
    for candidate in candidates:
        col = normalized.get(candidate.lower())
        if col is not None:
            return col

    return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if _is_missing(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if _is_missing(value):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if _is_missing(value):
        return default
    return str(value).strip()


def _format_number(value: float, decimals: int = 2) -> str:
    if math.isnan(value) or math.isinf(value):
        return "0"
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_percent(value: float, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}%"


def _extract_metrics(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}

    for key in ("metrics", "metricas", "evaluation", "evaluacion", "metricas_df"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            return dict(value)

    return {}


def _extract_ranking_df(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    if not isinstance(payload, Mapping):
        return pd.DataFrame()

    for key in ("ranking_df", "ranking", "results_df", "resultados_df", "topk_df"):
        if key in payload:
            return _as_dataframe(payload.get(key))

    return pd.DataFrame()


def _extract_analysis_df(payload: Mapping[str, Any] | None) -> pd.DataFrame:
    if not isinstance(payload, Mapping):
        return pd.DataFrame()

    for key in ("analysis_df", "features_df", "dataset_df", "data_df", "merged_df"):
        if key in payload:
            return _as_dataframe(payload.get(key))

    return pd.DataFrame()


def _extract_top_k(metrics: Mapping[str, Any]) -> float | None:
    for key in EXPECTED_TOP_K_KEYS:
        if key in metrics:
            return _safe_float(metrics[key], default=0.0)
    return None


def _prepare_ranking(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()

    province_col = _find_first_column(result, PROVINCE_CANDIDATES)
    score_col = _find_first_column(result, SCORE_CANDIDATES)
    rank_col = _find_first_column(result, RANK_CANDIDATES)

    if score_col is not None:
        result[score_col] = pd.to_numeric(result[score_col], errors="coerce").fillna(0.0)

    if rank_col is None:
        if score_col is not None:
            result = result.sort_values(by=score_col, ascending=False).reset_index(drop=True)
            result["rank"] = range(1, len(result) + 1)
        else:
            result = result.reset_index(drop=True)
            result["rank"] = range(1, len(result) + 1)
    else:
        result = result.sort_values(by=rank_col, ascending=True).reset_index(drop=True)

    if province_col is None:
        result["provincia"] = [f"Provincia {i}" for i in range(1, len(result) + 1)]

    return result


def _normalize_inputs(
    pipeline_output: Mapping[str, Any] | None = None,
    ranking_df: pd.DataFrame | list[dict[str, Any]] | None = None,
    metrics: Mapping[str, Any] | pd.DataFrame | None = None,
    analysis_df: pd.DataFrame | list[dict[str, Any]] | None = None,
    **kwargs: Any,
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    """
    Normaliza entradas para soportar ambas firmas:
    1) build_*(pipeline_output={...})
    2) build_*(ranking_df=..., metrics=..., analysis_df=...)
    """
    ranking_from_payload = _extract_ranking_df(pipeline_output)
    metrics_from_payload = _extract_metrics(pipeline_output)
    analysis_from_payload = _extract_analysis_df(pipeline_output)

    final_ranking_df = _prepare_ranking(
        _as_dataframe(ranking_df) if ranking_df is not None else ranking_from_payload
    )

    if isinstance(metrics, pd.DataFrame):
        final_metrics = {}
    else:
        final_metrics = dict(metrics) if isinstance(metrics, Mapping) else metrics_from_payload

    final_analysis_df = (
        _as_dataframe(analysis_df) if analysis_df is not None else analysis_from_payload
    )

    if final_ranking_df.empty:
        for key in ("results_df", "resultados_df", "topk_df", "ranking"):
            if key in kwargs:
                final_ranking_df = _prepare_ranking(_as_dataframe(kwargs[key]))
                break

    if not final_metrics:
        for key in ("metricas", "evaluation", "evaluacion"):
            value = kwargs.get(key)
            if isinstance(value, Mapping):
                final_metrics = dict(value)
                break

    if final_analysis_df.empty:
        for key in ("data_df", "dataset_df", "merged_df", "features_df"):
            if key in kwargs:
                final_analysis_df = _as_dataframe(kwargs[key])
                break

    return final_ranking_df, final_metrics, final_analysis_df


def _build_top_provinces_sentence(ranking_df: pd.DataFrame, top_n: int = 5) -> str:
    if ranking_df.empty:
        return (
            "No fue posible identificar provincias priorizadas porque el ranking "
            "de salida no contiene registros válidos."
        )

    province_col = _find_first_column(ranking_df, PROVINCE_CANDIDATES) or "provincia"
    score_col = _find_first_column(ranking_df, SCORE_CANDIDATES)
    rank_col = _find_first_column(ranking_df, RANK_CANDIDATES) or "rank"

    top_df = ranking_df.head(top_n).copy()

    parts: list[str] = []
    for _, row in top_df.iterrows():
        province = _safe_str(row.get(province_col), default="Provincia sin nombre")
        rank_value = _safe_int(row.get(rank_col), default=len(parts) + 1)

        if score_col is not None:
            score_value = _safe_float(row.get(score_col), default=0.0)
            parts.append(
                f"{rank_value}) {province} (puntaje {_format_number(score_value, 2)})"
            )
        else:
            parts.append(f"{rank_value}) {province}")

    return "Las provincias con mayor prioridad en el corte analizado son: " + "; ".join(parts) + "."


def _build_concentration_sentence(ranking_df: pd.DataFrame, top_n: int = 5) -> str:
    if ranking_df.empty:
        return ""

    score_col = _find_first_column(ranking_df, SCORE_CANDIDATES)
    if score_col is None:
        return ""

    total_score = _safe_float(ranking_df[score_col].sum(), default=0.0)
    if total_score <= 0:
        return ""

    top_score = _safe_float(ranking_df.head(top_n)[score_col].sum(), default=0.0)
    share = top_score / total_score if total_score > 0 else 0.0

    return (
        f"En términos de concentración del riesgo estimado, el Top-{top_n} acumula "
        f"{_format_percent(share, 1)} del puntaje total observado en el ranking."
    )


def _build_metric_sentence(metrics: Mapping[str, Any]) -> str:
    if not metrics:
        return (
            "No se localizaron métricas de evaluación en la salida del pipeline, por lo que "
            "la narrativa se enfoca en la priorización generada."
        )

    fragments: list[str] = []

    top_k = _extract_top_k(metrics)
    if top_k is not None:
        fragments.append(f"HitRate@K/Top-K accuracy: {_format_percent(top_k, 1)}")

    for key in ("precision", "recall", "f1", "roc_auc", "auc", "mae", "rmse", "r2"):
        if key in metrics:
            label = {
                "precision": "Precisión",
                "recall": "Recall",
                "f1": "F1",
                "roc_auc": "ROC-AUC",
                "auc": "AUC",
                "mae": "MAE",
                "rmse": "RMSE",
                "r2": "R²",
            }[key]
            fragments.append(f"{label}: {_format_number(_safe_float(metrics[key]), 3)}")

    if "coverage" in metrics:
        fragments.append(f"Cobertura: {_format_percent(_safe_float(metrics['coverage']), 1)}")

    if not fragments:
        return (
            "La salida incluye métricas, pero no en un formato narrativamente explotable "
            "por esta versión del módulo."
        )

    return "Desde la perspectiva de desempeño del sistema, se observan los siguientes indicadores: " + "; ".join(fragments) + "."


def _build_data_support_sentence(
    ranking_df: pd.DataFrame,
    analysis_df: pd.DataFrame,
) -> str:
    ranking_count = len(ranking_df)
    analysis_count = len(analysis_df)

    if ranking_count == 0 and analysis_count == 0:
        return (
            "No se dispone de suficiente evidencia tabular en la salida para describir "
            "el soporte cuantitativo del análisis."
        )

    if ranking_count > 0 and analysis_count > 0:
        return (
            f"El resultado narrativo se apoya en {analysis_count} registros analíticos procesados "
            f"y en un ranking final compuesto por {ranking_count} filas priorizadas."
        )

    if ranking_count > 0:
        return f"El ranking final contiene {ranking_count} filas priorizadas utilizadas para la síntesis ejecutiva."

    return f"La base analítica disponible para esta narrativa contiene {analysis_count} registros procesados."


def _build_caution_sentence(ranking_df: pd.DataFrame, metrics: Mapping[str, Any]) -> str:
    has_scores = _find_first_column(ranking_df, SCORE_CANDIDATES) is not None
    has_topk = _extract_top_k(metrics) is not None

    if has_scores and has_topk:
        return (
            "Esta salida debe interpretarse como un instrumento de apoyo a la decisión y no "
            "como un sustituto del criterio experto, ya que la priorización integra señales "
            "predictivas y reglas de negocio sujetas a revisión operativa."
        )

    return (
        "La interpretación del resultado debe mantenerse en un plano de apoyo a la decisión. "
        "Cuando existan cambios en la calidad del dato, cobertura territorial o reglas de negocio, "
        "el ranking puede variar y debe recalibrarse."
    )


def _split_sentences(text: str) -> list[str]:
    if not text:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def format_topk_list(text: str) -> list[str]:
    """
    Convierte la frase de Top-K en lista de ítems.
    """
    if not text:
        return []

    if ":" not in text:
        return [text]

    _, right = text.split(":", 1)
    items = [item.strip().rstrip(".") for item in right.split(";") if item.strip()]
    return items


def format_executive_narrative(text: str) -> dict[str, Any]:
    """
    Convierte una narrativa lineal en bloques estructurados tipo informe ejecutivo.
    """
    blocks: dict[str, Any] = {
        "contexto": "",
        "resumen": "",
        "topk_text": "",
        "topk_items": [],
        "metricas": "",
        "interpretacion": "",
        "cierre": "",
    }

    for sentence in _split_sentences(text):
        lower = sentence.lower()

        if "sistema de soporte a la decisión" in lower:
            blocks["contexto"] += sentence + " "
        elif "ranking final contiene" in lower or "resultado narrativo se apoya" in lower:
            blocks["resumen"] += sentence + " "
        elif "provincias con mayor prioridad" in lower:
            blocks["topk_text"] += sentence + " "
        elif (
            "desempeño del sistema" in lower
            or "hitrate@k" in lower
            or "top-k accuracy" in lower
            or "mae:" in lower
            or "rmse:" in lower
            or "r²:" in lower
        ):
            blocks["metricas"] += sentence + " "
        elif (
            "apoyo a la decisión" in lower
            or "criterio experto" in lower
            or "debe interpretarse" in lower
            or "recalibrarse" in lower
        ):
            blocks["cierre"] += sentence + " "
        else:
            blocks["interpretacion"] += sentence + " "

    blocks = {
        key: value.strip() if isinstance(value, str) else value
        for key, value in blocks.items()
    }

    blocks["topk_items"] = format_topk_list(blocks["topk_text"])

    return blocks


def build_executive_summary(
    pipeline_output: Mapping[str, Any] | None = None,
    *,
    ranking_df: pd.DataFrame | list[dict[str, Any]] | None = None,
    metrics: Mapping[str, Any] | None = None,
    analysis_df: pd.DataFrame | list[dict[str, Any]] | None = None,
    top_n: int = 5,
    **kwargs: Any,
) -> str:
    """
    Construye un resumen ejecutivo amplio y tolerante a variaciones en la salida
    del pipeline.
    """
    final_ranking_df, final_metrics, final_analysis_df = _normalize_inputs(
        pipeline_output=pipeline_output,
        ranking_df=ranking_df,
        metrics=metrics,
        analysis_df=analysis_df,
        **kwargs,
    )

    paragraphs = [
        (
            "El sistema de soporte a la decisión generó una priorización territorial orientada a "
            "identificar provincias que requieren mayor atención relativa dentro del escenario evaluado."
        ),
        _build_data_support_sentence(final_ranking_df, final_analysis_df),
        _build_top_provinces_sentence(final_ranking_df, top_n=top_n),
    ]

    concentration_sentence = _build_concentration_sentence(final_ranking_df, top_n=top_n)
    if concentration_sentence:
        paragraphs.append(concentration_sentence)

    paragraphs.append(_build_metric_sentence(final_metrics))
    paragraphs.append(_build_caution_sentence(final_ranking_df, final_metrics))

    return "\n\n".join(p for p in paragraphs if p.strip())


def build_brief_executive_summary(
    pipeline_output: Mapping[str, Any] | None = None,
    *,
    ranking_df: pd.DataFrame | list[dict[str, Any]] | None = None,
    metrics: Mapping[str, Any] | None = None,
    analysis_df: pd.DataFrame | list[dict[str, Any]] | None = None,
    top_n: int = 3,
    **kwargs: Any,
) -> str:
    """
    Construye una versión breve del resumen ejecutivo para tarjetas, paneles
    laterales o encabezados de resultados.
    """
    final_ranking_df, final_metrics, _ = _normalize_inputs(
        pipeline_output=pipeline_output,
        ranking_df=ranking_df,
        metrics=metrics,
        analysis_df=analysis_df,
        **kwargs,
    )

    if final_ranking_df.empty:
        return (
            "No se generó un ranking priorizado con información suficiente para "
            "resumir los resultados del análisis."
        )

    province_col = _find_first_column(final_ranking_df, PROVINCE_CANDIDATES) or "provincia"
    top_items = (
        final_ranking_df.head(top_n)[province_col]
        .fillna("Provincia sin nombre")
        .astype(str)
        .tolist()
    )
    province_list = ", ".join(top_items)

    parts = [
        f"El DSS prioriza como focos principales a: {province_list}."
    ]

    top_k = _extract_top_k(final_metrics)
    if top_k is not None:
        parts.append(f"El desempeño Top-K reportado alcanza {_format_percent(top_k, 1)}.")

    score_col = _find_first_column(final_ranking_df, SCORE_CANDIDATES)
    if score_col is not None and len(final_ranking_df) >= top_n:
        spread = (
            _safe_float(final_ranking_df.iloc[0][score_col])
            - _safe_float(final_ranking_df.iloc[top_n - 1][score_col])
        )
        parts.append(
            f"La separación entre la primera y la provincia ubicada en la posición {top_n} "
            f"es de {_format_number(spread, 2)} puntos."
        )

    parts.append(
        "La salida debe leerse como apoyo a la priorización operativa y no como decisión automática final."
    )

    return " ".join(parts)


def build_topk_narrative(
    pipeline_output: Mapping[str, Any] | None = None,
    *,
    ranking_df: pd.DataFrame | list[dict[str, Any]] | None = None,
    metrics: Mapping[str, Any] | None = None,
    analysis_df: pd.DataFrame | list[dict[str, Any]] | None = None,
    top_n: int = 10,
    **kwargs: Any,
) -> str:
    """
    Genera una narrativa específica para explicar la lógica de priorización Top-K.
    """
    final_ranking_df, final_metrics, _ = _normalize_inputs(
        pipeline_output=pipeline_output,
        ranking_df=ranking_df,
        metrics=metrics,
        analysis_df=analysis_df,
        **kwargs,
    )

    if final_ranking_df.empty:
        return (
            "No se dispone de ranking para construir una explicación específica "
            "sobre la priorización Top-K."
        )

    effective_top_n = min(top_n, len(final_ranking_df))

    top_sentence = _build_top_provinces_sentence(final_ranking_df, top_n=effective_top_n)
    concentration_sentence = _build_concentration_sentence(final_ranking_df, top_n=effective_top_n)
    metric_sentence = _build_metric_sentence(final_metrics)

    return " ".join(
        part
        for part in (top_sentence, concentration_sentence, metric_sentence)
        if part.strip()
    )


def build_narrative(
    ranking_df: pd.DataFrame,
    metricas_df: pd.DataFrame | Mapping[str, Any] | None,
    latest_year: int,
    model_label: str | None = None,
) -> str:
    """
    Wrapper de compatibilidad para el pipeline.
    Usa el resumen ejecutivo existente y añade el modelo utilizado.
    """
    metrics_payload: Mapping[str, Any] | None = None
    if isinstance(metricas_df, Mapping):
        metrics_payload = metricas_df

    try:
        base_text = build_executive_summary(
            ranking_df=ranking_df,
            metrics=metrics_payload,
            analysis_df=None,
            top_n=5,
        )
    except Exception:
        base_text = (
            f"El análisis del año {latest_year} identifica provincias con mayor "
            f"criticidad relativa para priorización territorial."
        )

    if model_label:
        return f"{base_text}\n\nMotor predictivo utilizado: {model_label}."

    return base_text


__all__ = [
    "build_brief_executive_summary",
    "build_executive_summary",
    "build_narrative",
    "build_topk_narrative",
    "format_executive_narrative",
    "format_topk_list",
]