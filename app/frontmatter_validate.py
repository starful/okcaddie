"""Validate markdown frontmatter lang vs title/seo script."""

from __future__ import annotations

import os
import re
from pathlib import Path

import frontmatter

try:
    from .paths import CONTENT_DIR, GUIDE_DIR
except ImportError:
    from paths import CONTENT_DIR, GUIDE_DIR

_HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
_LATIN_WORD_RE = re.compile(r"[A-Za-z]{4,}")

META_KEYS = ("title", "seo_title", "seo_description", "description", "summary")


def _lang_from_filename(path: str) -> str | None:
    stem = Path(path).stem
    if stem.endswith("_ko"):
        return "ko"
    if stem.endswith("_en"):
        return "en"
    return None


def hangul_ratio(text: str) -> float:
    if not text:
        return 0.0
    chars = [c for c in str(text) if not c.isspace()]
    if not chars:
        return 0.0
    return sum(1 for c in chars if _HANGUL_RE.match(c)) / len(chars)


def latin_word_count(text: str) -> int:
    return len(_LATIN_WORD_RE.findall(str(text)))


def validate_meta_text(lang: str, field: str, value: str) -> str | None:
    if not value or not str(value).strip():
        return None
    text = str(value).strip()
    ratio = hangul_ratio(text)
    if lang == "en" and ratio >= 0.15:
        return f"{field} has Korean-heavy text ({ratio:.0%}) for lang=en"
    return None


def validate_file(path: str) -> list[str]:
    errors: list[str] = []
    lang = _lang_from_filename(path)
    if not lang:
        return errors

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    if "---" in raw and not raw.startswith("---"):
        raw = "---" + raw.split("---", 1)[1]
    post = frontmatter.loads(raw)

    meta_lang = str(post.get("lang") or lang).strip().lower()
    if meta_lang != lang:
        errors.append(f"lang mismatch: filename={lang}, frontmatter={meta_lang}")

    for key in META_KEYS:
        err = validate_meta_text(lang, key, post.get(key, ""))
        if err:
            errors.append(err)
    return errors


def iter_content_files(content_dir: str | None = None, guide_dir: str | None = None):
    content_dir = content_dir or CONTENT_DIR
    guide_dir = guide_dir or GUIDE_DIR
    if os.path.isdir(content_dir):
        for name in sorted(os.listdir(content_dir)):
            if name.endswith(".md") and not name.startswith("_"):
                yield os.path.join(content_dir, name)
    if os.path.isdir(guide_dir):
        for name in sorted(os.listdir(guide_dir)):
            if name.endswith(".md"):
                yield os.path.join(guide_dir, name)


def collect_violations(content_dir: str | None = None, guide_dir: str | None = None) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    for path in iter_content_files(content_dir, guide_dir):
        errs = validate_file(path)
        if errs:
            out.append((path, errs))
    return out
