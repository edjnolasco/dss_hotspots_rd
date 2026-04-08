from __future__ import annotations

from pathlib import Path
import argparse
import sys

import pandas as pd


# ============================================================
# CONFIGURACIÓN BASE
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "data" / "digesett_provincias_raw.csv"
DEFAULT_OUTPUT = ROOT / "data" / "fallecimientos_provincias.csv"


# ============================================================
# UTILIDADES
# ============================================================

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    column_map = {}

    for col in df.columns:
        if "prov" in col:
            column_map[col] = "provincia"
        elif "año" in col or "ano" in col or "year" in col:
            column_map[col] = "year"
        elif "falle" in col or "cantidad" in col or "valor" in col:
            column_map[col] = "fallecidos"

    return df.rename(columns=column_map)


def read_digesett_file(input_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {input_path}")

    suffix = input_path.suffix.lower()

    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(input_path)

    encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
    separators = [";", ",", "\t"]

    last_error = None

    for encoding in encodings:
        for sep in separators:
            try:
                df = pd.read_csv(input_path, sep=sep, encoding=encoding)
                if df.shape[1] > 1:
                    return df
            except Exception as e:
                last_error = e

    raise ValueError(f"No se pudo leer el archivo con los formatos esperados: {last_error}")


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df)

    required_cols = ["provincia", "year", "fallecidos"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas después de normalizar: {missing}")

    out = df[required_cols].copy()

    out["provincia"] = out["provincia"].astype(str).str.strip()
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["fallecidos"] = pd.to_numeric(out["fallecidos"], errors="coerce")

    out = out.dropna(subset=["provincia", "year", "fallecidos"]).copy()

    out["year"] = out["year"].astype(int)
    out["fallecidos"] = out["fallecidos"].astype(int)

    out = out.sort_values(["year", "provincia"]).reset_index(drop=True)

    return out


def convert_digesett_csv(input_path: Path, output_path: Path) -> Path:
    print(f"[INFO] Leyendo archivo de entrada: {input_path}")

    raw_df = read_digesett_file(input_path)
    print(f"[INFO] Columnas originales detectadas: {list(raw_df.columns)}")
    print(f"[INFO] Forma original: {raw_df.shape}")

    clean_df = clean_dataset(raw_df)
    print(f"[INFO] Forma limpia: {clean_df.shape}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(output_path, index=False, encoding="utf-8")

    print(f"[OK] Archivo convertido guardado en: {output_path}")
    return output_path


# ============================================================
# CLI
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convierte un archivo DIGESETT de provincias a un CSV limpio y compatible con el DSS."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Ruta del archivo de entrada. Por defecto: {DEFAULT_INPUT}",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Ruta del archivo de salida. Por defecto: {DEFAULT_OUTPUT}",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        convert_digesett_csv(args.input, args.output)
        return 0
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
