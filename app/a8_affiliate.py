"""A8.net affiliate banners for OK Caddie.

Agoda uses Agoda Partners (CID) links, not A8.
"""

from __future__ import annotations

import os
from typing import Any

try:
    from agoda_partners import partner_search_url, url_for_location
except ImportError:
    from .agoda_partners import partner_search_url, url_for_location

_BANNERS: dict[str, dict[str, str]] = {
    "agoda": {
        "id": "agoda",
        # click_url filled at copy-time via Agoda Partners
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
    "jalan_golf": {
        "id": "jalan_golf",
        "click_url": "https://px.a8.net/svt/ejp?a8mat=4BCE3P+1OQCCA+36SI+5YRHE",
        "image_url": "",
        "pixel_url": "https://www16.a8.net/0.gif?a8mat=4BCE3P+1OQCCA+36SI+5YRHE",
        "label_en": "Jalan Golf — course search & booking",
        "label_ko": "じゃらんゴルフ — 골프장 검색·예약",
        "label_ja": "じゃらんゴルフ — ゴルフ場検索・予約",
        "desc_en": "Search and book Japan golf courses.",
        "desc_ko": "일본 골프장 검색·예약.",
        "desc_ja": "日本のゴルフ場を検索・予約。",
        "alt_en": "Jalan Golf — affiliate",
        "alt_ko": "じゃらんゴルフ — 제휴",
        "alt_ja": "じゃらんゴルフ — アフィリエイト",
    },
    "fairway_golf": {
        "id": "fairway_golf",
        "click_url": "https://px.a8.net/svt/ejp?a8mat=4BCE3P+1PBRY2+28NM+5YJRM",
        "image_url": "",
        "pixel_url": "https://www19.a8.net/0.gif?a8mat=4BCE3P+1PBRY2+28NM+5YJRM",
        "label_en": "Fairway Golf — clubs from the USA",
        "label_ko": "Fairway Golf — 미국직송 클럽",
        "label_ja": "フェアウェイゴルフ — USA直送クラブ",
        "desc_en": "Shop golf clubs shipped from the USA.",
        "desc_ko": "미국직송 골프 클럽.",
        "desc_ja": "USAからゴルフクラブを直送。",
        "alt_en": "Fairway Golf — affiliate",
        "alt_ko": "Fairway Golf — 제휴",
        "alt_ja": "フェアウェイゴルフ — アフィリエイト",
    },
    "alpen_golf5": {
        "id": "alpen_golf5",
        "click_url": "https://px.a8.net/svt/ejp?a8mat=4BCE3P+1X2ET6+3OSK+5ZMCI",
        "image_url": "",
        "pixel_url": "https://www10.a8.net/0.gif?a8mat=4BCE3P+1X2ET6+3OSK+5ZMCI",
        "label_en": "Golf5 / Alpen — official store",
        "label_ko": "Golf5·Alpen — 공식 스토어",
        "label_ja": "ゴルフ５・アルペン — 公式ストア",
        "desc_en": "Golf gear from Sports Depo / Golf5 / Alpen.",
        "desc_ko": "스포츠데포·Golf5·알펜 골프용품.",
        "desc_ja": "スポーツデポ・ゴルフ５・アルペンのゴルフ用品。",
        "alt_en": "Golf5 / Alpen — affiliate",
        "alt_ko": "Golf5·Alpen — 제휴",
        "alt_ja": "ゴルフ５・アルペン — アフィリエイト",
    },
    "victoria_golf": {
        "id": "victoria_golf",
        "click_url": "https://px.a8.net/svt/ejp?a8mat=4BCE3P+1LR6BE+4ABU+BZO4I",
        "image_url": "",
        "pixel_url": "https://www15.a8.net/0.gif?a8mat=4BCE3P+1LR6BE+4ABU+BZO4I",
        "label_en": "Victoria Golf — gear shop",
        "label_ko": "Victoria Golf — 골프용품",
        "label_ja": "ヴィクトリアゴルフ — ゴルフ用品",
        "desc_en": "Shop golf equipment online.",
        "desc_ko": "골프용품 온라인몰.",
        "desc_ja": "ゴルフ用品の通販。",
        "alt_en": "Victoria Golf — affiliate",
        "alt_ko": "Victoria Golf — 제휴",
        "alt_ja": "ヴィクトリアゴルフ — アフィリエイト",
    },
    "rizap_golf": {
        "id": "rizap_golf",
        "click_url": "https://px.a8.net/svt/ejp?a8mat=4BCIRR+6Y26PM+CW6+BF23HE",
        "image_url": "",
        "pixel_url": "https://www18.a8.net/0.gif?a8mat=4BCIRR+6Y26PM+CW6+BF23HE",
        "label_en": "RIZAP Golf — score-focused school",
        "label_ko": "RIZAP 골프 — 스코어 특화 스쿨",
        "label_ja": "RIZAP GOLF — スコア特化スクール",
        "desc_en": "Book a golf school consultation in Japan.",
        "desc_ko": "일본 골프 스쿨 상담·내점.",
        "desc_ja": "スコアアップのゴルフスクール。無料カウンセリング・来店。",
        "alt_en": "RIZAP Golf — affiliate",
        "alt_ko": "RIZAP 골프 — 제휴",
        "alt_ja": "RIZAP GOLF — アフィリエイト",
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
    key = banner_id.upper()
    if banner_id == "agoda":
        click = url_for_location(
            lang=lang,
            lat=lat,
            lng=lng,
            country=country,
            default_city=5085 if (country or "jp").lower() in ("jp", "japan", "") else None,
        )
        # Always use Partners URL (with city) — /go/agoda without city landed on
        # empty worldwide search and Agoda's error UI.
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
    return {
        "id": src["id"],
        "click_url": f"/go/{banner_id}",
        "image_url": os.getenv(f"A8_{key}_BANNER_URL", src["image_url"]),
        "pixel_url": os.getenv(f"A8_{key}_PIXEL_URL", src["pixel_url"]),
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
    # Keep the partner box scannable: booking + gear + lodging.
    # RIZAP (lesson/school) is JA-only — not for KO/EN trip booking intent.
    kw = {"lang": lang, "lat": lat, "lng": lng, "country": country}
    banners = [
        _copy("jalan_golf", lang=lang),
        _copy("fairway_golf", lang=lang),
        _copy("agoda", **kw),
        _copy("rakuten_travel", lang=lang),
    ]
    if code == "ko":
        banners.append(_copy("rakuten_esim", lang=lang))
    if code == "ja":
        banners.append(_copy("rizap_golf", lang=lang))
    titles = {
        "ko": "골프 여행 제휴",
        "ja": "ゴルフ提携（予約・用品・スクール）",
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
