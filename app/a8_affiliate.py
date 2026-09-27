"""Affiliate banners for OK Caddie.

Agoda = Agoda Partners (CID). Gear = Amazon JP Associates.
Rakuten eSIM = Rakuten affiliate (KO only). GORA tee-times stay elsewhere.
"""

from __future__ import annotations

import os
from typing import Any

try:
    from agoda_partners import partner_search_url, url_for_location
except ImportError:
    from .agoda_partners import partner_search_url, url_for_location

# Amazon JP Associates — golf gear search (tag=starful06-22)
AMAZON_GOLF_URL = os.getenv(
    "AMAZON_JP_GOLF_URL",
    "https://www.amazon.co.jp/s?k=golf&tag=starful06-22&linkCode=ll2"
    "&linkId=1b50c5ce7e68ac003be574ef9650dbee&ref_=as_li_ss_tl",
)

_BANNERS: dict[str, dict[str, str]] = {
    "agoda": {
        "id": "agoda",
        "click_url": "",
        "image_url": "",
        "pixel_url": "",
        "label_en": "Agoda — hotels near the course",
        "label_ko": "Agoda — 골프장 주변 숙소",
        "label_ja": "Agoda — コース周辺ホテル",
        "desc_en": "Book stays for your golf trip in Japan.",
        "desc_ko": "일본 골프 여행 숙소 예약.",
        "desc_ja": "ゴルフ旅行の宿泊予約。",
        "alt_en": "Agoda — hotels",
        "alt_ko": "Agoda — 숙소",
        "alt_ja": "Agoda — 宿泊",
    },
    "amazon_golf": {
        "id": "amazon_golf",
        "click_url": AMAZON_GOLF_URL,
        "image_url": "",
        "pixel_url": "",
        "label_en": "Amazon — golf gear",
        "label_ko": "Amazon — 골프 용품",
        "label_ja": "Amazon — ゴルフ用品",
        "desc_en": "Shop golf clubs and gear on Amazon.co.jp.",
        "desc_ko": "Amazon.co.jp에서 골프 용품 검색.",
        "desc_ja": "Amazon.co.jpでゴルフ用品を探す。",
        "alt_en": "Amazon golf gear",
        "alt_ko": "Amazon 골프 용품",
        "alt_ja": "Amazon ゴルフ用品",
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
}


def _enabled() -> bool:
    return os.getenv("A8_OKCADDIE_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def a8_dest_url(
    banner_id: str,
    *,
    city: str | int | None = None,
    lang: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    country: str | None = None,
) -> str:
    bid = (banner_id or "").strip().lower()
    if bid == "agoda":
        if city is not None and str(city).strip():
            return partner_search_url(lang=lang or "en", city_id=city)
        if lat is not None or lng is not None or country:
            return url_for_location(
                lang=lang or "en",
                lat=lat,
                lng=lng,
                country=country,
                default_city=5085,
            )
        return partner_search_url(lang=lang or "en", city_id=5085)
    src = _BANNERS.get(bid)
    if not src:
        return ""
    key = src["id"].upper()
    return os.getenv(f"A8_{key}_CLICK_URL", src["click_url"])


def _copy(
    banner_id: str,
    *,
    lang: str,
    lat: float | None = None,
    lng: float | None = None,
    country: str | None = None,
) -> dict[str, str]:
    src = _BANNERS[banner_id]
    code = (lang or "en").lower()
    suffix = code if code in ("ko", "ja") else "en"
    if banner_id == "agoda":
        click = url_for_location(
            lang=lang,
            lat=lat,
            lng=lng,
            country=country,
            default_city=5085 if (country or "jp").lower() in ("jp", "japan", "") else None,
        )
        return {
            "id": src["id"],
            "click_url": click,
            "image_url": "",
            "pixel_url": "",
            "label": src[f"label_{suffix}"],
            "desc": src[f"desc_{suffix}"],
            "alt": src[f"alt_{suffix}"],
            "partners_url": click,
        }
    if banner_id == "amazon_golf":
        return {
            "id": src["id"],
            "click_url": src["click_url"],
            "image_url": "",
            "pixel_url": "",
            "label": src[f"label_{suffix}"],
            "desc": src[f"desc_{suffix}"],
            "alt": src[f"alt_{suffix}"],
        }
    return {
        "id": src["id"],
        "click_url": f"/go/{banner_id}",
        "image_url": "",
        "pixel_url": "",
        "label": src[f"label_{suffix}"],
        "desc": src[f"desc_{suffix}"],
        "alt": src[f"alt_{suffix}"],
    }


def a8_banners_context(
    *,
    lang: str = "en",
    lat: float | None = None,
    lng: float | None = None,
    country: str | None = None,
) -> dict[str, Any]:
    if not _enabled():
        return {"show_a8_banners": False, "a8_banners": []}
    code = (lang or "en").lower()
    kw = {"lang": lang, "lat": lat, "lng": lng, "country": country}
    banners = [
        _copy("agoda", **kw),
        _copy("amazon_golf", lang=lang),
    ]
    if code == "ko":
        banners.append(_copy("rakuten_esim", lang=lang))
    titles = {
        "ko": "골프 여행 제휴",
        "ja": "ゴルフ提携（宿泊・用品）",
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
