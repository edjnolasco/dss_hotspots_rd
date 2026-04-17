from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import streamlit as st


# ============================================================
# Claves oficiales de estado
# ============================================================

VIEW_MAP = "map"
VIEW_RANKING = "ranking"
VIEW_SUMMARY = "summary"
VIEW_ABOUT = "about"
VIEW_HELP = "help"

VALID_VIEWS = {
    VIEW_MAP,
    VIEW_RANKING,
    VIEW_SUMMARY,
    VIEW_ABOUT,
    VIEW_HELP,
}


@dataclass(frozen=True)
class StateKeys:
    selected_view: str = "selected_view"
    selected_years: str = "selected_years"
    selected_metric: str = "selected_metric"
    normalization_mode: str = "normalization_mode"
    selected_provinces: str = "selected_provinces"
    selected_top_k: str = "selected_top_k"
    presentation_mode: str = "presentation_mode"
    glossary_enabled: str = "glossary_enabled"
    show_filters: str = "show_filters"
    show_executive_summary: str = "show_executive_summary"
    show_export_panel: str = "show_export_panel"
    last_summary_text: str = "last_summary_text"
    last_map_insight: str = "last_map_insight"
    last_ranking_insight: str = "last_ranking_insight"
    last_export_metadata: str = "last_export_metadata"
    active_analysis_context: str = "active_analysis_context"
    ui_initialized: str = "_ui_initialized"


STATE_KEYS = StateKeys()


# ============================================================
# Valores por defecto
# ============================================================

DEFAULTS: dict[str, Any] = {
    STATE_KEYS.selected_view: VIEW_MAP,
    STATE_KEYS.selected_years: [],
    STATE_KEYS.selected_metric: "fallecidos",
    STATE_KEYS.normalization_mode: "raw",
    STATE_KEYS.selected_provinces: [],
    STATE_KEYS.selected_top_k: 10,
    STATE_KEYS.presentation_mode: False,
    STATE_KEYS.glossary_enabled: True,
    STATE_KEYS.show_filters: True,
    STATE_KEYS.show_executive_summary: True,
    STATE_KEYS.show_export_panel: False,
    STATE_KEYS.last_summary_text: "",
    STATE_KEYS.last_map_insight: "",
    STATE_KEYS.last_ranking_insight: "",
    STATE_KEYS.last_export_metadata: {},
    STATE_KEYS.active_analysis_context: {},
    STATE_KEYS.ui_initialized: False,
}


# ============================================================
# Inicialización
# ============================================================

def init_view_state(overrides: dict[str, Any] | None = None) -> None:
    """
    Inicializa el estado global de la app una sola vez.
    Permite overrides para adaptar defaults por entorno o vista.
    """
    state_defaults = dict(DEFAULTS)
    if overrides:
        state_defaults.update(overrides)

    for key, value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    st.session_state[STATE_KEYS.ui_initialized] = True


def reset_view_state(preserve_keys: Iterable[str] | None = None) -> None:
    """
    Reinicia el estado a los valores por defecto.
    Puedes preservar claves específicas si hay contexto que no quieres perder.
    """
    preserve = set(preserve_keys or [])
    preserved_values = {
        key: st.session_state[key]
        for key in preserve
        if key in st.session_state
    }

    for key in list(st.session_state.keys()):
        if key in preserve:
            continue
        if key in DEFAULTS:
            del st.session_state[key]

    init_view_state()

    for key, value in preserved_values.items():
        st.session_state[key] = value


def ensure_initialized() -> None:
    """
    Garantiza que el estado haya sido inicializado antes de cualquier acceso.
    """
    if not st.session_state.get(STATE_KEYS.ui_initialized, False):
        init_view_state()


# ============================================================
# Helpers genéricos
# ============================================================

def get_state(key: str, default: Any = None) -> Any:
    ensure_initialized()
    return st.session_state.get(key, default)


def set_state(key: str, value: Any) -> None:
    ensure_initialized()
    st.session_state[key] = value


