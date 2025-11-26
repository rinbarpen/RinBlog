from __future__ import annotations

from typing import Literal

SUPPORTED_LANGUAGES = ["en", "zh"]
DEFAULT_LANGUAGE = "en"

LanguageCode = Literal["en", "zh"]


def normalize_lang(lang: str | None) -> LanguageCode:
    """Normalize language code to supported value."""
    if not lang:
        return DEFAULT_LANGUAGE
    normalized = lang.lower().strip()[:2]
    if normalized in SUPPORTED_LANGUAGES:
        return normalized  # type: ignore
    return DEFAULT_LANGUAGE


def get_language_names() -> dict[str, str]:
    """Get display names for languages."""
    return {
        "en": "English",
        "zh": "中文",
    }

