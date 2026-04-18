from __future__ import annotations

from pathlib import Path

PROJECT_NAME = "DSS_Hotspots_RD"
AUTHOR = "Edwin José Nolasco"


def _load_version(default: str = "v1.2.0") -> str:
    """
    Carga la versión desde el archivo VERSION en la raíz del proyecto.
    Fallback al valor por defecto si no existe o falla.
    """
    try:
        project_root = Path(__file__).resolve().parents[1]
        version_file = project_root / "VERSION"

        if version_file.exists():
            value = version_file.read_text(encoding="utf-8").strip()
            if value:
                return value

    except Exception:
        pass

    return default


VERSION = _load_version()