def update_state(values: dict[str, Any]) -> None:
    ensure_initialized()
    for key, value in values.items():
        st.session_state[key] = value


def clear_state_key(key: str) -> None:
    ensure_initialized()
    if key in st.session_state:
        del st.session_state[key]


# ============================================================
# Vista activa
# ============================================================

def get_selected_view() -> str:
    ensure_initialized()
    value = st.session_state.get(STATE_KEYS.selected_view, VIEW_MAP)
    return value if value in VALID_VIEWS else VIEW_MAP


def set_selected_view(view: str) -> None:
    ensure_initialized()
    if view not in VALID_VIEWS:
        raise ValueError(f"Vista no válida: {view}")
    st.session_state[STATE_KEYS.selected_view] = view


def is_map_view() -> bool:
    return get_selected_view() == VIEW_MAP


def is_ranking_view() -> bool:
    return get_selected_view() == VIEW_RANKING


def is_summary_view() -> bool:
    return get_selected_view() == VIEW_SUMMARY


# ============================================================
# Filtros analíticos
# ============================================================

def get_selected_years() -> list[int]:
    ensure_initialized()
    years = st.session_state.get(STATE_KEYS.selected_years, [])
    return list(years) if years else []


def set_selected_years(years: Iterable[int]) -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.selected_years] = sorted({int(y) for y in years})


def get_selected_metric() -> str:
    ensure_initialized()
    return str(st.session_state.get(STATE_KEYS.selected_metric, "fallecidos"))


def set_selected_metric(metric: str) -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.selected_metric] = str(metric)


def get_normalization_mode() -> str:
    ensure_initialized()
    return str(st.session_state.get(STATE_KEYS.normalization_mode, "raw"))


def set_normalization_mode(mode: str) -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.normalization_mode] = str(mode)


def get_selected_provinces() -> list[str]:
    ensure_initialized()
    provinces = st.session_state.get(STATE_KEYS.selected_provinces, [])
    return list(provinces) if provinces else []


def set_selected_provinces(provinces: Iterable[str]) -> None:
    ensure_initialized()
    cleaned = [str(p).strip() for p in provinces if str(p).strip()]
    st.session_state[STATE_KEYS.selected_provinces] = cleaned


def get_selected_top_k() -> int:
    ensure_initialized()
    value = st.session_state.get(STATE_KEYS.selected_top_k, 10)
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 10


def set_selected_top_k(value: int) -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.selected_top_k] = max(1, int(value))


# ============================================================
# Modo presentación / UX
# ============================================================

def is_presentation_mode() -> bool:
    ensure_initialized()
    return bool(st.session_state.get(STATE_KEYS.presentation_mode, False))


def set_presentation_mode(enabled: bool) -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.presentation_mode] = bool(enabled)

    # Comportamiento sugerido para un modo presentación serio:
    # menos ruido visual, más foco narrativo.
    if enabled:
        st.session_state[STATE_KEYS.show_filters] = False
        st.session_state[STATE_KEYS.show_export_panel] = False
        st.session_state[STATE_KEYS.show_executive_summary] = True


def toggle_presentation_mode() -> bool:
    new_value = not is_presentation_mode()
    set_presentation_mode(new_value)
    return new_value


def is_glossary_enabled() -> bool:
    ensure_initialized()
    return bool(st.session_state.get(STATE_KEYS.glossary_enabled, True))


def set_glossary_enabled(enabled: bool) -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.glossary_enabled] = bool(enabled)


def should_show_filters() -> bool:
    ensure_initialized()
    return bool(st.session_state.get(STATE_KEYS.show_filters, True))


def set_show_filters(visible: bool) -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.show_filters] = bool(visible)


def should_show_executive_summary() -> bool:
    ensure_initialized()
    return bool(st.session_state.get(STATE_KEYS.show_executive_summary, True))


def set_show_executive_summary(visible: bool) -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.show_executive_summary] = bool(visible)


def should_show_export_panel() -> bool:
    ensure_initialized()
    return bool(st.session_state.get(STATE_KEYS.show_export_panel, False))


def set_show_export_panel(visible: bool) -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.show_export_panel] = bool(visible)


