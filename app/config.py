"""Site-wide constants and configuration."""

from __future__ import annotations

import os

SITE_URL = os.environ.get("SITE_URL", "https://okcaddie.net").rstrip("/")
GCS_ASSET_PREFIX = "okcaddie"
GOOGLE_MAPS_JS_API_KEY = os.environ.get("GOOGLE_MAPS_JS_API_KEY", "").strip()
SUPPORTED_LANGS = frozenset({"en", "ko", "ja"})
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

# Home pins existing guides (no new /region URLs).
HOME_REGION_GUIDE_IDS = (
    "hokkaido-summer-golf",
    "tokyo-near-golf",
    "mt-fuji-view-golf",
    "kansai-golf-weekend",
    "kyushu-golf-circuit",
    "okinawa-ocean-golf",
)
HOME_PURPOSE_GUIDE_IDS = (
    "value-for-money-golf",
    "onsen-after-golf",
    "korean-friendly-courses",
    "best-winter-golf",
)

# Japanese catalog names for Rakuten GORA search_c_name.
# EN/KO SEO titles return zero courses — only these strings (or a JP title / gora_name).
GORA_SEARCH_NAMES: dict[str, str] = {
    "pgm_golf_resort_okinawa": "PGMゴルフリゾート沖縄",
    "ocean_castle_golf": "オーシャンキャッスルカントリークラブ",
    "natsudomari_golf_links": "夏泊ゴルフリンクス",
    "abc_golf_club": "ABCゴルフ倶楽部",
    "eniwa_country_club": "恵庭カントリー倶楽部",
    "totsuka_country_club": "戸塚カントリー倶楽部",
    "kotohira_golf_club": "琴平カントリー倶楽部",
    "shimonoseki_golf_club": "下関ゴルフ倶楽部",
    "phoenix_seagaia_resort": "フェニックスシーガイア",
    "karuizawa_72_golf_east": "軽井沢72",
    "southern_links": "サザンリンクスゴルフクラブ",
    "southern_links_golf_club": "サザンリンクスゴルフクラブ",
    "kanucha_golf_course": "カヌチャゴルフコース",
    "pgm_ishioka_golf_club": "PGM石岡ゴルフクラブ",
    "shishido_hills_country_club": "宍戸ヒルズカントリークラブ",
    "oarai_golf_club": "大洗ゴルフ倶楽部",
    "ibaraki_golf_club": "茨城ゴルフ倶楽部",
    "chiran_country_club": "知覧カントリークラブ",
    "chukyo_golf_club": "中京ゴルフ倶楽部",
    "satsuma_resort_golf_club": "薩摩リゾートゴルフ倶楽部",
    "mie_kokusai_golf_club": "三重国際ゴルフクラブ",
    "abiko_golf_club": "我孫子ゴルフ倶楽部",
    "wakagi_golf_club": "若木ゴルフ倶楽部",
    "nikko_country_club": "日光カントリークラブ",
    "kyoto_golf_club_kamigamo": "京都ゴルフ倶楽部",
    "hirono_golf_club": "廣野ゴルフ倶楽部",
    "yokohama_country_club": "横浜カントリークラブ",
    "hakone_country_club": "箱根カントリー倶楽部",
    "tokyo_golf_club": "東京ゴルフ倶楽部",
    "kasumigaseki_country_club": "霞ヶ関カンツリー倶楽部",
    "naruo_golf_club": "鳴尾ゴルフ倶楽部",
    "kawana_hotel_golf_course_fuji_course": "川奈ホテルゴルフコース",
    "sagamihara_golf_club": "相模原ゴルフクラブ",
    "fujizakura_country_club": "富士桜カントリー倶楽部",
    "camellia_hills_country_club": "カメリアヒルズカントリークラブ",
    "keya_golf_club": "芥屋ゴルフ倶楽部",
    "koganei_golf_club": "小金井カントリー倶楽部",
    "musashi_country_club_sasai": "武蔵カントリークラブ",
    "nidom_classic_course": "ニドムクラシックコース",
    "okinawa_country_club": "沖縄カントリークラブ",
    "sapporo_golf_club_wattsu_course": "札幌ゴルフ倶楽部",
    "takarazuka_golf_club": "宝塚ゴルフ倶楽部",
    "aso_resort_grandvrio": "阿蘇リゾートグランヴィリオ",
    "karuizawa_asama_golf_course": "軽井沢浅間ゴルフコース",
    "narita_golf_club": "成田ゴルフクラブ",
    "nasu_golf_club": "那須ゴルフ倶楽部",
    "nasu_kogen_golf_club": "那須高原カントリークラブ",
    "phoenix_country_club": "フェニックスカントリークラブ",
    "otaru_golf_club": "小樽カントリー倶楽部",
    "sapporo_country_club": "札幌カントリー倶楽部",
    "sendai_country_club": "仙台カントリークラブ",
    "zao_country_club": "蔵王カントリークラブ",
    "fuji_country_club": "富士カントリークラブ",
    "enoshima_golf_club": "江の島ゴルフクラブ",
    "hiratsuka_fuji_golf_course": "平塚富士ゴルフコース",
    "beppu_golf_club": "別府ゴルフ倶楽部",
    "nago_bay_golf_course": "名護湾ゴルフコース",
    "ryukyu_golf_club": "琉球ゴルフ倶楽部",
    "taiheiyo_club_gotemba_course": "太平洋クラブ御殿場",
    "the_windsor_golf_course": "ザ・ウィンザーホテル洞爺",
    "hokkaido_classic_golf_club": "北海道クラシックゴルフクラブ",
    "appi_kogen_golf_club": "安比高原ゴルフクラブ",
    "ashinoko_country_club": "芦ノ湖カントリークラブ",
    "katayamazu_golf_club": "片山津ゴルフ倶楽部",
    "fuchu_country_club": "府中カントリークラブ",
    "nishinomiya_country_club": "西宮カントリー倶楽部",
}

