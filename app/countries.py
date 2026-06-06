"""ISO 3166-1 alpha-2 country codes -> name (EN) + flag emoji.

The flag is derived from the code using the regional indicator symbols, with
no dependency or data file.
"""

from __future__ import annotations

COUNTRY_NAMES: dict[str, str] = {
    "AD": "Andorra", "AE": "United Arab Emirates", "AF": "Afghanistan",
    "AG": "Antigua and Barbuda", "AL": "Albania", "AM": "Armenia",
    "AO": "Angola", "AR": "Argentina", "AT": "Austria", "AU": "Australia",
    "AZ": "Azerbaijan", "BA": "Bosnia and Herzegovina", "BB": "Barbados",
    "BD": "Bangladesh", "BE": "Belgium", "BF": "Burkina Faso",
    "BG": "Bulgaria", "BH": "Bahrain", "BI": "Burundi", "BJ": "Benin",
    "BN": "Brunei", "BO": "Bolivia", "BR": "Brazil", "BS": "Bahamas",
    "BT": "Bhutan", "BW": "Botswana", "BY": "Belarus", "BZ": "Belize",
    "CA": "Canada", "CD": "DR Congo", "CF": "Central African Rep.", "CG": "Congo",
    "CH": "Switzerland", "CI": "Côte d'Ivoire", "CL": "Chile", "CM": "Cameroon",
    "CN": "China", "CO": "Colombia", "CR": "Costa Rica", "CU": "Cuba",
    "CV": "Cape Verde", "CY": "Cyprus", "CZ": "Czechia", "DE": "Germany",
    "DJ": "Djibouti", "DK": "Denmark", "DM": "Dominica",
    "DO": "Dominican Rep.", "DZ": "Algeria", "EC": "Ecuador",
    "EE": "Estonia", "EG": "Egypt", "ER": "Eritrea", "ES": "Spain",
    "ET": "Ethiopia", "FI": "Finland", "FJ": "Fiji", "FR": "France",
    "GA": "Gabon", "GB": "United Kingdom", "GD": "Grenada", "GE": "Georgia",
    "GH": "Ghana", "GM": "Gambia", "GN": "Guinea", "GQ": "Equatorial Guinea",
    "GR": "Greece", "GT": "Guatemala", "GW": "Guinea-Bissau", "GY": "Guyana",
    "HK": "Hong Kong", "HN": "Honduras", "HR": "Croatia", "HT": "Haiti",
    "HU": "Hungary", "ID": "Indonesia", "IE": "Ireland", "IL": "Israel",
    "IN": "India", "IQ": "Iraq", "IR": "Iran", "IS": "Iceland", "IT": "Italy",
    "JM": "Jamaica", "JO": "Jordan", "JP": "Japan", "KE": "Kenya",
    "KG": "Kyrgyzstan", "KH": "Cambodia", "KM": "Comoros",
    "KN": "Saint Kitts and Nevis", "KP": "North Korea", "KR": "South Korea",
    "KW": "Kuwait", "KZ": "Kazakhstan", "LA": "Laos", "LB": "Lebanon",
    "LC": "Saint Lucia", "LI": "Liechtenstein", "LK": "Sri Lanka",
    "LR": "Liberia", "LS": "Lesotho", "LT": "Lithuania", "LU": "Luxembourg",
    "LV": "Latvia", "LY": "Libya", "MA": "Morocco", "MC": "Monaco",
    "MD": "Moldova", "ME": "Montenegro", "MG": "Madagascar",
    "MK": "North Macedonia", "ML": "Mali", "MM": "Myanmar",
    "MN": "Mongolia", "MR": "Mauritania", "MT": "Malta", "MU": "Mauritius",
    "MV": "Maldives", "MW": "Malawi", "MX": "Mexico", "MY": "Malaysia",
    "MZ": "Mozambique", "NA": "Namibia", "NE": "Niger", "NG": "Nigeria",
    "NI": "Nicaragua", "NL": "Netherlands", "NO": "Norway", "NP": "Nepal",
    "NZ": "New Zealand", "OM": "Oman", "PA": "Panama", "PE": "Peru",
    "PG": "Papua New Guinea", "PH": "Philippines", "PK": "Pakistan",
    "PL": "Poland", "PT": "Portugal", "PY": "Paraguay", "QA": "Qatar",
    "RO": "Romania", "RS": "Serbia", "RU": "Russia", "RW": "Rwanda",
    "SA": "Saudi Arabia", "SB": "Solomon Islands", "SC": "Seychelles",
    "SD": "Sudan", "SE": "Sweden", "SG": "Singapore", "SI": "Slovenia",
    "SK": "Slovakia", "SL": "Sierra Leone", "SM": "San Marino",
    "SN": "Senegal", "SO": "Somalia", "SR": "Suriname", "SS": "South Sudan",
    "ST": "Sao Tome and Principe", "SV": "El Salvador", "SY": "Syria",
    "SZ": "Eswatini", "TD": "Chad", "TG": "Togo", "TH": "Thailand",
    "TJ": "Tajikistan", "TL": "Timor-Leste", "TM": "Turkmenistan",
    "TN": "Tunisia", "TO": "Tonga", "TR": "Turkey",
    "TT": "Trinidad and Tobago", "TW": "Taiwan", "TZ": "Tanzania",
    "UA": "Ukraine", "UG": "Uganda", "US": "United States", "UY": "Uruguay",
    "UZ": "Uzbekistan", "VA": "Vatican", "VC": "Saint Vincent",
    "VE": "Venezuela", "VN": "Vietnam", "VU": "Vanuatu", "YE": "Yemen",
    "ZA": "South Africa", "ZM": "Zambia", "ZW": "Zimbabwe",
}


def flag_emoji(code: str) -> str:
    """Flag emoji from a 2-letter code ('FR' -> 🇫🇷)."""
    code = (code or "").upper()
    if len(code) != 2 or not code.isalpha():
        return "🏳️"
    return "".join(chr(0x1F1E6 + ord(ch) - ord("A")) for ch in code)


def country_name(code: str) -> str:
    code = (code or "").upper()
    return COUNTRY_NAMES.get(code, code or "Unknown")
