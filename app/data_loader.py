"""In-memory cache for courses JSON and guide metadata."""

from __future__ import annotations

import json
import os
import re

import frontmatter

try:
    from .config import GUIDE_IMAGES
    from .content_new import enrich_item
    from .paths import DATA_FILE, GUIDE_DIR
    from .text_utils import clean_summary, get_meta_fallback, humanize_title, short_summary
except ImportError:
    from config import GUIDE_IMAGES
    from content_new import enrich_item
    from paths import DATA_FILE, GUIDE_DIR
    from text_utils import clean_summary, get_meta_fallback, humanize_title, short_summary

CACHED_DATA: dict = {"courses": []}
CACHED_GUIDES: list = []
_CACHE_MTIME: float = 0.0


def load_all_data() -> None:
    """서버 시작 시 메모리에 모든 마크다운 및 JSON 데이터를 로드"""
    global CACHED_GUIDES, _CACHE_MTIME

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                CACHED_DATA.clear()
                CACHED_DATA.update(data)
                _CACHE_MTIME = os.path.getmtime(DATA_FILE)
                print(f"✅ Course JSON loaded: {len(CACHED_DATA.get('courses', []))} items")
        except Exception as e:
            print(f"❌ Course Data error: {e}")
            CACHED_DATA.clear()
            CACHED_DATA.update({"courses": []})

    temp_guides = []
    if os.path.exists(GUIDE_DIR):
        files = sorted([f for f in os.listdir(GUIDE_DIR) if f.endswith(".md")], reverse=True)
        for filename in files:
            try:
                full_id = filename.replace(".md", "")
                if full_id.startswith("_") or "_" not in full_id:
                    continue

                with open(os.path.join(GUIDE_DIR, filename), "r", encoding="utf-8") as f:
                    raw_text = f.read().strip()
                    if "---" in raw_text:
                        raw_text = "---" + raw_text.split("---", 1)[1]

                    post = frontmatter.loads(raw_text)
                    item = dict(post.metadata)

                    base_id = full_id.rsplit("_", 1)[0]
                    detected_lang = "ko" if full_id.endswith("_ko") else "en"

                    title = item.get("title") or get_meta_fallback(raw_text, "title")
                    summary = item.get("summary") or get_meta_fallback(raw_text, "summary")

                    if not summary or "lang:" in summary:
                        clean_body = re.sub(r"---.*?---", "", post.content, flags=re.DOTALL).strip()
                        summary = clean_body[:130].replace("\n", " ") + "..."

                    title = humanize_title(title) or "Japan Golf Guide"

                    temp_guides.append(
                        enrich_item(
                            {
                                "id": full_id,
                                "base_id": base_id,
                                "lang": detected_lang,
                                "title": title,
                                "summary": short_summary(
                                    clean_summary(summary, title, detected_lang), 200
                                ),
                                "published": str(item.get("date", "2026-04-12")),
                                "image": GUIDE_IMAGES[abs(hash(base_id) * 97) % len(GUIDE_IMAGES)],
                            }
                        )
                    )
            except Exception as e:
                print(f"❌ Guide load error ({filename}): {e}")

    CACHED_GUIDES.clear()
    CACHED_GUIDES.extend(temp_guides)
    print(f"✅ AI Guides loaded: {len(CACHED_GUIDES)} items")


def ensure_course_cache() -> None:
    global _CACHE_MTIME
    if not os.path.exists(DATA_FILE):
        return
    try:
        mtime = os.path.getmtime(DATA_FILE)
    except OSError:
        return
    if mtime <= _CACHE_MTIME:
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            CACHED_DATA.clear()
            CACHED_DATA.update(data)
        _CACHE_MTIME = mtime
    except (OSError, json.JSONDecodeError):
        pass