# Verified Rakuten GORA Japan course IDs (public / bookable on GORA).
# Deep-link to calendar instead of prefecture keyword search.
GORA_COURSE_IDS: dict[str, str] = {
    "pgm_golf_resort_okinawa": "470006",
    "ocean_castle_golf": "520083",
    "abc_golf_club": "280028",
    "eniwa_country_club": "10015",
    "natsudomari_golf_links": "20008",
    "totsuka_country_club": "140032",
    "kanucha_golf_course": "470007",
    "pgm_ishioka_golf_club": "80007",
    "karuizawa_72_golf_east": "200015",
    "kotohira_golf_club": "370005",
    "beppu_golf_club": "440020",
    "phoenix_seagaia_resort": "450012",
    "phoenix_country_club": "450012",
    "southern_links": "470011",
    "southern_links_golf_club": "470011",
    "the_southern_links_resort": "470011",
    "aso_resort_grandvrio": "430006",
    "oarai_golf_club": "80019",
    "wakagi_golf_club": "410016",
    "abiko_golf_club": "120005",
    "shishido_hills_country_club": "80057",
    "chiran_country_club": "460028",
    "camellia_hills_country_club": "120029",
    "keya_golf_club": "400015",
    "appi_kogen_golf_club": "30001",
    "nidom_classic_course": "10112",
    "taiheiyo_club_gotemba_course": "220046",
}

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
    "golf-score-terms-japanese": "/guide/understanding-scorecards",
    "kanto-vs-kansai-golf": "/guide",
    "rental-clubs-japan": "/guide",
    "self-play-vs-caddy": "/guide",
    "spring-cherry-blossom-golf": "/guide/spring-sakura-golf",
    "stay-and-play-karuizawa": "/guide",
    "trash-and-smoking-rules": "/guide",
}