# ============================================================
# Narrativa / insights / caché ligera de UI
# ============================================================

def get_last_summary_text() -> str:
    ensure_initialized()
    return str(st.session_state.get(STATE_KEYS.last_summary_text, ""))


def set_last_summary_text(text: str) -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.last_summary_text] = str(text or "")


def get_last_map_insight() -> str:
    ensure_initialized()
    return str(st.session_state.get(STATE_KEYS.last_map_insight, ""))


def set_last_map_insight(text: str) -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.last_map_insight] = str(text or "")


def get_last_ranking_insight() -> str:
    ensure_initialized()
    return str(st.session_state.get(STATE_KEYS.last_ranking_insight, ""))


def set_last_ranking_insight(text: str) -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.last_ranking_insight] = str(text or "")


def clear_cached_narratives() -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.last_summary_text] = ""
    st.session_state[STATE_KEYS.last_map_insight] = ""
    st.session_state[STATE_KEYS.last_ranking_insight] = ""


# ============================================================
# Contexto activo del análisis
# ============================================================

def get_active_analysis_context() -> dict[str, Any]:
    ensure_initialized()
    context = st.session_state.get(STATE_KEYS.active_analysis_context, {})
    return dict(context) if isinstance(context, dict) else {}


def set_active_analysis_context(context: dict[str, Any]) -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.active_analysis_context] = dict(context or {})


def build_active_analysis_context(
    *,
    available_years: Iterable[int] | None = None,
    available_metrics: Iterable[str] | None = None,
) -> dict[str, Any]:
    """
    Construye un snapshot utilizable por narrative.py y exporter.py.
    """
    ensure_initialized()

    years = get_selected_years()
    metric = get_selected_metric()
    normalization_mode = get_normalization_mode()
    provinces = get_selected_provinces()
    top_k = get_selected_top_k()

    context = {
        "selected_view": get_selected_view(),
        "selected_years": years,
        "year_range": [min(years), max(years)] if years else [],
        "selected_metric": metric,
        "normalization_mode": normalization_mode,
        "selected_provinces": provinces,
        "selected_top_k": top_k,
        "presentation_mode": is_presentation_mode(),
        "available_years": list(available_years) if available_years else [],
        "available_metrics": list(available_metrics) if available_metrics else [],
    }

    set_active_analysis_context(context)
    return context


# ============================================================
# Exportación
# ============================================================

def get_last_export_metadata() -> dict[str, Any]:
    ensure_initialized()
    metadata = st.session_state.get(STATE_KEYS.last_export_metadata, {})
    return dict(metadata) if isinstance(metadata, dict) else {}


def set_last_export_metadata(metadata: dict[str, Any]) -> None:
    ensure_initialized()
    st.session_state[STATE_KEYS.last_export_metadata] = dict(metadata or {})


# ============================================================
# Utilidades DSS
# ============================================================

def is_single_year_mode() -> bool:
    years = get_selected_years()
    return len(years) == 1


def is_multi_year_mode() -> bool:
    years = get_selected_years()
    return len(years) > 1


def has_active_filters() -> bool:
    years = get_selected_years()
    provinces = get_selected_provinces()
    metric = get_selected_metric()
    normalization_mode = get_normalization_mode()
    top_k = get_selected_top_k()

    return bool(
        years
        or provinces
        or metric != "fallecidos"
        or normalization_mode != "raw"
        or top_k != 10
    )


def get_filter_summary() -> dict[str, Any]:
    """
    Resumen compacto del estado analítico actual.
    Útil para cabeceras, chips de filtros, exporter.py y narrative.py.
    """
    years = get_selected_years()

    return {
        "view": get_selected_view(),
        "years": years,
        "year_range": [min(years), max(years)] if years else [],
        "metric": get_selected_metric(),
        "normalization_mode": get_normalization_mode(),
        "provinces": get_selected_provinces(),
        "top_k": get_selected_top_k(),
        "presentation_mode": is_presentation_mode(),
        "has_active_filters": has_active_filters(),
    }