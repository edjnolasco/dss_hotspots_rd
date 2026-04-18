from __future__ import annotations

from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def ensure_reports_dirs(project_root: Path) -> tuple[Path, Path]:
    """
    Garantiza la existencia de las carpetas de salida para tablas y figuras.
    """
    reports_dir = project_root / "reports"
    figures_dir = reports_dir / "figures"
    tables_dir = reports_dir / "tables"

    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    return figures_dir, tables_dir


def export_benchmark_table(
    benchmark_df: pd.DataFrame,
    project_root: Path,
    filename_base: str = "benchmark_modelos",
) -> dict[str, str]:
    """
    Exporta la tabla benchmark a CSV y XLSX.
    """
    _figures_dir, tables_dir = ensure_reports_dirs(project_root)

    csv_path = tables_dir / f"{filename_base}.csv"
    xlsx_path = tables_dir / f"{filename_base}.xlsx"

    benchmark_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    try:
        benchmark_df.to_excel(xlsx_path, index=False)
    except Exception:
        xlsx_path = None

    return {
        "csv": str(csv_path),
        "xlsx": str(xlsx_path) if xlsx_path else "",
    }


def build_benchmark_figure(
    benchmark_df: pd.DataFrame,
) -> plt.Figure | None:
    """
    Construye una figura comparativa MAE vs RMSE.
    Retorna None si no hay datos suficientes.
    """
    plot_df = benchmark_df.dropna(subset=["mae", "rmse"]).copy()

    if plot_df.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))

    width = 0.35
    x = list(range(len(plot_df)))

    ax.bar(
        [i - width / 2 for i in x],
        plot_df["mae"],
        width=width,
        label="MAE",
    )
    ax.bar(
        [i + width / 2 for i in x],
        plot_df["rmse"],
        width=width,
        label="RMSE",
    )

    ax.set_xticks(x)
    ax.set_xticklabels(plot_df["model_label"], rotation=25, ha="right")
    ax.set_ylabel("Error")
    ax.set_title("Comparación de modelos predictivos (MAE y RMSE)")
    ax.legend()
    fig.tight_layout()

    return fig


def export_benchmark_figure(
    benchmark_df: pd.DataFrame,
    project_root: Path,
    filename_base: str = "benchmark_modelos",
) -> dict[str, str]:
    """
    Exporta la figura benchmark a PNG.
    """
    figures_dir, _tables_dir = ensure_reports_dirs(project_root)

    fig = build_benchmark_figure(benchmark_df)
    if fig is None:
        return {"png": ""}

    png_path = figures_dir / f"{filename_base}.png"
    fig.savefig(png_path, format="png", bbox_inches="tight", dpi=200)
    plt.close(fig)

    return {"png": str(png_path)}


def benchmark_figure_bytes(
    benchmark_df: pd.DataFrame,
) -> BytesIO | None:
    """
    Devuelve la figura en memoria para descarga directa desde Streamlit.
    """
    fig = build_benchmark_figure(benchmark_df)
    if fig is None:
        return None

    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=200)
    buffer.seek(0)
    plt.close(fig)
    return buffer


def export_benchmark_artifacts(
    benchmark_df: pd.DataFrame,
    project_root: Path,
    filename_base: str = "benchmark_modelos",
) -> dict[str, str]:
    """
    Exporta todos los artefactos del benchmark.
    """
    paths: dict[str, str] = {}
    paths.update(export_benchmark_table(benchmark_df, project_root, filename_base))
    paths.update(export_benchmark_figure(benchmark_df, project_root, filename_base))
    return paths