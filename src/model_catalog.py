from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    key: str
    label: str
    family: str
    description: str


MODEL_SPECS: dict[str, ModelSpec] = {
    "random_forest": ModelSpec(
        key="random_forest",
        label="Random Forest",
        family="ensemble",
        description="Modelo base robusto para tabular y no linealidades.",
    ),
    "extra_trees": ModelSpec(
        key="extra_trees",
        label="Extra Trees",
        family="ensemble",
        description="Árboles extremadamente aleatorizados, rápidos y robustos.",
    ),
    "gradient_boosting": ModelSpec(
        key="gradient_boosting",
        label="Gradient Boosting",
        family="boosting",
        description="Boosting clásico para patrones no lineales.",
    ),
    "hist_gradient_boosting": ModelSpec(
        key="hist_gradient_boosting",
        label="HistGradientBoosting",
        family="boosting",
        description="Boosting moderno y eficiente para datasets medianos.",
    ),
    "svr_rbf": ModelSpec(
        key="svr_rbf",
        label="SVM (SVR-RBF)",
        family="svm",
        description="Soporte vectorial con kernel RBF para relaciones no lineales.",
    ),
}

DEFAULT_MODEL_KEY = "random_forest"


def get_model_spec(model_key: str) -> ModelSpec:
    """Devuelve la especificación del modelo o el default si la clave no existe."""
    return MODEL_SPECS.get(model_key, MODEL_SPECS[DEFAULT_MODEL_KEY])


def get_model_label(model_key: str) -> str:
    """Devuelve la etiqueta legible del modelo."""
    return get_model_spec(model_key).label


def get_model_options() -> list[tuple[str, str]]:
    """Lista de opciones para UI: [(key, label), ...]."""
    return [(spec.key, spec.label) for spec in MODEL_SPECS.values()]