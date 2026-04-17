from __future__ import annotations


# =========================================================
# PALETAS VISUALES POR CATEGORÍA DSS
# =========================================================

CATEGORY_THEME: dict[str, dict[str, str]] = {
    "Alta prioridad": {
        "bg": "rgba(231, 76, 60, 0.12)",
        "border": "#e74c3c",
        "badge_bg": "rgba(231, 76, 60, 0.18)",
        "badge_text": "#fecaca",
        "label": "🔴 Alta",
    },
    "Vigilancia preventiva": {
        "bg": "rgba(243, 156, 18, 0.14)",
        "border": "#f39c12",
        "badge_bg": "rgba(243, 156, 18, 0.20)",
        "badge_text": "#fde68a",
        "label": "🟡 Media",
    },
    "Seguimiento rutinario": {
        "bg": "rgba(46, 204, 113, 0.12)",
        "border": "#2ecc71",
        "badge_bg": "rgba(46, 204, 113, 0.18)",
        "badge_text": "#bbf7d0",
        "label": "🟢 Baja",
    },
    "N/D": {
        "bg": "rgba(189, 195, 199, 0.16)",
        "border": "#bdc3c7",
        "badge_bg": "rgba(189, 195, 199, 0.22)",
        "badge_text": "#e5e7eb",
        "label": "⚪ N/D",
    },
}


# =========================================================
# FUNCIONES DE ACCESO
# =========================================================

def get_category_theme(categoria: str | None) -> dict[str, str]:
    """
    Devuelve la paleta visual asociada a una categoría DSS.
    Siempre retorna un diccionario válido (fallback = N/D).
    """
    if categoria is None:
        return CATEGORY_THEME["N/D"]

    return CATEGORY_THEME.get(str(categoria).strip(), CATEGORY_THEME["N/D"])


def get_category_label(categoria: str | None) -> str:
    """
    Devuelve la etiqueta corta (ej: 🔴 Alta).
    """
    return get_category_theme(categoria)["label"]