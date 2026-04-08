from __future__ import annotations


PROVINCE_ALIASES = {
    "azua": "Azua",
    "bahoruco": "Bahoruco",
    "barahona": "Barahona",
    "dajabon": "Dajabón",
    "dajabón": "Dajabón",
    "distrito nacional": "Distrito Nacional",
    "distritonacional": "Distrito Nacional",
    "duarte": "Duarte",

    "el seibo": "El Seibo",
    "elseibo": "El Seibo",

    "elias pina": "Elías Piña",
    "eliaspina": "Elías Piña",
    "elias piña": "Elías Piña",
    "eliaspiña": "Elías Piña",
    "elías piña": "Elías Piña",
    "elíaspiña": "Elías Piña",

    "espaillat": "Espaillat",
    "hato mayor": "Hato Mayor",
    "hatomayor": "Hato Mayor",

    "hermanas mirabal": "Hermanas Mirabal",
    "hermanasmirabal": "Hermanas Mirabal",

    "independencia": "Independencia",
    "la altagracia": "La Altagracia",
    "laaltagracia": "La Altagracia",
    "la romana": "La Romana",
    "laromana": "La Romana",
    "la vega": "La Vega",
    "lavega": "La Vega",
    "maria trinidad sanchez": "María Trinidad Sánchez",
    "mariatrinidadsanchez": "María Trinidad Sánchez",
    "maría trinidad sánchez": "María Trinidad Sánchez",
    "maríatrinidadsánchez": "María Trinidad Sánchez",
    "monsenor nouel": "Monseñor Nouel",
    "monsenornouel": "Monseñor Nouel",
    "monseñor nouel": "Monseñor Nouel",
    "monseñornouel": "Monseñor Nouel",
    "monte cristi": "Monte Cristi",
    "montecristi": "Monte Cristi",
    "monte plata": "Monte Plata",
    "monteplata": "Monte Plata",
    "pedernales": "Pedernales",
    "peravia": "Peravia",
    "puerto plata": "Puerto Plata",
    "puertoplata": "Puerto Plata",
    "samana": "Samaná",
    "samaná": "Samaná",
    "san cristobal": "San Cristóbal",
    "sancristobal": "San Cristóbal",
    "san cristóbal": "San Cristóbal",
    "sancristóbal": "San Cristóbal",
    "san jose de ocoa": "San José de Ocoa",
    "sanjosedeocoa": "San José de Ocoa",
    "san josé de ocoa": "San José de Ocoa",
    "sanjosédeocoa": "San José de Ocoa",
    "san juan": "San Juan",
    "sanjuan": "San Juan",
    "san pedro de macoris": "San Pedro de Macorís",
    "sanpedrodemacoris": "San Pedro de Macorís",
    "san pedro de macorís": "San Pedro de Macorís",
    "sanpedrodemacorís": "San Pedro de Macorís",
    "sanchez ramirez": "Sánchez Ramírez",
    "sanchezramirez": "Sánchez Ramírez",
    "sánchez ramírez": "Sánchez Ramírez",
    "sánchezramírez": "Sánchez Ramírez",
    "santiago": "Santiago",
    "santiago rodriguez": "Santiago Rodríguez",
    "santiagorodriguez": "Santiago Rodríguez",
    "santiago rodríguez": "Santiago Rodríguez",
    "santiagorodríguez": "Santiago Rodríguez",
    "santo domingo": "Santo Domingo",
    "santodomingo": "Santo Domingo",
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
    return normalize_text(canonical_province(name)).replace(" ", "_")
