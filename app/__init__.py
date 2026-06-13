from flask import Flask, jsonify, render_template, abort, send_from_directory, redirect, request, make_response
from flask_compress import Compress
import json
import os
import frontmatter
import markdown
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

app = Flask(__name__)
Compress(app)

try:
    from .reactions import reactions_bp
except ImportError:
    from reactions import reactions_bp

app.register_blueprint(reactions_bp)

SITE_URL = os.environ.get("SITE_URL", "https://okcaddie.net").rstrip("/")

# ==========================================
# ⚙️ 경로 및 데이터 설정
# ==========================================
BASE_DIR = app.root_path
STATIC_DIR = os.path.join(BASE_DIR, 'static')
CONTENT_DIR = os.path.join(BASE_DIR, 'content')
GUIDE_DIR = os.path.join(CONTENT_DIR, 'guides')
DATA_FILE = os.path.join(STATIC_DIR, 'json', 'courses_data.json')

# [고화질 골프 이미지 20개] 확실히 살아있는 링크 리스트
GUIDE_IMAGES = [
    "https://images.unsplash.com/photo-1587174486073-ae5e5cff23aa?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1535131749006-b7f58c99034b?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1591491640784-3232eb748d4b?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1563299796-17596ed6b017?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1590602847861-f357a9332bbc?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1586227740560-8cf2732c1531?auto=format&fit=crop&w=1200"
]

# 일본 도도부현별 라쿠텐 고라 지역 코드 매핑 (전체 47개주)
AREA_MAP = {
    '北海道': 1, '青森': 2, '岩手': 3, '宮城': 4, '秋田': 5, '山形': 6, '福島': 7,
    '茨城': 8, '栃木': 9, '群馬': 10, '埼玉': 11, '千葉': 12, '東京': 13, '神奈川': 14,
    '新潟': 15, '富山': 16, '石川': 17, '福井': 18, '山梨': 19, '長野': 20, '岐阜': 21,
    '静岡': 22, '愛知': 23, '三重': 24, '滋賀': 25, '京都': 26, '大阪': 27, '兵庫': 28,
    '奈良': 29, '和歌山': 30, '鳥取': 31, '島根': 32, '岡山': 33, '広島': 34, '山口': 35,
    '徳島': 36, '香川': 37, '愛媛': 38, '高知': 39, '福岡': 40, '佐賀': 41, '長崎': 42,
    '熊本': 43, '大分': 44, '宮崎': 45, '鹿児島': 46, '沖縄': 47
}
PREFECTURE_KEYWORDS = tuple(AREA_MAP.keys())

CACHED_DATA = {"courses": []}
CACHED_GUIDES = []
GOOGLE_MAPS_JS_API_KEY = os.environ.get("GOOGLE_MAPS_JS_API_KEY", "").strip()
SUPPORTED_LANGS = {"en", "ko"}

# GSC priority courses: homepage spotlight, crawl-nav order, sitemap priority (P1)
FEATURED_COURSE_BASE_IDS = [
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
]

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
    "women-friendly-golf_en": ["yokohama_country_club", "camellia_hills_country_club", "phoenix_country_club"],
    "women-friendly-golf_ko": ["yokohama_country_club", "camellia_hills_country_club", "phoenix_country_club"],
}

# ==========================================
# 🛠️ 유틸리티 및 데이터 로드 함수
# ==========================================

def get_meta_fallback(text, key):
    """YAML 파싱 실패 시 정규식으로 데이터를 강제 추출하는 백업 함수"""
    pattern = rf'{key}:\s*["\']?(.*?)["\']?\n'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else ""

# 레거시 보일러플레이트 타이틀을 SERP/모바일 친화적 형태로 정규화
_LANG_SUFFIX_RE = re.compile(r'\s*\(\s*(?:en|ko|EN|KO)\s*\)\s*$')
_REVIEW_BOILERPLATE_RE = re.compile(
    r'^\s*The\s+Definitive\s+Guide\s+to\s+(?P<name>.+?)\s*:\s*An\s+Expert\s+Review\b.*$',
    re.IGNORECASE,
)
# 한·영 모두에서 흔하게 등장하는 "AI 보일러플레이트" 구문. 어디 있든 제거한 뒤 트리밍한다.
_BOILERPLATE_PHRASES = (
    "The Definitive Guide to ",
    ": An Expert Review",
    "An Expert Review",
    " Masterpiece Review",
    "마스터피스 리뷰",
    "마스터 리뷰",
    "마스터 가이드",
    "완벽 가이드",
    "전문가 리뷰",
    "심층 분석",
    "20년 경력 베테랑 캐디의",
)

def humanize_title(title):
    """타이틀에서 라벨·보일러플레이트를 정리해 SERP에 어울리는 형태로 만든다."""
    if not title:
        return ""
    s = _LANG_SUFFIX_RE.sub('', str(title).strip())
    m = _REVIEW_BOILERPLATE_RE.match(s)
    if m:
        return m.group('name').strip()

    cleaned = s
    for phrase in _BOILERPLATE_PHRASES:
        cleaned = cleaned.replace(phrase, "")
    # 콜론 뒤가 보일러플레이트 잔재인 경우가 많으므로, prefix가 충분히 길면 잘라낸다.
    for sep in (":", "：", " - ", " — "):
        if sep in cleaned:
            prefix = cleaned.split(sep, 1)[0].strip()
            if len(prefix) >= 4:
                cleaned = prefix
                break
    cleaned = cleaned.strip(" -—|·•")
    # 여전히 너무 길고 ` | ` 구분자가 있으면 첫 segment만 취한다.
    if len(cleaned) > 70 and " | " in cleaned:
        first = cleaned.split(" | ")[0].strip()
        if len(first) >= 5:
            cleaned = first
    return cleaned or s

