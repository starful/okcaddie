"""Amazon JP Associates search links for OK Caddie (golf gear by guide kind)."""

from __future__ import annotations

import os
from urllib.parse import quote

AMAZON_TAG = os.getenv("AMAZON_JP_TAG", "starful06-22")

# Default golf URL (unchanged from the original single banner).
AMAZON_GOLF_URL = os.getenv(
    "AMAZON_JP_GOLF_URL",
    "https://www.amazon.co.jp/s?k=golf&tag=starful06-22&linkCode=ll2"
    "&linkId=1b50c5ce7e68ac003be574ef9650dbee&ref_=as_li_ss_tl",
)

# kind -> Amazon search keyword. "golf" keeps AMAZON_GOLF_URL.
AMAZON_KEYWORDS: dict[str, str] = {
    "beginner": "ゴルフ 初心者",
    "foliage": "ゴルフ ウェア",
}

_BEGINNER_MARKERS = ("beginner",)
_FOLIAGE_MARKERS = ("foliage", "autumn", "fall-", "koyo")


def amazon_kind(base_id: str | None = None) -> str:
    """Guess guide kind from a guide base id (e.g. beginner-golf-japan)."""
    gid = (base_id or "").strip().lower()
    if any(m in gid for m in _BEGINNER_MARKERS):
        return "beginner"
    if any(m in gid for m in _FOLIAGE_MARKERS):
        return "foliage"
    return "golf"


def amazon_search_url(keyword: str) -> str:
    return f"https://www.amazon.co.jp/s?k={quote(keyword)}&tag={AMAZON_TAG}"


def amazon_url(kind: str | None = None) -> str:
    key = (kind or "golf").strip().lower()
    kw = AMAZON_KEYWORDS.get(key)
    if not kw:
        return AMAZON_GOLF_URL
    return amazon_search_url(kw)