# Non-golf / removed course slugs: 301 instead of soft-404 (Search Console).
RETIRED_COURSE_REDIRECTS = {
    "kobe_harborland_cafe": "/courses",
    "kumamoto_castle_town_cafe": "/courses",
    "nagoya_sakae_espresso": "/courses",
    "sendai_ichibancho_latte": "/courses",
    "kamakura_komachi_drip": "/courses",
    "naha_kokusai_street_coffee": "/courses",
    "yokohama_minato_mirai_cafe": "/courses",
    "sample_golf_club": "/courses",
}

# Slugs omitted from sitemaps (test/demo content).
SITEMAP_EXCLUDED_COURSE_BASE_IDS = frozenset({"sample_golf_club"})

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

_GUIDE_RELATED_BASE: dict[str, tuple[str, ...]] = {
    "okinawa-ocean-golf": (
        "pgm_golf_resort_okinawa",
        "southern_links_golf_club",
        "kanucha_golf_course",
    ),
    "golf-etiquette-japan": ("yokohama_country_club", "tokyo_golf_club", "abc_golf_club"),
    "autumn-leaves-golf": ("karuizawa_72_golf_east", "nasu_kogen_golf_club", "zao_country_club"),
    "mt-fuji-view-golf": (
        "hakone_country_club",
        "fuji_country_club",
        "hiratsuka_fuji_golf_course",
        "kawana_hotel_golf_course_fuji_course",
    ),
    "onsen-after-golf": (
        "hakone_country_club",
        "beppu_golf_club",
        "nasu_kogen_golf_club",
        "kawana_hotel_golf_course_fuji_course",
    ),
    "hokkaido-summer-golf": (
        "eniwa_country_club",
        "sapporo_golf_club_wattsu_course",
        "otaru_golf_club",
    ),
    "booking-tips-japan": ("pgm_golf_resort_okinawa", "yokohama_country_club", "abc_golf_club"),
    "value-for-money-golf": ("abc_golf_club", "totsuka_country_club", "kotohira_golf_club"),
    "women-friendly-golf": (
        "yokohama_country_club",
        "camellia_hills_country_club",
        "phoenix_country_club",
        "kawana_hotel_golf_course_fuji_course",
    ),
    "tokyo-near-golf": (
        "yokohama_country_club",
        "totsuka_country_club",
        "narita_golf_club",
        "kawana_hotel_golf_course_fuji_course",
    ),
    "kansai-golf-weekend": ("hirono_golf_club", "kyoto_golf_club_kamigamo", "abc_golf_club"),
    "kyushu-golf-circuit": (
        "beppu_golf_club",
        "satsuma_resort_golf_club",
        "phoenix_seagaia_resort",
    ),
    "korean-friendly-courses": ("pgm_golf_resort_okinawa", "beppu_golf_club", "abc_golf_club"),
    "best-winter-golf": ("beppu_golf_club", "satsuma_resort_golf_club", "pgm_golf_resort_okinawa"),
    "single-golfer-booking": (
        "pgm_golf_resort_okinawa",
        "abc_golf_club",
        "kawana_hotel_golf_course_fuji_course",
    ),
    "luxury-golf-experience": (
        "hirono_golf_club",
        "kawana_hotel_golf_course_fuji_course",
        "kasumigaseki_country_club",
    ),
}
GUIDE_RELATED_COURSES = {
    f"{gid}_{lang}": list(ids)
    for gid, ids in _GUIDE_RELATED_BASE.items()
    for lang in ("en", "ko", "ja")
}

# Course → guide base_ids (used on course detail "related guides").
_COURSE_RELATED_GUIDES_BASE: dict[str, tuple[str, ...]] = {
    "kawana_hotel_golf_course_fuji_course": (
        "tokyo-near-golf",
        "onsen-after-golf",
        "luxury-golf-experience",
        "single-golfer-booking",
    ),
    "hirono_golf_club": ("kansai-golf-weekend", "luxury-golf-experience", "booking-tips-japan"),
    "pgm_golf_resort_okinawa": (
        "okinawa-ocean-golf",
        "booking-tips-japan",
        "korean-friendly-courses",
    ),
}
COURSE_RELATED_GUIDES = dict(_COURSE_RELATED_GUIDES_BASE)
