from __future__ import annotations

import streamlit as st

from src.model_catalog import DEFAULT_MODEL_KEY, get_model_options, get_model_spec


def render_model_selector() -> str:
    """
    Renderiza el selector de modelo en sidebar y devuelve la clave elegida.
    """
    options = get_model_options()
    keys = [key for key, _label in options]
    labels = {key: label for key, label in options}

    default_index = keys.index(DEFAULT_MODEL_KEY) if DEFAULT_MODEL_KEY in keys else 0

    model_key = st.radio(
        "Motor predictivo",
        options=keys,
        index=default_index,
        format_func=lambda key: labels[key],
        key="selected_model_key",
        help=(
            "Selecciona el algoritmo que generará el score de riesgo "
            "antes de aplicar reglas DSS y ranking territorial."
        ),
    )

    spec = get_model_spec(model_key)
    st.caption(f"**Familia:** {spec.family} · {spec.description}")

    return model_key