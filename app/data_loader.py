"""In-memory cache for courses JSON and guide metadata."""

from __future__ import annotations

import json
import os

try:
    from .guide_content import build_guide_list_item
    from .paths import DATA_FILE, GUIDE_DIR
except ImportError:
    from guide_content import build_guide_list_item
    from paths import DATA_FILE, GUIDE_DIR

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
                item = build_guide_list_item(filename)
                if item:
                    temp_guides.append(item)
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
