from __future__ import annotations

import streamlit as st

DEFAULT_ACTIVE_SECTION = "Mapa y drill-down"


def ensure_session_state() -> None:
    """
    Inicializa las claves mínimas necesarias para la aplicación.

    Convención:
    - selected_province: fuente de verdad de la provincia activa.
    - selected_province_widget: estado técnico del selectbox, siempre
      sincronizado desde app.py.
    """
    defaults: dict[str, object] = {
        "analysis_results": None,
        "source_label": None,
        "selected_province": None,
        "selected_province_widget": None,
        "active_section": DEFAULT_ACTIVE_SECTION,
        "active_section_widget": DEFAULT_ACTIVE_SECTION,
        "force_section": None,
        "selected_year": None,
        "selected_provinces": [],
        "metric_column": "score_riesgo",
        "top_n": 10,
        "show_top_only": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    cleanup_legacy_state_keys()


def cleanup_legacy_state_keys() -> None:
    """
    Elimina claves heredadas que pueden provocar desincronización entre
    el mapa, el selectbox y el estado persistente de Streamlit.
    """
    legacy_keys = [
        "selected_province_selectbox",
        "provincia_seleccionada",
        "provincia_focus",
        "active_province",
        "selected_points",
        "last_clicked_province",
    ]

    for key in legacy_keys:
        if key in st.session_state:
            del st.session_state[key]


def reset_selection_state() -> None:
    """
    Reinicia el estado de selección y limpia residuos heredados,
    sin tocar los resultados del análisis.
    """
    st.session_state["selected_province"] = None
    st.session_state["selected_province_widget"] = None
    st.session_state["force_section"] = None

    cleanup_legacy_state_keys()