def short_summary(summary, limit=155):
    """SERP description 길이 제한 (모바일 우선)."""
    if not summary:
        return ""
    s = str(summary).strip()
    if len(s) <= limit:
        return s
    return s[: limit - 1].rstrip() + "…"

# AI 자기점검 메타텍스트(보일러플레이트)가 본문 끝에 박힌 케이스를 런타임에서 잘라낸다.
_RUNTIME_SELFCHECK_PATTERNS = [
    re.compile(r"^\s*\*{0,2}\s*\(?\s*Total\s+character", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*\*{0,2}\s*\(?\s*Character\s+count\s+check", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*Markdown\s+formatting\s+with", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*YAML\s+frontmatter\s+is\s+correctly", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*The\s+tone\s+is\s+professional,?\s+technical", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*The\s+generated\s+(?:Korean|English)\s+content\s+is\s+~?\s*\d", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*\d+\.\s+\*\*(?:Character\s+Count|Tone|Language|YAML\s+Frontmatter)\b", re.IGNORECASE | re.MULTILINE),
]

def strip_llm_selfcheck(body):
    """본문에서 LLM 자기점검 푸터가 나타나는 첫 위치부터 끝까지 잘라낸다."""
    if not body:
        return body
    earliest = len(body)
    for pat in _RUNTIME_SELFCHECK_PATTERNS:
        m = pat.search(body)
        if m and m.start() < earliest:
            earliest = m.start()
    if earliest < len(body):
        return body[:earliest].rstrip()
    return body

# AI summary 자기홍보 문구 ("9,000자에 달하는 종합 마스터 가이드", "comprehensive 9,000-character master guide" 등)
_PROMO_SUMMARY_RE = re.compile(
    r'\d{1,3},?\d{3}\s*(?:자|character|-?\s*character)',
    re.IGNORECASE,
)

def clean_summary(summary, title='', lang='en'):
    """AI 보일러플레이트 summary 를 SERP-친화적 형태로 대체한다."""
    if not summary:
        return summary
    s = str(summary).strip()
    if not _PROMO_SUMMARY_RE.search(s):
        return s
    name = humanize_title(title) if title else ""
    if lang == 'ko':
        return f"{name} 그린피, 예약 정보, 코스 공략, 접근성, 베스트 시즌까지 한 페이지에 정리한 가이드.".strip()
    return f"{name} guide: green fees, booking paths, layout strategy, access tips, and best seasons.".strip()

def split_localized_id(item_id):
    if item_id.endswith("_ko"):
        return item_id[:-3], "ko"
    if item_id.endswith("_en"):
        return item_id[:-3], "en"
    return item_id, None

def extract_prefecture(text):
    if not text:
        return ""
    for pref in PREFECTURE_KEYWORDS:
        if pref in text:
            return pref
    return ""

def resolve_course_id(base_id, lang):
    course_id = f"{base_id}_{lang}"
    if os.path.exists(os.path.join(CONTENT_DIR, f"{course_id}.md")):
        return course_id
    fallback_id = f"{base_id}_en"
    if os.path.exists(os.path.join(CONTENT_DIR, f"{fallback_id}.md")):
        return fallback_id
    return None

def resolve_guide_id(base_id, lang):
    guide_id = f"{base_id}_{lang}"
    if os.path.exists(os.path.join(GUIDE_DIR, f"{guide_id}.md")):
        return guide_id
    fallback_id = f"{base_id}_en"
    if os.path.exists(os.path.join(GUIDE_DIR, f"{fallback_id}.md")):
        return fallback_id
    return None


def _truncate_text(value, max_len):
    text = " ".join(str(value or "").split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _course_href(base_id, lang):
    return f"/course/{base_id}" + ("?lang=ko" if lang == "ko" else "")


def _courses_by_base_lang():
    index = {}
    for c in CACHED_DATA.get("courses", []):
        bid = c.get("base_id") or split_localized_id(c.get("id", ""))[0]
        lang = c.get("lang", "en")
        index[(bid, lang)] = c
    return index


def _course_cards(base_ids, lang="en", limit=None):
    """Lightweight cards for templates (featured, guide related, crawl nav)."""
    by_bl = _courses_by_base_lang()
    cards = []
    for bid in base_ids:
        c = by_bl.get((bid, lang)) or by_bl.get((bid, "en"))
        if not c:
            continue
        title = humanize_title(c.get("title", "")) or bid
        cards.append(
            {
                "base_id": bid,
                "lang": lang,
                "link": _course_href(bid, lang),
                "title": title,
                "short_title": _truncate_text(title, 72),
                "address": c.get("address", ""),
                "thumbnail": c.get("thumbnail", ""),
                "summary": short_summary(
                    clean_summary(c.get("summary", ""), title, lang), 110
                ),
            }
        )
        if limit and len(cards) >= limit:
            break
    return cards


def _crawl_course_links(limit=60, lang="en"):
    """SSR link list for crawlers: GSC priority courses first, then newest."""
    by_bl = _courses_by_base_lang()
    ordered_bases = []
    for bid in FEATURED_COURSE_BASE_IDS:
        if (bid, lang) in by_bl or (bid, "en") in by_bl:
            ordered_bases.append(bid)
    newest = sorted(
        [c for c in CACHED_DATA.get("courses", []) if c.get("lang") == lang],
        key=lambda x: str(x.get("published", "")),
        reverse=True,
    )
    for c in newest:
        bid = c.get("base_id") or split_localized_id(c.get("id", ""))[0]
        if bid not in ordered_bases:
            ordered_bases.append(bid)
    links = []
    for bid in ordered_bases[:limit]:
        card = _course_cards([bid], lang=lang, limit=1)
        if not card:
            continue
        links.append({"link": card[0]["link"], "label": card[0]["short_title"]})
    return links


def _attach_seo_fields(post, page_kind="course"):
    """SERP-friendly title/description; honors frontmatter seo_title / seo_description."""
    title = str(post.get("title", "")).strip()
    summary = str(post.get("summary", "")).strip()
    lang = str(post.get("lang", "en") or "en").lower()
    is_course = page_kind == "course"

    override_title = str(post.get("seo_title", "") or "").strip()
    override_desc = str(post.get("seo_description", "") or "").strip()

    if lang == "ko":
        hook = "그린피·예약·코스 가이드" if is_course else "일본 골프 여행 가이드"
        tail = (
            " OKCaddie에서 지도, 그린피, 라쿠텐 고라 예약 링크를 확인하세요."
            if is_course
            else " OKCaddie에서 핵심 팁과 코스 링크를 골라 일정에 넣으세요."
        )
        default_title = (
            _truncate_text(f"{title} | {hook} | OKCaddie", 60)
            if title
            else "일본 골프 가이드 | OKCaddie"
        )
    else:
        hook = "green fees, tee times & booking" if is_course else "Japan golf travel guide"
        tail = (
            " Green fees, Rakuten GORA booking, map & course tips on OKCaddie."
            if is_course
            else " Practical tips and course links for your Japan golf trip on OKCaddie."
        )
        default_title = (
            _truncate_text(f"{title} | {hook} | OKCaddie", 60)
            if title
            else "Japan Golf Guide | OKCaddie"
        )

    post["seo_title"] = _truncate_text(override_title, 60) if override_title else default_title
    if override_desc:
        post["seo_description"] = _truncate_text(override_desc, 160)
    else:
        core = (summary or title).strip()
        post["seo_description"] = _truncate_text(f"{core}{tail}", 155)
    return post


def _detail_trust_copy(lang):
    if str(lang or "en").lower() == "ko":
        return (
            "본 글은 여행 계획용 에디토리얼 콘텐츠입니다. 공식 클럽 사이트가 아니므로 그린피·영업·예약 조건은 방문 전 라쿠텐 고라 또는 클럽에 반드시 확인하세요.",
            "상단 이미지는 이해를 돕기 위한 예시이며, 실제 코스 전경·시설과 다를 수 있습니다.",
        )
    return (
        "Editorial trip-planning content—not the club's official site. Confirm green fees, access, and tee times on Rakuten GORA or with the club before you book.",
        "Lead images are illustrative; actual course conditions and facilities may differ.",
    )


def _enrich_course_detail_post(post):
    lang = str(post.get("lang") or "en")
    if not post.get("editorial_note") or not post.get("illustration_note"):
        ed, ill = _detail_trust_copy(lang)
        if not post.get("editorial_note"):
            post["editorial_note"] = ed
        if not post.get("illustration_note"):
            post["illustration_note"] = ill


def _safe_iso_date(value, fallback):
    if not value:
        return fallback
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return fallback


def _file_lastmod(path, fallback):
    if not os.path.exists(path):
        return fallback
    ts = os.path.getmtime(path)
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def _xml_url_block(loc, lastmod, changefreq, priority, alternates=None):
    lines = ["  <url>", f"    <loc>{escape(loc)}</loc>"]
    if alternates:
        for lang_code, href in alternates:
            lines.append(
                f'    <xhtml:link rel="alternate" hreflang="{escape(lang_code)}" href="{escape(href)}" />'
            )
    lines.extend(
        [
            f"    <lastmod>{escape(lastmod)}</lastmod>",
            f"    <changefreq>{changefreq}</changefreq>",
            f"    <priority>{priority}</priority>",
            "  </url>",
        ]
    )
    return lines


def _course_sitemap_entries(now_iso):
    grouped = {}
    for c in CACHED_DATA.get("courses", []):
        bid = c.get("base_id") or split_localized_id(c.get("id", ""))[0]
        lang = c.get("lang", "en")
        grouped[(bid, lang)] = c

    entries = []
    seen_paths = set()
    for c in CACHED_DATA.get("courses", []):
        bid = c.get("base_id") or split_localized_id(c.get("id", ""))[0]
        lang = c.get("lang", "en")
        path = _course_href(bid, lang)
        if path in seen_paths:
            continue
        seen_paths.add(path)
        course_id = c.get("id") or f"{bid}_{lang}"
        md_path = os.path.join(CONTENT_DIR, f"{course_id}.md")
        fallback = _safe_iso_date(c.get("published"), now_iso)
        lastmod = _file_lastmod(md_path, fallback)
        priority = "0.85" if bid in FEATURED_COURSE_BASE_IDS else "0.7"
        alternates = []
        if (bid, "en") in grouped:
            alternates.append(("en", f"{SITE_URL}{_course_href(bid, 'en')}"))
        if (bid, "ko") in grouped:
            alternates.append(("ko", f"{SITE_URL}{_course_href(bid, 'ko')}"))
        xd = f"{SITE_URL}{_course_href(bid, 'en')}"
        alternates.append(("x-default", xd))
        entries.append(
            {
                "loc": f"{SITE_URL}{path}",
                "lastmod": lastmod,
                "changefreq": "weekly",
                "priority": priority,
                "alternates": alternates,
            }
        )
    return entries


def _guide_sitemap_entries(now_iso):
    entries = []
    for g in CACHED_GUIDES:
        base_id = g.get("base_id") or split_localized_id(g.get("id", ""))[0]
        lang = g.get("lang", "en")
        path = f"/guide/{base_id}" + ("?lang=ko" if lang == "ko" else "")
        guide_id = g.get("id") or f"{base_id}_{lang}"
        md_path = os.path.join(GUIDE_DIR, f"{guide_id}.md")
        fallback = _safe_iso_date(g.get("date"), now_iso)
        lastmod = _file_lastmod(md_path, fallback)
        alternates = []
        en_path = os.path.join(GUIDE_DIR, f"{base_id}_en.md")
        ko_path = os.path.join(GUIDE_DIR, f"{base_id}_ko.md")
        if os.path.exists(en_path):
            alternates.append(("en", f"{SITE_URL}/guide/{base_id}"))
        if os.path.exists(ko_path):
            alternates.append(("ko", f"{SITE_URL}/guide/{base_id}?lang=ko"))
        alternates.append(("x-default", f"{SITE_URL}/guide/{base_id}"))
        entries.append(
            {
                "loc": f"{SITE_URL}{path}",
                "lastmod": lastmod,
                "changefreq": "weekly",
                "priority": "0.9",
                "alternates": alternates,
            }
        )
    return entries


def _render_urlset(entries):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for e in entries:
        lines.extend(
            _xml_url_block(
                e["loc"],
                e["lastmod"],
                e["changefreq"],
                e["priority"],
                e.get("alternates"),
            )
        )
    lines.append("</urlset>")
    return "\n".join(lines)


def load_all_data():
    """서버 시작 시 메모리에 모든 마크다운 및 JSON 데이터를 로드"""
    global CACHED_DATA, CACHED_GUIDES
    
    # 1. 골프장 코스 JSON 데이터 로드
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                CACHED_DATA = json.load(f)
                print(f"✅ Course JSON loaded: {len(CACHED_DATA.get('courses', []))} items")
        except Exception as e:
            print(f"❌ Course Data error: {e}")
            CACHED_DATA = {"courses": []}

    # 2. AI 가이드 마크다운 로드 및 정제
    temp_guides = []
    if os.path.exists(GUIDE_DIR):
        files = sorted([f for f in os.listdir(GUIDE_DIR) if f.endswith('.md')], reverse=True)
        for filename in files:
            try:
                full_id = filename.replace('.md', '')
                if full_id.startswith('_') or '_' not in full_id:
                    continue

                with open(os.path.join(GUIDE_DIR, filename), 'r', encoding='utf-8') as f:
                    raw_text = f.read().strip()
                    # YAML 구분자 보정 (첫 줄에 --- 가 오도록 강제)
                    if '---' in raw_text:
                        raw_text = '---' + raw_text.split('---', 1)[1]
                    
                    post = frontmatter.loads(raw_text)
                    item = dict(post.metadata)
                    
                    base_id = full_id.rsplit('_', 1)[0]
                    # 파일명으로 언어 강제 분류 (en/ko)
                    detected_lang = 'ko' if full_id.endswith('_ko') else 'en'
                    
                    # 제목 및 요약문 로드 (누락 시 fallback 작동)
                    title = item.get('title') or get_meta_fallback(raw_text, 'title')
                    summary = item.get('summary') or get_meta_fallback(raw_text, 'summary')
                    
                    if not summary or 'lang:' in summary:
                        # 본문 첫 부분을 잘라서 요약문 생성
                        clean_body = re.sub(r'---.*?---', '', post.content, flags=re.DOTALL).strip()
                        summary = clean_body[:130].replace('\n', ' ') + '...'

                    title = humanize_title(title) or "Japan Golf Guide"

                    temp_guides.append({
                        'id': full_id,
                        'base_id': base_id,
                        'lang': detected_lang,
                        'title': title,
                        'summary': short_summary(clean_summary(summary, title, detected_lang), 200),
                        'date': str(item.get('date', '2026-04-12')),
                        'image': GUIDE_IMAGES[abs(hash(base_id) * 97) % len(GUIDE_IMAGES)]
                    })
            except Exception as e:
                print(f"❌ Guide load error ({filename}): {e}")
    
    CACHED_GUIDES = temp_guides
    print(f"✅ AI Guides loaded: {len(CACHED_GUIDES)} items")

# 초기 실행
load_all_data()


@app.context_processor
def inject_site_url():
    n_courses = len({c.get("base_id") or split_localized_id(c.get("id", ""))[0] for c in CACHED_DATA.get("courses", [])})
    return {"site_url": SITE_URL, "total_course_count": n_courses or len(CACHED_DATA.get("courses", []))}


# ==========================================
# 🔗 SEO: HTTPS / 영어 URL 정규화 (?lang=en 제거)
# ==========================================

@app.before_request
def seo_url_normalization():
    if request.method != 'GET':
        return None
    p = request.path
    if (
        p.startswith('/static/')
        or p.startswith('/api/')
        or p.startswith('/booking/')
        or p.startswith('/travel/')
    ):
        return None

    if request.headers.get('X-Forwarded-Proto', '').lower() == 'http':
        return redirect(request.url.replace('http://', 'https://', 1), code=301)

    args = request.args
    keys = set(args.keys())

    if p == '/' and keys == {'lang'} and args.get('lang') == 'en':
        return redirect('/', code=301)
    if p == '/guide' and keys == {'lang'} and args.get('lang') == 'en':
        return redirect('/guide', code=301)
    if p == '/about' and keys == {'lang'} and args.get('lang') == 'en':
        return redirect('/about', code=301)
    if p == '/privacy' and keys == {'lang'} and args.get('lang') == 'en':
        return redirect('/privacy', code=301)

    if p == '/courses':
        if keys == {'lang'} and args.get('lang') == 'en':
            return redirect('/courses', code=301)
        if keys == {'lang', 'page'} and args.get('lang') == 'en':
            pg = args.get('page') or '1'
            if pg == '1':
                return redirect('/courses', code=301)
            return redirect(f'/courses?page={pg}', code=301)

    if p.startswith('/course/') and len(p) > len('/course/'):
        if keys == {'lang'} and args.get('lang') == 'en':
            return redirect(p, code=301)
    if p.startswith('/guide/') and p != '/guide' and len(p) > len('/guide/'):
        if keys == {'lang'} and args.get('lang') == 'en':
            return redirect(p, code=301)

    return None

# ==========================================
# 🌐 라우팅 (Routing) - 사용자 페이지
# ==========================================

@app.route('/')
def index():
    """메인 페이지: 선택 언어에 맞는 가이드 하이라이트 노출"""
    lang = request.args.get('lang', 'en')
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    featured = [g for g in CACHED_GUIDES if g['lang'] == lang][:3]
    if not featured:
        featured = CACHED_GUIDES[:3]
    return render_template(
        'index.html',
        featured_guides=featured,
        featured_courses=_course_cards(FEATURED_COURSE_BASE_IDS, lang=lang),
        crawl_course_links=_crawl_course_links(limit=60, lang=lang),
        active_lang=lang,
        google_maps_js_api_key=GOOGLE_MAPS_JS_API_KEY,
    )

@app.route('/about')
@app.route('/about.html')
def about():
    """소개 페이지"""
    lang = request.args.get('lang', 'en')
    return render_template('about.html', active_lang=lang)

@app.route('/privacy')
@app.route('/privacy.html')
def privacy():
    """개인정보 처리방침 페이지"""
    lang = request.args.get('lang', 'en')
    return render_template('privacy.html', active_lang=lang)

@app.route('/api/courses')
def api_courses():
    """지도 및 리스트용 데이터 API: JS 호환을 위한 언어 속성 변조 포함"""
    lang = request.args.get('lang', 'en')
    filtered = []
    for c in CACHED_DATA.get('courses', []):
        if c.get('lang') == lang:
            temp = dict(c)
            temp['lang'] = 'en' # main.js가 en만 찾도록 고정되어 있어도 한국어 내용을 보여주게 함
            temp['title'] = humanize_title(temp.get('title', ''))
            temp['summary'] = clean_summary(temp.get('summary', ''), temp['title'], lang)
            filtered.append(temp)
    # 필터링 결과가 없으면 전체 전송
    if not filtered:
        filtered = [
            {**c, 'title': humanize_title(c.get('title', '')),
             'summary': clean_summary(c.get('summary', ''), humanize_title(c.get('title', '')), c.get('lang', 'en'))}
            for c in CACHED_DATA.get('courses', [])
        ]
    response = jsonify({"last_updated": CACHED_DATA.get('last_updated'), "courses": filtered})
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response

@app.route('/course/<course_ref>')
def course_detail(course_ref):
    """골프장 상세 페이지: 마크다운 파싱 및 본문 찌꺼기 제거"""
    base_id, legacy_lang = split_localized_id(course_ref)
    if legacy_lang:
        return redirect(f"/course/{base_id}?lang={legacy_lang}", code=301)

    lang = request.args.get('lang', 'en').strip().lower()
    if lang not in SUPPORTED_LANGS:
        lang = "en"

    course_id = resolve_course_id(base_id, lang)
    if not course_id:
        abort(404)

    md_path = os.path.join(CONTENT_DIR, f"{course_id}.md")
    if not os.path.exists(md_path):
        abort(404)
        
    with open(md_path, 'r', encoding='utf-8') as f:
        raw = f.read().strip()
    
    if '---' in raw:
        raw = '---' + raw.split('---', 1)[1]
    
    post_obj = frontmatter.loads(raw)
    post_data = dict(post_obj.metadata)
    
    # 본문 내 불필요한 메타데이터 텍스트 강제 삭제
    post_content = re.sub(r'^(lang|title|lat|lng|categories|thumbnail|address|date|booking|summary):.*$', '', post_obj.content, flags=re.MULTILINE | re.IGNORECASE).strip()
    # AI 자기점검 푸터(영문 보일러플레이트)가 살아있는 경우 런타임에서 제거
    post_content = strip_llm_selfcheck(post_content)
    
    post_data['id'] = course_id
    post_data['base_id'] = base_id
    post_data['lang'] = 'ko' if course_id.endswith('_ko') else 'en'
    post_data['title'] = humanize_title(post_data.get('title', ''))
    post_data['summary'] = short_summary(
        clean_summary(post_data.get('summary', ''), post_data['title'], post_data['lang']),
        200,
    )
    post_data = _attach_seo_fields(post_data, page_kind="course")
    _enrich_course_detail_post(post_data)

    if isinstance(post_data.get('categories'), str):
        post_data['categories'] = [c.strip() for c in post_data['categories'].split(',')]

    # 가독성을 위한 줄바꿈 정규식 보정
    post_content = re.sub(r'([\.!?:])\s+(\*\s)', r'\1\n\n\2', post_content)
    post_content = re.sub(r'([^\n])\n\*\s', r'\1\n\n* ', post_content)
    
    content_html = markdown.markdown(post_content, extensions=['tables', 'fenced_code'])

    current_categories = set(post_data.get('categories', []))
    current_pref = extract_prefecture(post_data.get("address", ""))
    related_candidates = []
    for course in CACHED_DATA.get('courses', []):
        if course.get('id') == course_id:
            continue
        if course.get('lang') != post_data['lang']:
            continue
        candidate_categories = set(course.get('categories', []))
        shared_categories = len(current_categories & candidate_categories) if current_categories else 0
        candidate_pref = extract_prefecture(course.get("address", ""))
        same_pref = 1 if current_pref and current_pref == candidate_pref else 0
        if shared_categories == 0 and same_pref == 0:
            continue
        score = (same_pref, shared_categories)
        related_candidates.append((score, course))

    related_candidates.sort(key=lambda x: x[0], reverse=True)
    related_courses = []
    for _, course in related_candidates[:6]:
        c = dict(course)
        c['title'] = humanize_title(c.get('title', ''))
        related_courses.append(c)

    related_guides = [g for g in CACHED_GUIDES if g.get('lang') == post_data['lang']][:3]

    return render_template(
        'detail.html',
        post=post_data,
        content=content_html,
        active_lang=post_data['lang'],
        related_courses=related_courses,
        related_guides=related_guides
    )

@app.route('/courses')
def courses_index():
    """크롤러/사용자용 서버 렌더 코스 인덱스 페이지"""
    lang = request.args.get('lang', 'en')
    page = max(1, request.args.get('page', default=1, type=int))
    per_page = 24

    filtered = [c for c in CACHED_DATA.get('courses', []) if c.get('lang') == lang]
    if not filtered:
        filtered = CACHED_DATA.get('courses', [])

    total = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)

    start = (page - 1) * per_page
    end = start + per_page
    page_courses = []
    for c in filtered[start:end]:
        cc = dict(c)
        cc['title'] = humanize_title(cc.get('title', ''))
        cc['summary'] = short_summary(
            clean_summary(cc.get('summary', ''), cc['title'], cc.get('lang', lang)),
            200,
        )
        page_courses.append(cc)

    return render_template(
        'courses.html',
        courses=page_courses,
        active_lang=lang,
        page=page,
        total_pages=total_pages,
        total_courses=total,
        has_prev=(page > 1),
        has_next=(page < total_pages)
    )

@app.route('/guide')
def guide_list():
    """가이드 전체 목록 페이지"""
    lang = request.args.get('lang', 'en')
    guides = [g for g in CACHED_GUIDES if g['lang'] == lang]
    return render_template('guide_list.html', guides=guides, lang=lang, active_lang=lang)

@app.route('/guide/<guide_ref>')
def guide_detail(guide_ref):
    """가이드 상세 페이지: 본문 청소 및 맞춤 이미지 매핑"""
    base_id, legacy_lang = split_localized_id(guide_ref)
    if legacy_lang:
        return redirect(f"/guide/{base_id}?lang={legacy_lang}", code=301)

    lang = request.args.get('lang', 'en').strip().lower()
    if lang not in SUPPORTED_LANGS:
        lang = "en"

    guide_id = resolve_guide_id(base_id, lang)
    if not guide_id:
        abort(404)

    path = os.path.join(GUIDE_DIR, f"{guide_id}.md")
    if not os.path.exists(path):
        abort(404)
        
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read().strip()
        if '---' in raw:
            raw = '---' + raw.split('---', 1)[1]
        post_obj = frontmatter.loads(raw)

    post_data = dict(post_obj.metadata)
    post_data['id'] = guide_id
    post_data['base_id'] = base_id
    post_data['lang'] = post_data.get('lang', 'en').strip().lower()
    post_data['title'] = humanize_title(post_data.get('title', '')) or "Japan Golf Guide"
    post_data['summary'] = short_summary(
        clean_summary(post_data.get('summary', ''), post_data['title'], post_data['lang']),
        200,
    )
    post_data = _attach_seo_fields(post_data, page_kind="guide")

    clean_body = re.sub(r'^(lang|title|summary|date):.*', '', post_obj.content, flags=re.MULTILINE).strip()
    clean_body = strip_llm_selfcheck(clean_body)

    html_content = markdown.markdown(clean_body, extensions=['tables', 'fenced_code'])
    base_id = guide_id.rsplit('_', 1)[0]
    img_url = GUIDE_IMAGES[abs(hash(base_id) * 97) % len(GUIDE_IMAGES)]
    related_courses = _course_cards(
        GUIDE_RELATED_COURSES.get(guide_id, []),
        lang=post_data['lang'],
        limit=6,
    )

    return render_template(
        'guide_detail.html',
        post=post_data,
        content=html_content,
        image=img_url,
        active_lang=post_data['lang'],
        related_courses=related_courses,
    )

# ==========================================
# 💰 수익화 리다이렉트 (라쿠텐 & 클룩)
# ==========================================

@app.route('/booking/<course_id>')
def booking_redirect(course_id):
    """라쿠텐 고라: 본문에서 도도부현을 찾아 D+7일 날짜로 검색 리다이렉트"""
    area_code = 0
    md_path = os.path.join(CONTENT_DIR, f"{course_id}.md")
    
    if os.path.exists(md_path):
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for pref, code in AREA_MAP.items():
                if pref in content:
                    area_code = code
                    break

    # 일주일 뒤 날짜 계산
    target_date = datetime.now() + timedelta(days=7)
    
    rakuten_params = [
        ('search_c_name', ''),
        ('year', str(target_date.year)),
        ('month', str(target_date.month)),
        ('day', str(target_date.day)),
        ('widthday', '1'),
        ('search_mode', 'normal'),
        ('l-id', 'search_btn_search'),
        ('area[]', area_code if area_code > 0 else 12), # 못 찾으면 기본 12(지바)
        ('order', 'rec')
    ]
    
    target_url = "https://gora.golf.rakuten.co.jp/search/result/?" + urllib.parse.urlencode(rakuten_params)
    # 사용자 라쿠텐 파트너 ID 결합
    final_url = "https://hb.afl.rakuten.co.jp/hgc/53117f43.0bea4fc1.53117f44.cd5b3814/?pc=" + urllib.parse.quote(target_url) + "&link_type=text&ut=eyJwYWdlIjoidXJsIiwidHlwZSI6InRleHQiLCJjb2wiOjF9"
    
    return redirect(final_url)

@app.route('/travel/<item_type>/<course_id>')
def travel_redirect(item_type, course_id):
    """클룩: 렌터카, 픽업, eSIM 별 전용 파트너 링크 리다이렉트"""
    is_ko = course_id.endswith('_ko')
    links = {
        "rental": "https://klook.tpo.mx/llRQoxrb" if is_ko else "https://klook.tpo.mx/skGztuAJ",
        "pickup": "https://klook.tpo.mx/8qLZKsBY" if is_ko else "https://klook.tpo.mx/zPN5kiip",
        "esim":   "https://klook.tpo.mx/OBHJbySq" if is_ko else "https://klook.tpo.mx/696NKlPT"
    }
    return redirect(links.get(item_type, "https://klook.tpo.mx/470RSray"))

# ==========================================
# 🖼️ 파비콘 및 SEO 정적 서비스 (구글 봇 최적화)
# ==========================================

@app.route('/favicon.ico')
@app.route('/favicon-32x32.png')
@app.route('/favicon-48x48.png')
@app.route('/apple-touch-icon.png')
@app.route('/android-chrome-192x192.png')
@app.route('/android-chrome-512x512.png')
def serve_favicons():
    """구글 검색 아이콘 노출을 위해 루트 경로에서 직접 파일 서빙"""
    image_dir = os.path.join(app.root_path, 'static', 'images')
    filename = request.path[1:]
    # Legacy asset fallback: some builds have favicons.ico instead of favicon.ico
    if filename == 'favicon.ico' and not os.path.exists(os.path.join(image_dir, filename)):
        filename = 'favicons.ico'
    return send_from_directory(
        image_dir,
        filename,
        mimetype='image/png' if filename.endswith('.png') else 'image/vnd.microsoft.icon'
    )

@app.route('/site.webmanifest')
def webmanifest():
    """PWA/검색엔진 아이콘 인식을 위한 manifest 파일 서빙"""
    return send_from_directory(STATIC_DIR, 'site.webmanifest', mimetype='application/manifest+json')

@app.route('/static/images/<path:filename>')
def serve_images(filename):
    """이미지는 GCS가 기준 — okadmin 업로드 즉시 반영."""
    images_root = os.path.join(app.root_path, 'static', 'images')
    if any(x in filename for x in ['favicon', 'apple-touch']):
        local_path = os.path.join(images_root, filename)
        if os.path.isfile(local_path):
            return send_from_directory(images_root, filename)
    url = f"https://storage.googleapis.com/ok-project-assets/okcaddie/{filename}"
    if request.query_string:
        url = f"{url}?{request.query_string.decode()}"
    return redirect(url, code=302)

@app.route('/sitemap.xml')
def sitemap_xml():
    """Sitemap index; sub-sitemaps are generated dynamically with file mtimes."""
    now_iso = datetime.now(timezone.utc).date().isoformat()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for name in ("sitemap-hub.xml", "sitemap-courses.xml", "sitemap-guides.xml"):
        lines.extend(
            [
                "  <sitemap>",
                f"    <loc>{escape(f'{SITE_URL}/{name}')}</loc>",
                f"    <lastmod>{now_iso}</lastmod>",
                "  </sitemap>",
            ]
        )
    lines.append("</sitemapindex>")
    response = make_response("\n".join(lines))
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route('/sitemap-courses.xml')
def sitemap_courses_xml():
    now_iso = datetime.now(timezone.utc).date().isoformat()
    response = make_response(_render_urlset(_course_sitemap_entries(now_iso)))
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route('/sitemap-guides.xml')
def sitemap_guides_xml():
    now_iso = datetime.now(timezone.utc).date().isoformat()
    response = make_response(_render_urlset(_guide_sitemap_entries(now_iso)))
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route('/sitemap-hub.xml')
def sitemap_hub_xml():
    now_iso = datetime.now(timezone.utc).date().isoformat()
    about_lastmod = _file_lastmod(os.path.join(BASE_DIR, "templates", "about.html"), now_iso)
    privacy_lastmod = _file_lastmod(os.path.join(BASE_DIR, "templates", "privacy.html"), now_iso)
    course_entries = _course_sitemap_entries(now_iso)
    guide_entries = _guide_sitemap_entries(now_iso)
    latest_course = max((e["lastmod"] for e in course_entries), default=now_iso)
    latest_guide = max((e["lastmod"] for e in guide_entries), default=now_iso)
    home_mod = max(latest_course, latest_guide)

    hub = [
        {
            "loc": f"{SITE_URL}/",
            "lastmod": home_mod,
            "changefreq": "daily",
            "priority": "1.0",
            "alternates": [
                ("en", f"{SITE_URL}/"),
                ("ko", f"{SITE_URL}/?lang=ko"),
                ("x-default", f"{SITE_URL}/"),
            ],
        },
        {
            "loc": f"{SITE_URL}/?lang=ko",
            "lastmod": home_mod,
            "changefreq": "daily",
            "priority": "0.9",
            "alternates": [
                ("en", f"{SITE_URL}/"),
                ("ko", f"{SITE_URL}/?lang=ko"),
                ("x-default", f"{SITE_URL}/"),
            ],
        },
        {
            "loc": f"{SITE_URL}/courses",
            "lastmod": latest_course,
            "changefreq": "weekly",
            "priority": "0.9",
            "alternates": [
                ("en", f"{SITE_URL}/courses"),
                ("ko", f"{SITE_URL}/courses?lang=ko"),
                ("x-default", f"{SITE_URL}/courses"),
            ],
        },
        {
            "loc": f"{SITE_URL}/courses?lang=ko",
            "lastmod": latest_course,
            "changefreq": "weekly",
            "priority": "0.8",
            "alternates": [
                ("en", f"{SITE_URL}/courses"),
                ("ko", f"{SITE_URL}/courses?lang=ko"),
                ("x-default", f"{SITE_URL}/courses"),
            ],
        },
        {
            "loc": f"{SITE_URL}/guide",
            "lastmod": latest_guide,
            "changefreq": "weekly",
            "priority": "0.9",
            "alternates": [
                ("en", f"{SITE_URL}/guide"),
                ("ko", f"{SITE_URL}/guide?lang=ko"),
                ("x-default", f"{SITE_URL}/guide"),
            ],
        },
        {
            "loc": f"{SITE_URL}/guide?lang=ko",
            "lastmod": latest_guide,
            "changefreq": "weekly",
            "priority": "0.8",
            "alternates": [
                ("en", f"{SITE_URL}/guide"),
                ("ko", f"{SITE_URL}/guide?lang=ko"),
                ("x-default", f"{SITE_URL}/guide"),
            ],
        },
        {
            "loc": f"{SITE_URL}/about",
            "lastmod": about_lastmod,
            "changefreq": "monthly",
            "priority": "0.4",
            "alternates": [
                ("en", f"{SITE_URL}/about"),
                ("ko", f"{SITE_URL}/about?lang=ko"),
                ("x-default", f"{SITE_URL}/about"),
            ],
        },
        {
            "loc": f"{SITE_URL}/about?lang=ko",
            "lastmod": about_lastmod,
            "changefreq": "monthly",
            "priority": "0.35",
            "alternates": [
                ("en", f"{SITE_URL}/about"),
                ("ko", f"{SITE_URL}/about?lang=ko"),
                ("x-default", f"{SITE_URL}/about"),
            ],
        },
        {
            "loc": f"{SITE_URL}/privacy",
            "lastmod": privacy_lastmod,
            "changefreq": "yearly",
            "priority": "0.3",
            "alternates": [
                ("en", f"{SITE_URL}/privacy"),
                ("ko", f"{SITE_URL}/privacy?lang=ko"),
                ("x-default", f"{SITE_URL}/privacy"),
            ],
        },
        {
            "loc": f"{SITE_URL}/privacy?lang=ko",
            "lastmod": privacy_lastmod,
            "changefreq": "yearly",
            "priority": "0.3",
            "alternates": [
                ("en", f"{SITE_URL}/privacy"),
                ("ko", f"{SITE_URL}/privacy?lang=ko"),
                ("x-default", f"{SITE_URL}/privacy"),
            ],
        },
    ]
    response = make_response(_render_urlset(hub))
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route('/robots.txt')
def robots_txt(): return send_from_directory(STATIC_DIR, 'robots.txt')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)