from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RuleResult:
    categoria: str
    regla_aplicada: str
    justificacion: str
    recomendacion: str


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def classify_priority(
    score: float,
    delta_abs: float,
    delta_pct: float,
    pred_fallecidos_next: float,
) -> RuleResult:
    """
    Motor de reglas del DSS.

    Variables de entrada:
    - score: score_riesgo normalizado [0,1]
    - delta_abs: cambio absoluto estimado respecto al valor actual
    - delta_pct: cambio porcentual estimado respecto al valor actual
    - pred_fallecidos_next: predicción del siguiente período

    Reglas propuestas:
    1) Alta prioridad
       - score >= 0.80
       - o score >= 0.70 y crecimiento absoluto/relativo relevante
    2) Vigilancia preventiva
       - score >= 0.55 y crecimiento positivo
       - o score medio con señal operativa de aumento
    3) Seguimiento rutinario
       - resto de casos
    """

    # -----------------------------------------------------------------
    # Regla 1: alta prioridad por riesgo muy alto
    # -----------------------------------------------------------------
    if score >= 0.80:
        return RuleResult(
            categoria="Alta prioridad",
            regla_aplicada="R1: score_riesgo >= 0.80",
            justificacion=(
                f"El score de riesgo ({score:.3f}) supera el umbral alto del DSS. "
                f"Esto indica una posición relativa crítica dentro del conjunto analizado."
            ),
            recomendacion=(
                "Priorizar intervención inmediata, revisión operativa focalizada, "
                "seguimiento intensivo y asignación preferente de recursos preventivos."
            ),
        )

    # -----------------------------------------------------------------
    # Regla 2: alta prioridad por combinación de riesgo alto + crecimiento
    # -----------------------------------------------------------------
    if score >= 0.70 and (delta_abs > 0 or delta_pct >= 10.0):
        return RuleResult(
            categoria="Alta prioridad",
            regla_aplicada="R2: score_riesgo >= 0.70 y señal de crecimiento reciente",
            justificacion=(
                f"La provincia combina un score alto ({score:.3f}) con una señal de aumento "
                f"reciente (delta_abs={delta_abs:.2f}, delta_pct={delta_pct:.2f}%). "
                f"En el contexto del DSS, esta combinación se trata como prioridad alta."
            ),
            recomendacion=(
                "Elevar la provincia al grupo de intervención prioritaria, "
                "reforzar monitoreo y preparar medidas preventivas de ejecución inmediata."
            ),
        )

    # -----------------------------------------------------------------
    # Regla 3: vigilancia preventiva por score medio-alto y aumento reciente
    # -----------------------------------------------------------------
    if score >= 0.55 and delta_abs > 0:
        return RuleResult(
            categoria="Vigilancia preventiva",
            regla_aplicada="R3: score_riesgo >= 0.55 y delta_abs > 0",
            justificacion=(
                f"El score ({score:.3f}) se sitúa en una franja de atención operativa y, "
                f"además, la variación absoluta reciente es positiva ({delta_abs:.2f}). "
                f"Esto sugiere una posible intensificación del riesgo."
            ),
            recomendacion=(
                "Mantener vigilancia preventiva, monitorear evolución en el próximo período "
                "y preparar escalamiento si la tendencia ascendente persiste."
            ),
        )

    # -----------------------------------------------------------------
    # Regla 4: vigilancia preventiva por predicción elevada aunque sin gran delta
    # -----------------------------------------------------------------
    if score >= 0.55 and pred_fallecidos_next >= 1.0:
        return RuleResult(
            categoria="Vigilancia preventiva",
            regla_aplicada="R4: score_riesgo >= 0.55 y predicción operativamente relevante",
            justificacion=(
                f"Aunque no se observa una aceleración fuerte reciente, la provincia mantiene "
                f"un score medio-alto ({score:.3f}) y una predicción esperada de "
                f"{pred_fallecidos_next:.2f} para el próximo período."
            ),
            recomendacion=(
                "Sostener vigilancia preventiva, revisar evolución comparada con provincias "
                "vecinas y mantener la provincia dentro del grupo de seguimiento reforzado."
            ),
        )

    # -----------------------------------------------------------------
    # Regla 5: seguimiento rutinario
    # -----------------------------------------------------------------
    return RuleResult(
        categoria="Seguimiento rutinario",
        regla_aplicada="R5: caso residual del motor DSS",
        justificacion=(
            f"La provincia no alcanza los umbrales de prioridad alta ni de vigilancia "
            f"preventiva. El score actual ({score:.3f}) y los cambios recientes no "
            f"justifican escalamiento en esta iteración."
        ),
        recomendacion=(
            "Mantener seguimiento rutinario, conservar observación periódica y reevaluar "
            "en el próximo ciclo de análisis."
        ),
    )


def apply_rules(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica el motor DSS sobre un dataframe que contiene, como mínimo:
    - score_riesgo
    - delta_abs

    Si están disponibles, también aprovecha:
    - delta_pct
    - pred_fallecidos_next

    Devuelve el dataframe enriquecido con:
    - categoria
    - regla_aplicada
    - justificacion_regla
    - recomendacion
    """
    out = df.copy()

    required_cols = {"score_riesgo", "delta_abs"}
    missing = required_cols - set(out.columns)
    if missing:
        raise ValueError(
            f"Faltan columnas requeridas para aplicar reglas DSS: {sorted(missing)}"
        )

    out["score_riesgo"] = pd.to_numeric(out["score_riesgo"], errors="coerce").fillna(0.0)
    out["delta_abs"] = pd.to_numeric(out["delta_abs"], errors="coerce").fillna(0.0)

    if "delta_pct" not in out.columns:
        out["delta_pct"] = 0.0
    out["delta_pct"] = pd.to_numeric(out["delta_pct"], errors="coerce").fillna(0.0)

    if "pred_fallecidos_next" not in out.columns:
        out["pred_fallecidos_next"] = 0.0
    out["pred_fallecidos_next"] = pd.to_numeric(
        out["pred_fallecidos_next"],
        errors="coerce",
    ).fillna(0.0)

    rule_outputs = [
        classify_priority(
            score=_to_float(score),
            delta_abs=_to_float(delta_abs),
            delta_pct=_to_float(delta_pct),
            pred_fallecidos_next=_to_float(pred_next),
        )
        for score, delta_abs, delta_pct, pred_next in zip(
            out["score_riesgo"],
            out["delta_abs"],
            out["delta_pct"],
            out["pred_fallecidos_next"],
        )
    ]

    out["categoria"] = [r.categoria for r in rule_outputs]
    out["regla_aplicada"] = [r.regla_aplicada for r in rule_outputs]
    out["justificacion_regla"] = [r.justificacion for r in rule_outputs]
    out["recomendacion"] = [r.recomendacion for r in rule_outputs]

    return out