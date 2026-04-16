from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Iterator

import pandas as pd
import streamlit as st


DEBUG_ENV_VAR = "APP_DEBUG"
LOGGER_NAME = "dss_hotspots_rd"


def is_debug_enabled() -> bool:
    """
    Determina si el modo DEBUG global está activo a partir de una variable
    de entorno. Valores válidos típicos: true, 1, yes, on.
    """
    raw_value = os.getenv(DEBUG_ENV_VAR, "false").strip().lower()
    return raw_value in {"1", "true", "yes", "on"}


def configure_logger(name: str = LOGGER_NAME) -> logging.Logger:
    """
    Configura y devuelve un logger reutilizable para la aplicación.
    Evita duplicar handlers si la función se invoca múltiples veces.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(logging.DEBUG if is_debug_enabled() else logging.INFO)
    logger.propagate = False
    return logger


def sync_debug_state() -> None:
    """
    Sincroniza banderas de debug en session_state.
    En producción fuerza todos los toggles a False.
    """
    debug_mode = is_debug_enabled()
    st.session_state["debug_mode"] = debug_mode

    defaults: dict[str, Any] = {
        "debug_mode": debug_mode,
        "debug_map_click": False,
        "debug_show_state": False,
        "debug_show_data_preview": False,
        "debug_show_pipeline_metrics": False,
        "debug_show_geo_diagnostics": False,
        "debug_show_trace_table": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if not debug_mode:
        st.session_state["debug_map_click"] = False
        st.session_state["debug_show_state"] = False
        st.session_state["debug_show_data_preview"] = False
        st.session_state["debug_show_pipeline_metrics"] = False
        st.session_state["debug_show_geo_diagnostics"] = False
        st.session_state["debug_show_trace_table"] = False


def render_debug_sidebar() -> None:
    """
    Renderiza controles globales de diagnóstico solo cuando APP_DEBUG=true.
    """
    if not is_debug_enabled():
        return

    st.header("Diagnóstico")
    st.checkbox(
        "Debug de clic del mapa",
        key="debug_map_click",
    )
    st.checkbox(
        "Mostrar estado de sesión",
        key="debug_show_state",
    )
    st.checkbox(
        "Mostrar vista previa de datos",
        key="debug_show_data_preview",
    )
    st.checkbox(
        "Mostrar métricas internas del pipeline",
        key="debug_show_pipeline_metrics",
    )
    st.checkbox(
        "Mostrar diagnóstico geográfico",
        key="debug_show_geo_diagnostics",
    )
    st.checkbox(
        "Mostrar traza técnica DSS",
        key="debug_show_trace_table",
    )


def debug_flag(flag_name: str, default: bool = False) -> bool:
    """
    Devuelve True únicamente si el modo debug global está activo y
    el flag solicitado está habilitado.
    """
    if not is_debug_enabled():
        return False
    return bool(st.session_state.get(flag_name, default))


def should_debug_map_click() -> bool:
    return debug_flag("debug_map_click")


def measure_runtime(label: str, logger: logging.Logger | None = None) -> "_RuntimeMeasure":
    """
    Helper orientado a bloque:
        with measure_runtime("pipeline", LOGGER) as m:
            result = run_pipeline(df)
        elapsed = m.elapsed
    """
    return _RuntimeMeasure(label=label, logger=logger)


class _RuntimeMeasure:
    def __init__(self, label: str, logger: logging.Logger | None = None) -> None:
        self.label = label
        self.logger = logger
        self._start: float | None = None
        self.elapsed: float = 0.0

    def __enter__(self) -> "_RuntimeMeasure":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._start is None:
            self.elapsed = 0.0
        else:
            self.elapsed = time.perf_counter() - self._start

        if self.logger is not None:
            self.logger.debug(
                "Runtime '%s' completado en %.6fs",
                self.label,
                self.elapsed,
            )


@contextmanager
def capture_runtime(
    label: str,
    logger: logging.Logger | None = None,
) -> Iterator[dict[str, Any]]:
    """
    Variante con contextmanager que expone un diccionario mutable.
    """
    payload: dict[str, Any] = {"label": label, "elapsed": None}
    start = time.perf_counter()
    try:
        yield payload
    finally:
        payload["elapsed"] = time.perf_counter() - start
        if logger is not None:
            logger.debug(
                "Runtime '%s' completado en %.6fs",
                label,
                payload["elapsed"],
            )


def build_pipeline_debug_info(
    input_df: pd.DataFrame,
    runtime_sec: float,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Construye un bloque estándar de metadatos técnicos del pipeline.
    """
    info: dict[str, Any] = {
        "pipeline_runtime_sec": round(float(runtime_sec), 6),
        "input_rows": int(len(input_df)),
        "input_columns_count": int(len(input_df.columns)),
        "input_columns": list(input_df.columns),
    }

    if extra:
        info.update(extra)

    return info


