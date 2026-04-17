from __future__ import annotations

import html
from typing import Callable

import pandas as pd
import streamlit as st

from src.glossary import get_tooltip
from ui.ui_theme import get_category_theme


def _escape(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _help_badge(text: str) -> str:
    if text is None or str(text).strip() == "":
        return ""

    safe_text = html.escape(str(text), quote=True)

    return (
        f'<span title="{safe_text}" '
        'style="display:inline-flex;align-items:center;justify-content:center;'
        'width:16px;height:16px;border-radius:50%;background:#1f2937;'
        'color:#93c5fd;font-size:11px;font-weight:700;cursor:help;'
        'border:1px solid #374151;user-select:none;margin-left:6px;'
        'vertical-align:middle;">i</span>'
    )


def _inject_topk_styles() -> None:
    st.markdown(
        """
        <style>
        .topk-panel-card {
            border-radius: 16px;
            padding: 14px 14px 12px 14px;
            min-height: 172px;
            transition:
                transform 0.18s ease,
                box-shadow 0.18s ease,
                border-color 0.18s ease,
                background-color 0.18s ease;
        }

        .topk-panel-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.12);
        }

        .topk-panel-card--active {
            box-shadow:
                0 0 0 2px rgba(59, 130, 246, 0.16),
                0 12px 24px rgba(15, 23, 42, 0.12);
            transform: translateY(-1px);
        }

        .topk-panel-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 8px;
            margin-bottom: 0.65rem;
        }

        .topk-rank-chip {
            display: inline-block;
            padding: 4px 9px;
            border-radius: 999px;
            background: rgba(15, 23, 42, 0.36);
            color: #e2e8f0;
            font-size: 0.76rem;
            font-weight: 800;
            border: 1px solid rgba(148, 163, 184, 0.20);
        }

        .topk-badge {
            display: inline-block;
            padding: 4px 9px;
            border-radius: 999px;
            font-size: 0.76rem;
            font-weight: 800;
            white-space: nowrap;
        }

        .topk-province {
            font-weight: 800;
            font-size: 1.02rem;
            line-height: 1.2;
            color: #f8fafc;
            margin-bottom: 0.4rem;
        }

        .topk-focus-pill {
            display: inline-block;
            margin-top: 0.35rem;
            padding: 3px 8px;
            border-radius: 999px;
            background: rgba(59, 130, 246, 0.14);
            color: #bfdbfe;
            font-size: 0.78rem;
            font-weight: 700;
        }

        .topk-metrics-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-top: 0.8rem;
        }

        .topk-metric-box {
            border-radius: 12px;
            padding: 8px 10px;
            background: rgba(15, 23, 42, 0.20);
            border: 1px solid rgba(148, 163, 184, 0.16);
        }

        .topk-metric-label {
            font-size: 0.75rem;
            color: #94a3b8;
            margin-bottom: 0.18rem;
            font-weight: 700;
        }

        .topk-metric-value {
            font-size: 0.94rem;
            color: #f8fafc;
            font-weight: 800;
        }

        .topk-detail {
            font-size: 0.9rem;
            line-height: 1.55;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _format_float(value: float, decimals: int = 2) -> str:
    return f"{value:.{decimals}f}"


def _format_signed(value: float, decimals: int = 2) -> str:
    return f"{value:+.{decimals}f}"


def _panel_card_html(
    provincia: str,
    categoria: str,
    score: float,
    pred_next: float,
    delta_abs: float,
    posicion: int,
    is_active: bool,
    palette: dict[str, str],
) -> str:
    position_help = _help_badge(get_tooltip("Posicion"))
    category_help = _help_badge(get_tooltip("Categoria DSS"))
    score_help = _help_badge(get_tooltip("Score actual"))
    pred_help = _help_badge(get_tooltip("Prediccion proxima"))
    delta_help = _help_badge(get_tooltip("Delta abs."))
    focus_help = _help_badge(get_tooltip("Provincia en foco"))

    active_class = " topk-panel-card--active" if is_active else ""

    focus_text = (
        f'<div class="topk-focus-pill">Provincia en foco {focus_help}</div>'
        if is_active
        else ""
    )

    return (
        f'<div class="topk-panel-card{active_class}" '
        f'style="background:{palette["bg"]};border:1px solid {palette["border"]};">'
        '<div class="topk-panel-top">'
        f'<div class="topk-rank-chip">#{posicion}{position_help}</div>'
        f'<div class="topk-badge" '
        f'style="background:{palette["badge_bg"]};color:{palette["badge_text"]};">'
        f'{_escape(palette["label"])}{category_help}</div>'
        "</div>"
        f'<div class="topk-province">{_escape(provincia)}</div>'
        f"{focus_text}"
        '<div class="topk-metrics-grid">'
        '<div class="topk-metric-box">'
        f'<div class="topk-metric-label">Score{score_help}</div>'
        f'<div class="topk-metric-value">{_format_float(score, 3)}</div>'
        "</div>"
        '<div class="topk-metric-box">'
        f'<div class="topk-metric-label">Prediccion{pred_help}</div>'
        f'<div class="topk-metric-value">{_format_float(pred_next, 2)}</div>'
        "</div>"
        '<div class="topk-metric-box" style="grid-column: 1 / span 2;">'
        f'<div class="topk-metric-label">Delta abs.{delta_help}</div>'
        f'<div class="topk-metric-value">{_format_signed(delta_abs, 2)}</div>'
        "</div>"
        "</div>"
        "</div>"
    )


def _detail_lines_html(
    rule_text: str,
    justification_text: str,
) -> str:
    trace_help = _help_badge(get_tooltip("Trazabilidad de la decision"))

    lines: list[str] = []

    if rule_text:
        lines.append(f"<b>Regla:</b> {_escape(rule_text)}{trace_help}")

    if justification_text:
        lines.append(f"<b>Justificacion:</b> {_escape(justification_text)}{trace_help}")

    if not lines:
        lines.append("No hay detalle adicional disponible para esta provincia.")

    return f'<div class="topk-detail">{"<br>".join(lines)}</div>'


def _infer_columns(num_cards: int) -> int:
    if num_cards <= 1:
        return 1
    if num_cards <= 4:
        return 2
    return 3


def render_topk_preview(
    filtered_ranking: pd.DataFrame,
    top_n: int,
    set_selected_province_fn: Callable[[str | None], bool],
) -> bool:
    _inject_topk_styles()

    st.markdown("### Top-K priorizado")
    st.caption(get_tooltip("Top-K"))

    if filtered_ranking is None or filtered_ranking.empty:
        st.info("No hay provincias disponibles para mostrar en el Top-K.")
        return False

    preview_df = filtered_ranking.head(min(top_n, len(filtered_ranking))).copy()

    if preview_df.empty:
        st.info("No hay provincias disponibles para mostrar en el Top-K.")
        return False

    current_focus = str(st.session_state.get("selected_province", "")).strip()
    clicked_any = False

    num_cards = len(preview_df)
    num_cols = _infer_columns(num_cards)

    rows = [
        preview_df.iloc[i:i + num_cols]
        for i in range(0, num_cards, num_cols)
    ]

    for row_idx, row_df in enumerate(rows):
        cols = st.columns(num_cols)

        for col_idx, (col, (_, row)) in enumerate(zip(cols, row_df.iterrows())):
            provincia = str(row.get("provincia", "N/D")).strip()
            categoria = str(row.get("categoria", "N/D")).strip() or "N/D"
            score = float(pd.to_numeric(row.get("score_riesgo", 0.0), errors="coerce"))
            pred_next = float(
                pd.to_numeric(row.get("pred_fallecidos_next", 0.0), errors="coerce")
            )
            delta_abs = float(pd.to_numeric(row.get("delta_abs", 0.0), errors="coerce"))
            posicion = int(pd.to_numeric(row.get("ranking_posicion", 0), errors="coerce"))
            rule_text = str(row.get("regla_aplicada", "")).strip()
            justification_text = str(row.get("justificacion_regla", "")).strip()

            is_active = current_focus == provincia
            palette = get_category_theme(categoria)

            with col:
                st.markdown(
                    _panel_card_html(
                        provincia=provincia,
                        categoria=categoria,
                        score=score,
                        pred_next=pred_next,
                        delta_abs=delta_abs,
                        posicion=posicion,
                        is_active=is_active,
                        palette=palette,
                    ),
                    unsafe_allow_html=True,
                )

                with st.expander("Ver trazabilidad", expanded=False):
                    st.markdown(
                        _detail_lines_html(
                            rule_text=rule_text,
                            justification_text=justification_text,
                        ),
                        unsafe_allow_html=True,
                    )

                button_label = "Provincia en foco" if is_active else f"Enfocar {provincia}"

                clicked = st.button(
                    button_label,
                    key=f"topk_btn_{row_idx}_{col_idx}_{provincia}",
                    width="stretch",
                    disabled=is_active,
                )

                if clicked and set_selected_province_fn(provincia):
                    clicked_any = True

    return clicked_any