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


def split_localized_id(item_id):
    if item_id.endswith("_ko"):
        return item_id[:-3], "ko"
    if item_id.endswith("_en"):
        return item_id[:-3], "en"
    return item_id, None


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
    return f"/course/{base_id}" + ("?lang=ko" if lang == "ko" else "")
