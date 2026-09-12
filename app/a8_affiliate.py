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
        "desc_en": "Book stays for your golf trip in Japan.",
        "desc_ko": "일본 골프 여행 숙소 예약.",
        "alt_en": "Agoda — affiliate",
        "alt_ko": "Agoda — 제휴",
    },
    "rakuten_esim": {
        "id": "rakuten_esim",
        "click_url": "https://a.r10.to/hPsyyI",
        "image_url": "",
        "pixel_url": "",
        "label_en": "Rakuten eSIM — Japan travel",
        "label_ko": "라쿠텐 eSIM — 일본 여행",
        "desc_en": "Japan travel eSIM.",
        "desc_ko": "일본 여행 eSIM.",
        "alt_en": "Rakuten eSIM",
        "alt_ko": "라쿠텐 eSIM",
    },
    "rakuten_travel": {
        "id": "rakuten_travel",
        "click_url": "https://a.r10.to/h5didY",
        "image_url": "",
        "pixel_url": "",
        "label_en": "Rakuten Travel — hotels in Japan",
        "label_ko": "라쿠텐 트래블 — 일본 숙소",
        "desc_en": "Book hotels for your Japan golf trip.",
        "desc_ko": "일본 골프 여행 숙소 예약.",
        "alt_en": "Rakuten Travel",
        "alt_ko": "라쿠텐 트래블",
    },
}


def _enabled() -> bool:
    return os.getenv("A8_OKCADDIE_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _copy(banner_id: str, *, lang: str) -> dict[str, str]:
    src = _BANNERS[banner_id]
    is_ko = (lang or "en").lower() == "ko"
    suffix = "ko" if is_ko else "en"
    key = banner_id.upper()
    return {
        "id": src["id"],
        "click_url": os.getenv(f"A8_{key}_CLICK_URL", src["click_url"]),
        "image_url": os.getenv(f"A8_{key}_BANNER_URL", src["image_url"]),
        "pixel_url": os.getenv(f"A8_{key}_PIXEL_URL", src["pixel_url"]),
        "label": src[f"label_{suffix}"],
        "desc": src[f"desc_{suffix}"],
        "alt": src[f"alt_{suffix}"],
    }


def a8_banners_context(*, lang: str = "en") -> dict[str, Any]:
    if not _enabled():
        return {"show_a8_banners": False, "a8_banners": []}
    is_ko = (lang or "en").lower() == "ko"
    banners = [_copy("agoda", lang=lang), _copy("rakuten_travel", lang=lang)]
    if is_ko:
        banners.append(_copy("rakuten_esim", lang=lang))
    return {
        "show_a8_banners": True,
        "a8_banners": banners,
        "a8_banners_title": (
            "골프 여행 제휴" if is_ko else "Golf trip partners"
        ),
        "a8_banners_note": (
            "제휴 광고 · 새 탭에서 열림"
            if is_ko
            else "Affiliate ads · opens in new tab"
        ),
    }
