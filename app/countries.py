"""ISO 3166-1 alpha-2 country codes -> name (FR) + flag emoji.

The flag is derived from the code using the regional indicator symbols, with
no dependency or data file. The names are kept in French (UI language).
"""

from __future__ import annotations

COUNTRY_NAMES: dict[str, str] = {
    "AD": "Andorre", "AE": "Émirats arabes unis", "AF": "Afghanistan",
    "AG": "Antigua-et-Barbuda", "AL": "Albanie", "AM": "Arménie",
    "AO": "Angola", "AR": "Argentine", "AT": "Autriche", "AU": "Australie",
    "AZ": "Azerbaïdjan", "BA": "Bosnie-Herzégovine", "BB": "Barbade",
    "BD": "Bangladesh", "BE": "Belgique", "BF": "Burkina Faso",
    "BG": "Bulgarie", "BH": "Bahreïn", "BI": "Burundi", "BJ": "Bénin",
    "BN": "Brunei", "BO": "Bolivie", "BR": "Brésil", "BS": "Bahamas",
    "BT": "Bhoutan", "BW": "Botswana", "BY": "Biélorussie", "BZ": "Belize",
    "CA": "Canada", "CD": "RD Congo", "CF": "Centrafrique", "CG": "Congo",
    "CH": "Suisse", "CI": "Côte d'Ivoire", "CL": "Chili", "CM": "Cameroun",
    "CN": "Chine", "CO": "Colombie", "CR": "Costa Rica", "CU": "Cuba",
    "CV": "Cap-Vert", "CY": "Chypre", "CZ": "Tchéquie", "DE": "Allemagne",
    "DJ": "Djibouti", "DK": "Danemark", "DM": "Dominique",
    "DO": "Rép. dominicaine", "DZ": "Algérie", "EC": "Équateur",
    "EE": "Estonie", "EG": "Égypte", "ER": "Érythrée", "ES": "Espagne",
    "ET": "Éthiopie", "FI": "Finlande", "FJ": "Fidji", "FR": "France",
    "GA": "Gabon", "GB": "Royaume-Uni", "GD": "Grenade", "GE": "Géorgie",
    "GH": "Ghana", "GM": "Gambie", "GN": "Guinée", "GQ": "Guinée équatoriale",
    "GR": "Grèce", "GT": "Guatemala", "GW": "Guinée-Bissau", "GY": "Guyana",
    "HK": "Hong Kong", "HN": "Honduras", "HR": "Croatie", "HT": "Haïti",
    "HU": "Hongrie", "ID": "Indonésie", "IE": "Irlande", "IL": "Israël",
    "IN": "Inde", "IQ": "Irak", "IR": "Iran", "IS": "Islande", "IT": "Italie",
    "JM": "Jamaïque", "JO": "Jordanie", "JP": "Japon", "KE": "Kenya",
    "KG": "Kirghizistan", "KH": "Cambodge", "KM": "Comores",
    "KN": "Saint-Kitts-et-Nevis", "KP": "Corée du Nord", "KR": "Corée du Sud",
    "KW": "Koweït", "KZ": "Kazakhstan", "LA": "Laos", "LB": "Liban",
    "LC": "Sainte-Lucie", "LI": "Liechtenstein", "LK": "Sri Lanka",
    "LR": "Liberia", "LS": "Lesotho", "LT": "Lituanie", "LU": "Luxembourg",
    "LV": "Lettonie", "LY": "Libye", "MA": "Maroc", "MC": "Monaco",
    "MD": "Moldavie", "ME": "Monténégro", "MG": "Madagascar",
    "MK": "Macédoine du Nord", "ML": "Mali", "MM": "Birmanie",
    "MN": "Mongolie", "MR": "Mauritanie", "MT": "Malte", "MU": "Maurice",
    "MV": "Maldives", "MW": "Malawi", "MX": "Mexique", "MY": "Malaisie",
    "MZ": "Mozambique", "NA": "Namibie", "NE": "Niger", "NG": "Nigeria",
    "NI": "Nicaragua", "NL": "Pays-Bas", "NO": "Norvège", "NP": "Népal",
    "NZ": "Nouvelle-Zélande", "OM": "Oman", "PA": "Panama", "PE": "Pérou",
    "PG": "Papouasie-N.-Guinée", "PH": "Philippines", "PK": "Pakistan",
    "PL": "Pologne", "PT": "Portugal", "PY": "Paraguay", "QA": "Qatar",
    "RO": "Roumanie", "RS": "Serbie", "RU": "Russie", "RW": "Rwanda",
    "SA": "Arabie saoudite", "SB": "Salomon", "SC": "Seychelles",
    "SD": "Soudan", "SE": "Suède", "SG": "Singapour", "SI": "Slovénie",
    "SK": "Slovaquie", "SL": "Sierra Leone", "SM": "Saint-Marin",
    "SN": "Sénégal", "SO": "Somalie", "SR": "Suriname", "SS": "Soudan du Sud",
    "ST": "Sao Tomé-et-Principe", "SV": "Salvador", "SY": "Syrie",
    "SZ": "Eswatini", "TD": "Tchad", "TG": "Togo", "TH": "Thaïlande",
    "TJ": "Tadjikistan", "TL": "Timor oriental", "TM": "Turkménistan",
    "TN": "Tunisie", "TO": "Tonga", "TR": "Turquie",
    "TT": "Trinité-et-Tobago", "TW": "Taïwan", "TZ": "Tanzanie",
    "UA": "Ukraine", "UG": "Ouganda", "US": "États-Unis", "UY": "Uruguay",
    "UZ": "Ouzbékistan", "VA": "Vatican", "VC": "Saint-Vincent",
    "VE": "Venezuela", "VN": "Viêt Nam", "VU": "Vanuatu", "YE": "Yémen",
    "ZA": "Afrique du Sud", "ZM": "Zambie", "ZW": "Zimbabwe",
}


def flag_emoji(code: str) -> str:
    """Flag emoji from a 2-letter code ('FR' -> 🇫🇷)."""
    code = (code or "").upper()
    if len(code) != 2 or not code.isalpha():
        return "🏳️"
    return "".join(chr(0x1F1E6 + ord(ch) - ord("A")) for ch in code)


def country_name(code: str) -> str:
    code = (code or "").upper()
    return COUNTRY_NAMES.get(code, code or "Inconnu")
