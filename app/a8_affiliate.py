"""A8.net affiliate banners for OK Caddie."""

from __future__ import annotations

import os
from typing import Any

_BANNERS: dict[str, dict[str, str]] = {
    "agoda": {
        "id": "agoda",
        "click_url": "https://px.a8.net/svt/ejp?a8mat=4BAH9J+13AQKA+4X1W+5ZMCH",
        "image_url": "https://www29.a8.net/svt/bgt?aid=260829415066&wid=006&eno=01&mid=s00000022946001006000&mc=1",
        "pixel_url": "https://www13.a8.net/0.gif?a8mat=4BAH9J+13AQKA+4X1W+5ZMCH",
        "label_en": "Agoda — hotels near the course",
        "label_ko": "Agoda — 골프장 주변 숙소",
        "label_ja": "Agoda — コース周辺ホテル",
        "desc_en": "Book stays for your golf trip in Japan.",
        "desc_ko": "일본 골프 여행 숙소 예약.",
        "desc_ja": "ゴルフ旅行の宿泊予約。",
        "alt_en": "Agoda — affiliate",
        "alt_ko": "Agoda — 제휴",
        "alt_ja": "Agoda — アフィリエイト",
    },
    "rakuten_esim": {
        "id": "rakuten_esim",
        "click_url": "https://a.r10.to/hPsyyI",
        "image_url": "",
        "pixel_url": "",
        "label_en": "Rakuten eSIM — Japan travel",
        "label_ko": "라쿠텐 eSIM — 일본 여행",
        "label_ja": "楽天 eSIM — 日本旅行",
        "desc_en": "Japan travel eSIM.",
        "desc_ko": "일본 여행 eSIM.",
        "desc_ja": "日本旅行向けeSIM。",
        "alt_en": "Rakuten eSIM",
        "alt_ko": "라쿠텐 eSIM",
        "alt_ja": "楽天 eSIM",
    },
    "rakuten_travel": {
        "id": "rakuten_travel",
        "click_url": "https://a.r10.to/h5didY",
        "image_url": "",
        "pixel_url": "",
        "label_en": "Rakuten Travel — hotels in Japan",
        "label_ko": "라쿠텐 트래블 — 일본 숙소",
        "label_ja": "楽天トラベル — 国内宿",
        "desc_en": "Book hotels for your Japan golf trip.",
        "desc_ko": "일본 골프 여행 숙소 예약.",
        "desc_ja": "ゴルフ旅行の宿を検索。",
        "alt_en": "Rakuten Travel",
        "alt_ko": "라쿠텐 트래블",
        "alt_ja": "楽天トラベル",
    },
}


def _enabled() -> bool:
    return os.getenv("A8_OKCADDIE_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def a8_dest_url(banner_id: str) -> str:
    src = _BANNERS.get((banner_id or "").strip().lower())
    if not src:
        return ""
    key = src["id"].upper()
    return os.getenv(f"A8_{key}_CLICK_URL", src["click_url"])


def _copy(banner_id: str, *, lang: str) -> dict[str, str]:
    src = _BANNERS[banner_id]
    code = (lang or "en").lower()
    suffix = code if code in ("ko", "ja") else "en"
    key = banner_id.upper()
    return {
        "id": src["id"],
        "click_url": f"/go/{banner_id}",
        "image_url": os.getenv(f"A8_{key}_BANNER_URL", src["image_url"]),
        "pixel_url": os.getenv(f"A8_{key}_PIXEL_URL", src["pixel_url"]),
        "label": src[f"label_{suffix}"],
        "desc": src[f"desc_{suffix}"],
        "alt": src[f"alt_{suffix}"],
    }


def a8_banners_context(*, lang: str = "en") -> dict[str, Any]:
    if not _enabled():
        return {"show_a8_banners": False, "a8_banners": []}
    code = (lang or "en").lower()
    banners = [_copy("agoda", lang=lang), _copy("rakuten_travel", lang=lang)]
    if code == "ko":
        banners.append(_copy("rakuten_esim", lang=lang))
    titles = {
        "ko": "골프 여행 제휴",
        "ja": "ゴルフトリップ提携",
        "en": "Golf trip partners",
    }
    notes = {
        "ko": "제휴 광고 · 새 탭에서 열림",
        "ja": "アフィリエイト広告 · 新しいタブで開きます",
        "en": "Affiliate ads · opens in new tab",
    }
    return {
        "show_a8_banners": True,
        "a8_banners": banners,
        "a8_banners_title": titles.get(code, titles["en"]),
        "a8_banners_note": notes.get(code, notes["en"]),
    }
