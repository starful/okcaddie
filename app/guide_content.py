"""Guide markdown loading helpers."""

from __future__ import annotations

import os
import re

import frontmatter

try:
    from .config import GUIDE_IMAGES
    from .badges import enrich_item
    from .paths import GUIDE_DIR
    from .text_utils import clean_summary, get_meta_fallback, humanize_title, short_summary
except ImportError:
    from badges import enrich_item
    from config import GUIDE_IMAGES
    from paths import GUIDE_DIR
    from text_utils import clean_summary, get_meta_fallback, humanize_title, short_summary


def normalize_guide_raw(raw: str) -> str:
    raw = raw.strip()
    if "---" in raw and not raw.startswith("---"):
        raw = "---" + raw.split("---", 1)[1]
    return raw


def load_guide_post(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return frontmatter.loads(normalize_guide_raw(f.read()))


def guide_id_parts(guide_id: str) -> tuple[str, str]:
    base_id = guide_id.rsplit("_", 1)[0]
    lang = "ko" if guide_id.endswith("_ko") else "en"
    return base_id, lang


def build_guide_list_item(filename: str) -> dict | None:
    full_id = filename.replace(".md", "")
    if full_id.startswith("_") or "_" not in full_id:
        return None

    path = os.path.join(GUIDE_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        raw_text = f.read()
    post = frontmatter.loads(normalize_guide_raw(raw_text))
    item = dict(post.metadata)
    base_id, detected_lang = guide_id_parts(full_id)

    title = item.get("title") or get_meta_fallback(raw_text, "title")
    summary = item.get("summary") or get_meta_fallback(raw_text, "summary")
    if not summary or "lang:" in summary:
        clean_body = re.sub(r"---.*?---", "", post.content, flags=re.DOTALL).strip()
        summary = clean_body[:130].replace("\n", " ") + "..."

    title = humanize_title(title) or "Japan Golf Guide"
    return enrich_item(
        {
            "id": full_id,
            "base_id": base_id,
            "lang": detected_lang,
            "title": title,
            "summary": short_summary(clean_summary(summary, title, detected_lang), 200),
            "published": str(item.get("date", "2026-04-12")),
            "image": GUIDE_IMAGES[abs(hash(base_id) * 97) % len(GUIDE_IMAGES)],
        }
    )


def guide_image_url(base_id: str) -> str:
    return GUIDE_IMAGES[abs(hash(base_id) * 97) % len(GUIDE_IMAGES)]
