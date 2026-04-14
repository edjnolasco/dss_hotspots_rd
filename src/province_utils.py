from __future__ import annotations

import unicodedata


def normalize_text(value: str) -> str:
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = "".join(text.split())
    return text


_PROVINCE_ALIASES = {
    "distritonacional": "distritonacional",
    "dn": "distritonacional",
    "dist.nac.": "distritonacional",

    "santodomingo": "santodomingo",
    "provinciasantodomingo": "santodomingo",

    "elseibo": "elseybo",
    "elseybo": "elseybo",
    "seibo": "elseybo",

    "eliaspina": "laestrelleta",
    "laestrelleta": "laestrelleta",
    "sanrafael": "laestrelleta",

    "hatomayor": "hatomayor",
    "hatomayordelrey": "hatomayor",
    "hatomajor": "hatomayor",

    "hermanasmirabal": "salcedo",
    "salcedo": "salcedo",

    "laaltagracia": "laaltagracia",
    "laromana": "laromana",
    "lavega": "lavega",

    "mariatrinidadsanchez": "mariatrinidadsanchez",
    "trinidadsanchez": "mariatrinidadsanchez",

    "monsenornouel": "monseñornouel",
    "monseñornouel": "monseñornouel",

    "montecristi": "montecristi",
    "monteplata": "monteplata",
    "puertoplata": "puertoplata",

    "sancristobal": "sancristobal",
    "sanjosedeocoa": "sanjosedeocoa",
    "sanjuan": "sanjuan",
    "sanjuandelamaguana": "sanjuan",
    "sanpedrodemacoris": "sanpedrodemacoris",
    "santiagorodriguez": "santiagorodriguez",
    "sanchezramirez": "sanchezramirez",

    "azua": "azua",
    "azuadecompostela": "azua",
    "bahoruco": "bahoruco",
    "baoruco": "bahoruco",
    "barahona": "barahona",
    "dajabon": "dajabon",
    "duarte": "duarte",
    "espaillat": "espaillat",
    "independencia": "independencia",
    "pedernales": "pedernales",
    "peravia": "peravia",
    "samana": "samana",
    "santiago": "santiago",
    "santiagodeloscaballeros": "santiago",
    "valverde": "valverde",
}


_CANONICAL_TO_DISPLAY = {
    "distritonacional": "Distrito Nacional",
    "santodomingo": "Santo Domingo",
    "elseybo": "El Seibo",
    "laestrelleta": "Elías Piña",
    "hatomayor": "Hato Mayor",
    "salcedo": "Hermanas Mirabal",
    "laaltagracia": "La Altagracia",
    "laromana": "La Romana",
    "lavega": "La Vega",
    "mariatrinidadsanchez": "María Trinidad Sánchez",
    "monseñornouel": "Monseñor Nouel",
    "montecristi": "Monte Cristi",
    "monteplata": "Monte Plata",
    "puertoplata": "Puerto Plata",
    "sancristobal": "San Cristóbal",
    "sanjosedeocoa": "San José de Ocoa",
    "sanjuan": "San Juan",
    "sanpedrodemacoris": "San Pedro de Macorís",
    "santiagorodriguez": "Santiago Rodríguez",
    "sanchezramirez": "Sánchez Ramírez",
    "azua": "Azua",
    "bahoruco": "Bahoruco",
    "barahona": "Barahona",
    "dajabon": "Dajabón",
    "duarte": "Duarte",
    "espaillat": "Espaillat",
    "independencia": "Independencia",
    "pedernales": "Pedernales",
    "peravia": "Peravia",
    "samana": "Samaná",
    "santiago": "Santiago",
    "valverde": "Valverde",
}


def canonical_province(value: str) -> str:
    text = normalize_text(value)
    return _PROVINCE_ALIASES.get(text, text)


def display_province_name(value: str) -> str:
    canonical = canonical_province(value)
    return _CANONICAL_TO_DISPLAY.get(canonical, str(value).strip())


def build_geo_aliases(raw_name: str, varname: str | None = None) -> set[str]:
    aliases = {canonical_province(raw_name)}

    if varname and str(varname).strip() and str(varname).strip().upper() != "NA":
        for part in str(varname).split("|"):
            alias = part.strip()
            if alias:
                aliases.add(canonical_province(alias))

    return aliases