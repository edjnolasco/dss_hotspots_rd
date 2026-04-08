from __future__ import annotations


PROVINCE_ALIASES = {
    "azua": "Azua",
    "bahoruco": "Bahoruco",
    "barahona": "Barahona",
    "dajabon": "Dajabón",
    "dajabón": "Dajabón",
    "distrito nacional": "Distrito Nacional",
    "duarte": "Duarte",
    "el seibo": "El Seibo",
    "elias pina": "Elías Piña",
    "elías piña": "Elías Piña",
    "espaillat": "Espaillat",
    "hato mayor": "Hato Mayor",
    "hermanas mirabal": "Hermanas Mirabal",
    "independencia": "Independencia",
    "la altagracia": "La Altagracia",
    "la romana": "La Romana",
    "la vega": "La Vega",
    "maria trinidad sanchez": "María Trinidad Sánchez",
    "maría trinidad sánchez": "María Trinidad Sánchez",
    "monsenor nouel": "Monseñor Nouel",
    "monseñor nouel": "Monseñor Nouel",
    "monte cristi": "Monte Cristi",
    "monte plata": "Monte Plata",
    "pedernales": "Pedernales",
    "peravia": "Peravia",
    "puerto plata": "Puerto Plata",
    "samana": "Samaná",
    "samaná": "Samaná",
    "san cristobal": "San Cristóbal",
    "san cristóbal": "San Cristóbal",
    "san jose de ocoa": "San José de Ocoa",
    "san josé de ocoa": "San José de Ocoa",
    "san juan": "San Juan",
    "san pedro de macoris": "San Pedro de Macorís",
    "san pedro de macorís": "San Pedro de Macorís",
    "sanchez ramirez": "Sánchez Ramírez",
    "sánchez ramírez": "Sánchez Ramírez",
    "santiago": "Santiago",
    "santiago rodriguez": "Santiago Rodríguez",
    "santiago rodríguez": "Santiago Rodríguez",
    "santo domingo": "Santo Domingo",
    "valverde": "Valverde",
}


def normalize_text(s: str) -> str:
    return (
        str(s).strip().lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )


def canonical_province(name: str) -> str:
    return PROVINCE_ALIASES.get(normalize_text(name), str(name).strip())


def province_key(name: str) -> str:
    """
    Clave técnica única para matching entre dataset y GeoJSON.
    """
    return normalize_text(canonical_province(name)).replace(" ", "_")
