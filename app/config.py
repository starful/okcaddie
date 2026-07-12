"""Site-wide constants and configuration."""

from __future__ import annotations

import os

SITE_URL = os.environ.get("SITE_URL", "https://okcaddie.net").rstrip("/")
GCS_ASSET_PREFIX = "okcaddie"
GOOGLE_MAPS_JS_API_KEY = os.environ.get("GOOGLE_MAPS_JS_API_KEY", "").strip()
SUPPORTED_LANGS = frozenset({"en", "ko"})
FAMILY_SITE_ID = "okcaddie"

FEATURED_COURSE_BASE_IDS = (
    "pgm_golf_resort_okinawa",
    "hirono_golf_club",
    "yokohama_country_club",
    "shimonoseki_golf_club",
    "natsudomari_golf_links",
    "hakone_country_club",
    "abc_golf_club",
    "eniwa_country_club",
    "totsuka_country_club",
    "kotohira_golf_club",
)
FEATURED_COURSE_BASE_IDS_SET = frozenset(FEATURED_COURSE_BASE_IDS)

# Retired guides: 301 to guide hub (or a successor) instead of soft-404.
RETIRED_GUIDE_REDIRECTS = {
    "guide_seed_001": "/guide",
    "guide_seed_002": "/guide",
    "guide_seed_003": "/guide",
    "guide_expand_001": "/guide",
    "guide_expand_002": "/guide",
    "guide_expand_003": "/guide",
    "guide_expand_004": "/guide",
    "guide_expand_005": "/guide",
    "guide_expand_006": "/guide",
    "guide_expand_007": "/guide",
    "guide_expand_008": "/guide",
    "guide_expand_009": "/guide",
    "best-souvenirs-proshop": "/guide",
    "chipping-and-putting-practice": "/guide",
    "golf-insurance-for-travelers": "/guide",
    "kanto-vs-kansai-golf": "/guide",
    "rental-clubs-japan": "/guide",
    "self-play-vs-caddy": "/guide",
    "spring-cherry-blossom-golf": "/guide",
    "stay-and-play-karuizawa": "/guide",
    "trash-and-smoking-rules": "/guide",
}

GUIDE_IMAGES = [
    "https://images.unsplash.com/photo-1587174486073-ae5e5cff23aa?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1535131749006-b7f58c99034b?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1591491640784-3232eb748d4b?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1563299796-17596ed6b017?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1590602847861-f357a9332bbc?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1586227740560-8cf2732c1531?auto=format&fit=crop&w=1200",
]

AREA_MAP = {
    "北海道": 1,
    "青森": 2,
    "岩手": 3,
    "宮城": 4,
    "秋田": 5,
    "山形": 6,
    "福島": 7,
    "茨城": 8,
    "栃木": 9,
    "群馬": 10,
    "埼玉": 11,
    "千葉": 12,
    "東京": 13,
    "神奈川": 14,
    "新潟": 15,
    "富山": 16,
    "石川": 17,
    "福井": 18,
    "山梨": 19,
    "長野": 20,
    "岐阜": 21,
    "静岡": 22,
    "愛知": 23,
    "三重": 24,
    "滋賀": 25,
    "京都": 26,
    "大阪": 27,
    "兵庫": 28,
    "奈良": 29,
    "和歌山": 30,
    "鳥取": 31,
    "島根": 32,
    "岡山": 33,
    "広島": 34,
    "山口": 35,
    "徳島": 36,
    "香川": 37,
    "愛媛": 38,
    "高知": 39,
    "福岡": 40,
    "佐賀": 41,
    "長崎": 42,
    "熊本": 43,
    "大分": 44,
    "宮崎": 45,
    "鹿児島": 46,
    "沖縄": 47,
}
PREFECTURE_KEYWORDS = tuple(AREA_MAP.keys())

GUIDE_RELATED_COURSES = {
    "okinawa-ocean-golf_en": [
        "pgm_golf_resort_okinawa",
        "southern_links_golf_club",
        "phoenix_country_club",
    ],
    "okinawa-ocean-golf_ko": [
        "pgm_golf_resort_okinawa",
        "southern_links_golf_club",
        "phoenix_country_club",
    ],
    "golf-etiquette-japan_en": [
        "yokohama_country_club",
        "tokyo_golf_club",
        "abc_golf_club",
    ],
    "golf-etiquette-japan_ko": [
        "yokohama_country_club",
        "tokyo_golf_club",
        "abc_golf_club",
    ],
    "autumn-leaves-golf_en": [
        "karuizawa_72_golf_east",
        "nasu_kogen_golf_club",
        "zao_country_club",
    ],
    "autumn-leaves-golf_ko": [
        "karuizawa_72_golf_east",
        "nasu_kogen_golf_club",
        "zao_country_club",
    ],
    "mt-fuji-view-golf_en": [
        "hakone_country_club",
        "fuji_country_club",
        "hiratsuka_fuji_golf_course",
    ],
    "mt-fuji-view-golf_ko": [
        "hakone_country_club",
        "fuji_country_club",
        "hiratsuka_fuji_golf_course",
    ],
    "onsen-after-golf_en": [
        "hakone_country_club",
        "beppu_golf_club",
        "nasu_kogen_golf_club",
    ],
    "onsen-after-golf_ko": [
        "hakone_country_club",
        "beppu_golf_club",
        "nasu_kogen_golf_club",
    ],
    "hokkaido-summer-golf_en": [
        "eniwa_country_club",
        "sapporo_golf_club_wattsu_course",
        "nishinasuno_country_club",
    ],
    "hokkaido-summer-golf_ko": [
        "eniwa_country_club",
        "sapporo_golf_club_wattsu_course",
        "nishinasuno_country_club",
    ],
    "booking-tips-japan_en": [
        "pgm_golf_resort_okinawa",
        "yokohama_country_club",
        "abc_golf_club",
    ],
    "booking-tips-japan_ko": [
        "pgm_golf_resort_okinawa",
        "yokohama_country_club",
        "abc_golf_club",
    ],
    "value-for-money-golf_en": ["abc_golf_club", "totsuka_country_club", "kotohira_golf_club"],
    "value-for-money-golf_ko": ["abc_golf_club", "totsuka_country_club", "kotohira_golf_club"],
    "women-friendly-golf_en": [
        "yokohama_country_club",
        "camellia_hills_country_club",
        "phoenix_country_club",
    ],
    "women-friendly-golf_ko": [
        "yokohama_country_club",
        "camellia_hills_country_club",
        "phoenix_country_club",
    ],
}
