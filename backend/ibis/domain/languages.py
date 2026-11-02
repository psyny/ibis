"""Interface languages a household can use. The frontend has one translation file per code."""
from typing import Literal

LanguageCode = Literal["en", "pt-BR", "de", "fr", "it", "zh-CN", "ja", "ko", "hi"]

DEFAULT_LANGUAGE = "en"
