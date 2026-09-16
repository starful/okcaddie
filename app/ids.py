"""Localized content ID helpers."""

from __future__ import annotations

import os

try:
    from .paths import CONTENT_DIR, GUIDE_DIR
except ImportError:
    from paths import CONTENT_DIR, GUIDE_DIR

try:
    from .config import PREFECTURE_KEYWORDS
except ImportError:
    from config import PREFECTURE_KEYWORDS

_LANG_SUFFIXES = ("_ko", "_en", "_ja")


def split_localized_id(item_id):
    for suf in _LANG_SUFFIXES:
        if item_id.endswith(suf):
            return item_id[: -len(suf)], suf[1:]
    return item_id, None


def lang_from_course_id(course_id: str) -> str:
    _, lang = split_localized_id(course_id or "")
    return lang or "en"


def extract_prefecture(text):
    if not text:
        return ""
    for pref in PREFECTURE_KEYWORDS:
        if pref in text:
            return pref
    return ""


def resolve_course_id(base_id, lang):
    course_id = f"{base_id}_{lang}"
    if os.path.exists(os.path.join(CONTENT_DIR, f"{course_id}.md")):
        return course_id
    fallback_id = f"{base_id}_en"
    if os.path.exists(os.path.join(CONTENT_DIR, f"{fallback_id}.md")):
        return fallback_id
    return None


def resolve_guide_id(base_id, lang):
    guide_id = f"{base_id}_{lang}"
    if os.path.exists(os.path.join(GUIDE_DIR, f"{guide_id}.md")):
        return guide_id
    fallback_id = f"{base_id}_en"
    if os.path.exists(os.path.join(GUIDE_DIR, f"{fallback_id}.md")):
        return fallback_id
    return None


def course_href(base_id, lang):
    if lang == "ko":
        return f"/course/{base_id}?lang=ko"
    if lang == "ja":
        return f"/course/{base_id}?lang=ja"
    return f"/course/{base_id}"


def guide_href(base_id, lang):
    if lang == "ko":
        return f"/guide/{base_id}?lang=ko"
    if lang == "ja":
        return f"/guide/{base_id}?lang=ja"
    return f"/guide/{base_id}"
