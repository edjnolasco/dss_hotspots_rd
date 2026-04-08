from pathlib import Path
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

INPUT_FILE = "Fallecimientos según Provincias, DIGESETT, 2016 - 2026.csv"
OUTPUT_FILE = "data/fallecimientos_provincias.csv"


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def convert_digesett_csv(input_path: str, output_path: str):
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {input_path}")

    print("Leyendo archivo original...")

    # Leer CSV con separador correcto
    df = pd.read_csv(
        input_path,
        sep=";",
        encoding="latin1"
    )

    print("Columnas originales:", list(df.columns))

    # ------------------------------------------------------------
    # Normalizar nombres de columnas
    # ------------------------------------------------------------
    df.columns = [c.strip().lower() for c in df.columns]

    column_map = {}

    for col in df.columns:
        if "prov" in col:
            column_map[col] = "provincia"
        elif "año" in col or "ano" in col or "year" in col:
            column_map[col] = "year"
        elif "falle" in col or "cantidad" in col or "valor" in col:
            column_map[col] = "fallecidos"

    df = df.rename(columns=column_map)

    required_cols = ["provincia", "year", "fallecidos"]

    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Falta la columna requerida: {col}")

    # ------------------------------------------------------------
    # Limpieza de datos
    # ------------------------------------------------------------
    df = df[required_cols].copy()

    df["provincia"] = df["provincia"].astype(str).str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["fallecidos"] = pd.to_numeric(df["fallecidos"], errors="coerce")

    df = df.dropna().copy()

    df["year"] = df["year"].astype(int)
    df["fallecidos"] = df["fallecidos"].astype(int)

    df = df.sort_values(["year", "provincia"]).reset_index(drop=True)

    print("Datos limpios:", df.shape)

    # ------------------------------------------------------------
    # Guardar CSV limpio con comas
    # ------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8"
    )

    print(f"Archivo convertido guardado en: {output_path}")


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    convert_digesett_csv(INPUT_FILE, OUTPUT_FILE)