def render_pipeline_metrics(debug_info: dict[str, Any] | None) -> None:
    """
    Muestra métricas internas del pipeline.
    """
    if not debug_flag("debug_show_pipeline_metrics"):
        return

    with st.expander("Métricas internas del pipeline", expanded=False):
        if not debug_info:
            st.info("No hay métricas internas disponibles.")
            return
        st.json(debug_info)


def render_session_state_debug(extra_state: dict[str, Any] | None = None) -> None:
    """
    Muestra estado relevante de sesión para diagnóstico.
    """
    if not debug_flag("debug_show_state"):
        return

    state_snapshot = {
        "active_section": st.session_state.get("active_section"),
        "selected_province": st.session_state.get("selected_province"),
        "selected_years": st.session_state.get("selected_years"),
        "selected_provinces_filter": st.session_state.get("selected_provinces_filter"),
        "include_all_years": st.session_state.get("include_all_years"),
        "include_all_provinces": st.session_state.get("include_all_provinces"),
        "metric_column": st.session_state.get("metric_column"),
        "show_top_only": st.session_state.get("show_top_only"),
        "top_n": st.session_state.get("top_n"),
        "debug_mode": st.session_state.get("debug_mode"),
    }

    if extra_state:
        state_snapshot.update(extra_state)

    with st.expander("Estado de sesión", expanded=False):
        st.json(state_snapshot)


def render_dataframe_previews(
    frames: dict[str, pd.DataFrame],
    max_rows: int = 20,
) -> None:
    """
    Renderiza una vista previa de uno o varios DataFrames.
    Ejemplo:
        render_dataframe_previews({
            "scored_df": scored_df,
            "metricas_df": metricas_df,
        })
    """
    if not debug_flag("debug_show_data_preview"):
        return

    with st.expander("Vista previa de datos internos", expanded=False):
        if not frames:
            st.info("No hay DataFrames para mostrar.")
            return

        for name, df in frames.items():
            st.markdown(f"**{name}**")
            if isinstance(df, pd.DataFrame) and not df.empty:
                st.dataframe(df.head(max_rows), width="stretch")
            elif isinstance(df, pd.DataFrame):
                st.info(f"{name} está vacío.")
            else:
                st.warning(f"{name} no es un DataFrame válido.")


def render_geo_debug_panel(
    coverage: float,
    unmatched_count: int,
    unmatched_provinces: list[str] | None,
    matched_df: pd.DataFrame | None,
    metric_column: str | None = None,
) -> None:
    """
    Panel técnico para diagnóstico de matching geográfico.
    """
    if not debug_flag("debug_show_geo_diagnostics"):
        return

    unmatched_provinces = unmatched_provinces or []

    with st.expander("Diagnóstico geográfico", expanded=False):
        st.write("Cobertura:", coverage)
        st.write("Unmatched count:", unmatched_count)
        st.write("Unmatched provinces:", unmatched_provinces)

        if matched_df is None:
            st.info("No hay matched_df disponible.")
            return

        debug_cols = [
            col
            for col in [
                "provincia",
                "provincia_canon",
                "geo_match_name",
                metric_column,
            ]
            if col and col in matched_df.columns
        ]

        if debug_cols:
            st.dataframe(matched_df[debug_cols], width="stretch")
        else:
            st.dataframe(matched_df.head(20), width="stretch")


def render_trace_table(
    filtered_ranking: pd.DataFrame,
    trace_columns: list[str] | None = None,
) -> None:
    """
    Muestra una traza técnica del DSS separada de la trazabilidad funcional
    presentada al usuario final.
    """
    if not debug_flag("debug_show_trace_table"):
        return

    if trace_columns is None:
        trace_columns = [
            "provincia",
            "year",
            "score_riesgo",
            "pred_fallecidos_next",
            "delta_abs",
            "delta_pct",
            "categoria",
            "ranking_posicion",
            "regla_aplicada",
            "justificacion_regla",
        ]

    available_cols = [col for col in trace_columns if col in filtered_ranking.columns]

    with st.expander("Traza técnica DSS", expanded=False):
        if filtered_ranking.empty:
            st.info("No hay datos para la traza técnica.")
            return

        if available_cols:
            st.dataframe(filtered_ranking[available_cols], width="stretch")
        else:
            st.dataframe(filtered_ranking.head(20), width="stretch")


def log_debug(
    logger: logging.Logger,
    message: str,
    *args: Any,
) -> None:
    """
    Registra mensajes DEBUG solo cuando el modo global está activo.
    """
    if is_debug_enabled():
        logger.debug(message, *args)