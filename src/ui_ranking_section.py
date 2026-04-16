from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ui_sections import render_ranking_tab


def render_ranking_section(
    filtered_ranking: pd.DataFrame,
    top_n: int,
    show_dss_trace: bool,
) -> None:
    """
    Encapsula la vista de ranking con su encabezado contextual.
    """
    if show_dss_trace:
        st.markdown("### Lectura operativa del ranking")
        st.caption(
            "El ranking no representa solo una ordenacion visual. "
            "Expresa la salida final del DSS despues de combinar el score predictivo "
            "con la logica de reglas explicitas."
        )

    render_ranking_tab(filtered_ranking=filtered_ranking, top_n=top_n)