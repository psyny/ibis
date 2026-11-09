"""Task categories and locations: each household has its own lists (managers edit them).

New households start with these defaults, named in the household's language. The `key` stays with a
default even if it is renamed, so e.g. month-close payment tasks still find "Bills".
"""
from typing import Literal

LabelKind = Literal["category", "location"]
KIND_CATEGORY = "category"
KIND_LOCATION = "location"
KEY_BILLS = "bills"

#           key            en               pt-BR            de               fr                 it                zh-CN   ja            ko         hi
_CATEGORIES = [
    ("cleaning",    "Cleaning",    "Limpeza",    "Putzen",       "Ménage",       "Pulizie",      "清洁", "掃除",         "청소",     "सफ़ाई"),
    ("maintenance", "Maintenance", "Manutenção", "Wartung",      "Entretien",    "Manutenzione", "保养", "メンテナンス", "유지보수", "रखरखाव"),
    ("repair",      "Repair",      "Conserto",   "Reparatur",    "Réparation",   "Riparazione",  "维修", "修理",         "수리",     "मरम्मत"),
    ("improvement", "Improvement", "Melhoria",   "Verbesserung", "Amélioration", "Miglioria",    "改善", "改善",         "개선",     "सुधार"),
    ("bills",       "Bills",       "Contas",     "Rechnungen",   "Factures",     "Bollette",     "账单", "支払い",       "공과금",   "बिल"),
    ("shopping",    "Shopping",    "Compras",    "Einkaufen",    "Courses",      "Spesa",        "购物", "買い物",       "장보기",   "ख़रीदारी"),
    ("pets",        "Pets",        "Animais",    "Haustiere",    "Animaux",      "Animali",      "宠物", "ペット",       "반려동물", "पालतू जानवर"),
    ("other",       "Other",       "Outros",     "Sonstiges",    "Autre",        "Altro",        "其他", "その他",       "기타",     "अन्य"),
]

_LOCATIONS = [
    ("whole_house", "Whole house", "Casa toda",  "Ganzes Haus",  "Toute la maison", "Tutta la casa",   "全屋",   "家全体",     "집 전체", "पूरा घर"),
    ("living_room", "Living room", "Sala",       "Wohnzimmer",   "Salon",           "Soggiorno",       "客厅",   "リビング",   "거실",    "बैठक"),
    ("kitchen",     "Kitchen",     "Cozinha",    "Küche",        "Cuisine",         "Cucina",          "厨房",   "キッチン",   "주방",    "रसोई"),
    ("bedroom",     "Bedroom",     "Quarto",     "Schlafzimmer", "Chambre",         "Camera da letto", "卧室",   "寝室",       "침실",    "शयनकक्ष"),
    ("bathroom",    "Bathroom",    "Banheiro",   "Badezimmer",   "Salle de bain",   "Bagno",           "浴室",   "浴室",       "욕실",    "बाथरूम"),
    ("laundry",     "Laundry",     "Lavanderia", "Waschküche",   "Buanderie",       "Lavanderia",      "洗衣房", "ランドリー", "세탁실",  "कपड़े धोने की जगह"),
    ("office",      "Office",      "Escritório", "Büro",         "Bureau",          "Studio",          "书房",   "書斎",       "서재",    "ऑफ़िस"),
    ("garage",      "Garage",      "Garagem",    "Garage",       "Garage",          "Garage",          "车库",   "ガレージ",   "차고",    "गैराज"),
    ("garden",      "Garden",      "Jardim",     "Garten",       "Jardin",          "Giardino",        "花园",   "庭",         "정원",    "बगीचा"),
]

_LANGUAGES = ["en", "pt-BR", "de", "fr", "it", "zh-CN", "ja", "ko", "hi"]


def default_labels(language: str) -> list[tuple[str, str, str]]:
    """(kind, key, name) for a new household, in list order."""
    column = _LANGUAGES.index(language) + 1 if language in _LANGUAGES else 1
    return [(KIND_CATEGORY, row[0], row[column]) for row in _CATEGORIES] + [
        (KIND_LOCATION, row[0], row[column]) for row in _LOCATIONS
    ]
