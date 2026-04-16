# src/ui_components.py

from __future__ import annotations

import html
from typing import Mapping

import streamlit as st

from src.glossary import get_tooltip


def _escape(value: object) -> str:
    """Escapa texto para evitar problemas al renderizar HTML."""
    return html.escape("" if value is None else str(value))


def _is_valid_text(value: str | None) -> bool:
    """Valida que el texto no sea None ni vacío."""
    return value is not None and str(value).strip() != ""


def render_label_with_tooltip(label: str, help_text: str) -> str:
    """
    Construye un label con icono de ayuda usando tooltip nativo del navegador.
    """

    if not _is_valid_text(help_text):
        return f"""
        <div style="font-weight:600; font-size:1rem; color:#f8fafc; margin-bottom:6px;">
            {_escape(label)}
        </div>
        """

    safe_label = _escape(label)
    safe_help = _escape(help_text)

    return f"""
    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
        <span style="font-weight:600; font-size:1rem; color:#f8fafc;">
            {safe_label}
        </span>
        <span
            title="{safe_help}"
            style="
                display:inline-flex;
                align-items:center;
                justify-content:center;
                width:18px;
                height:18px;
                border-radius:50%;
                background:#1f2937;
                color:#93c5fd;
                font-size:12px;
                font-weight:700;
                cursor:help;
                border:1px solid #374151;
                user-select:none;
            "
        >
            i
        </span>
    </div>
    """


# =========================================================
# STATUS CARD
# =========================================================

def render_status_card(
    label: str,
    status: bool,
    tooltip: str | None = None,
    ok_bg: str = "#14532d",
    ok_fg: str = "#4ade80",
    off_bg: str = "#172554",
    off_fg: str = "#60a5fa",
    margin_bottom_px: int = 14,
) -> None:

    background = ok_bg if status else off_bg
    foreground = ok_fg if status else off_fg

    resolved_tooltip = tooltip if tooltip is not None else get_tooltip(label)

    title_html = render_label_with_tooltip(label, resolved_tooltip)

    st.markdown(
        f"""
        <div style="
            background:{background};
            color:{foreground};
            padding:18px 20px;
            border-radius:12px;
            margin-bottom:{margin_bottom_px}px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.12);
        ">
            {title_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# METRIC CARD
# =========================================================

def render_metric_card(
    label: str,
    value: object,
    tooltip: str | None = None,
    value_suffix: str = "",
    background: str = "#0f172a",
    border_color: str = "#1e293b",
    label_color: str = "#cbd5e1",
    value_color: str = "#f8fafc",
    min_height_px: int = 110,
) -> None:

    resolved_tooltip = tooltip if tooltip is not None else get_tooltip(label)

    title_html = render_label_with_tooltip(label, resolved_tooltip)

    display_value = f"{_escape(value)}{_escape(value_suffix)}"

    st.markdown(
        f"""
        <div style="
            background:{background};
            border:1px solid {border_color};
            border-radius:14px;
            padding:16px;
            min-height:{min_height_px}px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.10);
        ">
            {title_html}
            <div style="
                font-size:1.8rem;
                font-weight:700;
                color:{value_color};
                margin-top:8px;
                line-height:1.2;
            ">
                {display_value}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# INFO BOX
# =========================================================

def render_info_box(
    title: str,
    content: str,
    icon: str = "ℹ️",
    background: str = "#111827",
    border_left: str = "#22c55e",
    title_color: str = "#f8fafc",
    text_color: str = "#d1d5db",
) -> None:
    st.markdown(
        f"""
        <div style="
            background:{background};
            padding:14px 16px;
            border-radius:10px;
            border-left:4px solid {border_left};
            margin-bottom:10px;
        ">
            <div style="font-weight:700; color:{title_color}; margin-bottom:6px;">
                {_escape(icon)} {_escape(title)}
            </div>
            <div style="color:{text_color}; line-height:1.55;">
                {_escape(content)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# GLOSSARY EXPANDER
# =========================================================

def render_glossary_expander(
    glossary: Mapping[str, str],
    title: str = "📘 Ayuda y glosario DSS",
    intro: str = (
        "Conceptos clave utilizados en la lógica del sistema y en la "
        "interpretación del dashboard."
    ),
    expanded: bool = False,
) -> None:

    with st.expander(title, expanded=expanded):
        if intro:
            st.markdown(intro)

        for term, definition in glossary.items():
            st.markdown(f"**{_escape(term)}.** {_escape(definition)}")


# =========================================================
# STATUS PANEL
# =========================================================

def render_status_panel(
    title: str,
    items: list[dict],
) -> None:

    st.markdown(f"## {_escape(title)}")

    for item in items:
        render_status_card(
            label=item["label"],
            status=item["status"],
            tooltip=item.get("tooltip"),
            ok_bg=item.get("ok_bg", "#14532d"),
            ok_fg=item.get("ok_fg", "#4ade80"),
            off_bg=item.get("off_bg", "#172554"),
            off_fg=item.get("off_fg", "#60a5fa"),
        )


# =========================================================
# METRICS GRID
# =========================================================

def render_metrics_grid(
    metrics: list[dict],
    columns: int = 3,
) -> None:

    if columns < 1:
        raise ValueError("El parámetro 'columns' debe ser mayor o igual a 1.")

    cols = st.columns(columns)

    for idx, metric in enumerate(metrics):
        col = cols[idx % columns]

        with col:
            render_metric_card(
                label=metric["label"],
                value=metric["value"],
                tooltip=metric.get("tooltip"),
                value_suffix=metric.get("value_suffix", ""),
                background=metric.get("background", "#0f172a"),
                border_color=metric.get("border_color", "#1e293b"),
                label_color=metric.get("label_color", "#cbd5e1"),
                value_color=metric.get("value_color", "#f8fafc"),
            )

# =========================================================
# DSS TEXT (DESCRIPTIVE vs ANALYTIC)
# =========================================================

def inject_dss_text_styles() -> None:
    """
    Inyecta estilos para texto descriptivo y analítico DSS.
    Debe llamarse una sola vez por vista.
    """
    st.markdown(
        """
        <style>
        .dss-text-desc {
            color: rgba(255, 255, 255, 0.76);
            font-size: 0.93rem;
            line-height: 1.45;
            margin-top: -4px;
            margin-bottom: 12px;
        }

        .dss-text-analytic {
            color: #7cc4ff;
            font-size: 0.95rem;
            line-height: 1.5;
            margin-top: -2px;
            margin-bottom: 14px;
            font-weight: 500;
        }

        .dss-text-analytic strong {
            color: #a8d8ff;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_text_desc(text: str) -> None:
    """
    Renderiza texto descriptivo DSS (contexto, explicación).
    """
    if not _is_valid_text(text):
        return

    st.markdown(
        f"<div class='dss-text-desc'>{_escape(text)}</div>",
        unsafe_allow_html=True,
    )


def render_text_analytic(text: str) -> None:
    """
    Renderiza texto analítico DSS (resultados, métricas, insights).
    """
    if not _is_valid_text(text):
        return

    st.markdown(
        f"<div class='dss-text-analytic'>{text}</div>",  # NO escape (permite <strong>)
        unsafe_allow_html=True,
    )