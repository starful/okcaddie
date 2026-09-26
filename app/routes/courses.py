"""Course list, detail, API, and affiliate redirects."""

from __future__ import annotations

import os
import re
import urllib.parse
from datetime import datetime, timedelta

import markdown
from flask import Blueprint, abort, jsonify, redirect, render_template, request

try:
    from ..badges import enrich_item
    from ..a8_affiliate import a8_banners_context, a8_dest_url
    from ..config import (
        AREA_MAP,
        FAMILY_SITE_ID,
        GORA_COURSE_IDS,
        GORA_SEARCH_NAMES,
        COURSE_RELATED_GUIDES,
        GUIDE_RELATED_COURSES,
        RETIRED_COURSE_REDIRECTS,
        RETIRED_GUIDE_REDIRECTS,
        SITE_URL,
        SUPPORTED_LANGS,
    )
    from ..course_content import load_course_post_file
    from ..data_loader import CACHED_DATA, CACHED_GUIDES, ensure_course_cache
    from ..gora_overseas import (
        COUNTRY_ISO,
        is_overseas_slug,
        japan_booking_dest,
        overseas_booking_dest,
    )
    from ..family_sites import cross_links_for, inject_family_context
    from ..ids import (
        extract_prefecture,
        guide_href,
        lang_from_course_id,
        resolve_course_id,
        resolve_guide_id,
        split_localized_id,
        course_href,
    )
    from ..paths import CONTENT_DIR
    from ..text_utils import clean_summary, humanize_title, short_summary, strip_llm_selfcheck
    from ..view_helpers import (
        attach_seo_fields,
        card_path,
        course_cards,
        enrich_course_detail_post,
        og_image_context,
        public_course,
        share_context,
        thumbnail_cache_v,
        thumbnail_with_v,
    )
except ImportError:
    from badges import enrich_item
    from a8_affiliate import a8_banners_context, a8_dest_url
    from config import (
        AREA_MAP,
        FAMILY_SITE_ID,
        GORA_COURSE_IDS,
        GORA_SEARCH_NAMES,
        COURSE_RELATED_GUIDES,
        GUIDE_RELATED_COURSES,
        RETIRED_COURSE_REDIRECTS,
        RETIRED_GUIDE_REDIRECTS,
        SITE_URL,
        SUPPORTED_LANGS,
    )
    from course_content import load_course_post_file
    from data_loader import CACHED_DATA, CACHED_GUIDES, ensure_course_cache
    from gora_overseas import (
        COUNTRY_ISO,
        is_overseas_slug,
        japan_booking_dest,
        overseas_booking_dest,
    )
    from family_sites import cross_links_for, inject_family_context
    from ids import (
        extract_prefecture,
        guide_href,
        lang_from_course_id,
        resolve_course_id,
        resolve_guide_id,
        split_localized_id,
        course_href,
    )
    from paths import CONTENT_DIR
    from text_utils import clean_summary, humanize_title, short_summary, strip_llm_selfcheck
    from view_helpers import (
        attach_seo_fields,
        card_path,
        course_cards,
        enrich_course_detail_post,
        og_image_context,
        public_course,
        share_context,
        thumbnail_cache_v,
        thumbnail_with_v,
    )

courses_bp = Blueprint("courses", __name__)


def _related_guides_for_course(base_id: str, lang: str, limit: int = 3) -> list[dict]:
    """Prefer COURSE_RELATED_GUIDES mapping; fall back to same-lang guides."""
    by_base = {
        (g.get("base_id") or split_localized_id(g.get("id", ""))[0]): g
        for g in CACHED_GUIDES
        if g.get("lang") == lang
    }
    related: list[dict] = []
    for gid in COURSE_RELATED_GUIDES.get(base_id, ()):
        g = by_base.get(gid)
        if not g:
            continue
        item = dict(g)
        item["link"] = guide_href(gid, lang)
        related.append(item)
        if len(related) >= limit:
            return related
    if related:
        return related
    for g in CACHED_GUIDES:
        if g.get("lang") != lang:
            continue
        item = dict(g)
        bid = item.get("base_id") or split_localized_id(item.get("id", ""))[0]
        item["link"] = guide_href(bid, lang)
        related.append(item)
        if len(related) >= limit:
            break
    return related


@courses_bp.route("/api/courses")
def api_courses():
    ensure_course_cache()
    lang = request.args.get("lang", "en")
    filtered = []
    for c in CACHED_DATA.get("courses", []):
        if c.get("lang") == lang:
            temp = enrich_item(public_course(c))
            temp["lang"] = lang
            temp["title"] = humanize_title(temp.get("title", ""))
            temp["summary"] = clean_summary(temp.get("summary", ""), temp["title"], lang)
            filtered.append(temp)
    if not filtered:
        filtered = [
            enrich_item(
                {
                    **public_course(c),
                    "title": humanize_title(c.get("title", "")),
                    "summary": clean_summary(
                        c.get("summary", ""),
                        humanize_title(c.get("title", "")),
                        c.get("lang", "en"),
                    ),
                }
            )
            for c in CACHED_DATA.get("courses", [])
        ]
    response = jsonify({"last_updated": CACHED_DATA.get("last_updated"), "courses": filtered})
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@courses_bp.route("/courses")
def courses_index():
    lang = request.args.get("lang", "en")
    page = max(1, request.args.get("page", default=1, type=int))
    per_page = 24

    filtered = [c for c in CACHED_DATA.get("courses", []) if c.get("lang") == lang]
    if not filtered:
        filtered = CACHED_DATA.get("courses", [])

    total = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)

    start = (page - 1) * per_page
    end = start + per_page
    page_courses = []
    for c in filtered[start:end]:
        cc = dict(c)
        cc["title"] = humanize_title(cc.get("title", ""))
        cc["summary"] = short_summary(
            clean_summary(cc.get("summary", ""), cc["title"], cc.get("lang", lang)),
            200,
        )
        page_courses.append(cc)

    return render_template(
        "courses.html",
        courses=page_courses,
        active_lang=lang,
        page=page,
        total_pages=total_pages,
        total_courses=total,
        has_prev=(page > 1),
        has_next=(page < total_pages),
    )


def _lang_aware_redirect(dest: str, lang: str):
    if lang in ("ko", "ja"):
        if "?" not in dest:
            dest = f"{dest}?lang={lang}"
        elif "lang=" not in dest:
            dest = f"{dest}&lang={lang}"
    return redirect(dest, code=301)


@courses_bp.route("/course/<course_ref>")
def course_detail(course_ref):
    base_id, legacy_lang = split_localized_id(course_ref)

    lang = (legacy_lang or request.args.get("lang", "en")).strip().lower()
    if lang not in SUPPORTED_LANGS:
        lang = "en"

    retired_target = RETIRED_COURSE_REDIRECTS.get(base_id)
    if retired_target:
        return _lang_aware_redirect(retired_target, lang)

    if legacy_lang:
        dest = f"/course/{base_id}" + (f"?lang={legacy_lang}" if legacy_lang != "en" else "")
        return redirect(dest, code=301)

    lang = request.args.get("lang", "en").strip().lower()
    if lang not in SUPPORTED_LANGS:
        lang = "en"

    course_id = resolve_course_id(base_id, lang)
    if not course_id:
        abort(404)

    md_path = os.path.join(CONTENT_DIR, f"{course_id}.md")
    if not os.path.exists(md_path):
        abort(404)

    post_obj, _ = load_course_post_file(md_path)
    post_data = dict(post_obj.metadata)

    post_content = re.sub(
        r"^(lang|title|lat|lng|categories|thumbnail|address|date|booking|summary|youtube_id|gora_cid|gora_name|country):.*$",
        "",
        post_obj.content,
        flags=re.MULTILINE | re.IGNORECASE,
    ).strip()
    post_content = strip_llm_selfcheck(post_content)

    post_data["id"] = course_id
    post_data["base_id"] = base_id
    post_data["lang"] = lang_from_course_id(course_id)
    country = str(post_data.get("country") or "jp").strip().lower() or "jp"
    post_data["country"] = country
    post_data["country_iso"] = COUNTRY_ISO.get(country, "JP")
    mapped_cid = str(GORA_COURSE_IDS.get(base_id) or "").strip()
    yaml_cid = str(post_data.get("gora_cid") or "").strip()
    if not yaml_cid and mapped_cid:
        post_data["gora_cid"] = mapped_cid
    post_data["is_overseas"] = country != "jp" or is_overseas_slug(base_id)
    if isinstance(post_data.get("categories"), str):
        post_data["categories"] = [
            c.strip() for c in post_data["categories"].split(",")
        ]
    post_data["is_private"] = _is_private_categories(post_data.get("categories"))
    post_data["title"] = humanize_title(post_data.get("title", ""))
    post_data["summary"] = short_summary(
        clean_summary(post_data.get("summary", ""), post_data["title"], post_data["lang"]),
        200,
    )
    post_data = attach_seo_fields(post_data, page_kind="course")
    enrich_course_detail_post(post_data)

    cache_v = thumbnail_cache_v(post_data.get("date") or post_data.get("published"))
    base_id_for_img = post_data.get("base_id") or base_id
    thumb = post_data.get("thumbnail") or f"/static/images/{base_id_for_img}.jpg"
    post_data["thumbnail"] = thumbnail_with_v(thumb, cache_v)

    post_content = re.sub(r"([\.!?:])\s+(\*\s)", r"\1\n\n\2", post_content)
    post_content = re.sub(r"([^\n])\n\*\s", r"\1\n\n* ", post_content)

    content_html = markdown.markdown(post_content, extensions=["tables", "fenced_code"])

    current_categories = set(post_data.get("categories", []))
    current_pref = extract_prefecture(post_data.get("address", ""))
    related_candidates = []
    for course in CACHED_DATA.get("courses", []):
        if course.get("id") == course_id:
            continue
        if course.get("lang") != post_data["lang"]:
            continue
        candidate_categories = set(course.get("categories", []))
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
        c = public_course(course)
        c["title"] = humanize_title(c.get("title", ""))
        related_courses.append(c)

    related_guides = _related_guides_for_course(base_id, post_data["lang"])

    course_path = course_href(base_id, post_data["lang"])
    share_ctx = share_context(course_id, post_data["title"], post_data["lang"], course_path, base_id=base_id)

    return render_template(
        "detail.html",
        post=post_data,
        content=content_html,
        active_lang=post_data["lang"],
        related_courses=related_courses,
        related_guides=related_guides,
        cross_site_links=cross_links_for(
            FAMILY_SITE_ID,
            post_data["lang"],
            address=post_data.get("address"),
        ),
        **inject_family_context(FAMILY_SITE_ID, post_data["lang"]),
        **a8_banners_context(
            lang=post_data["lang"],
            lat=post_data.get("lat"),
            lng=post_data.get("lng"),
            country=post_data.get("country"),
        ),
        **og_image_context(base_id),
        **share_ctx,
    )


@courses_bp.route("/card/<course_ref>")
def course_social_card(course_ref):
    base_id, legacy_lang = split_localized_id(course_ref)
    if legacy_lang:
        dest = f"/card/{base_id}" + (f"?lang={legacy_lang}" if legacy_lang != "en" else "")
        return redirect(dest, code=301)

    lang = request.args.get("lang", "en").strip().lower()
    if lang not in SUPPORTED_LANGS:
        lang = "en"

    retired_target = RETIRED_COURSE_REDIRECTS.get(base_id)
    if retired_target:
        return _lang_aware_redirect(retired_target, lang)

    # Mislinked guide IDs under /card/ → canonical guide page (or retired target).
    guide_retired = RETIRED_GUIDE_REDIRECTS.get(base_id)
    if guide_retired:
        return _lang_aware_redirect(guide_retired, lang)
    if not resolve_course_id(base_id, lang) and resolve_guide_id(base_id, lang):
        dest = f"/guide/{base_id}"
        return _lang_aware_redirect(dest, lang)

    course_id = resolve_course_id(base_id, lang)
    if not course_id:
        abort(404)

    md_path = os.path.join(CONTENT_DIR, f"{course_id}.md")
    if not os.path.exists(md_path):
        abort(404)

    post_obj, _ = load_course_post_file(md_path)
    post_data = dict(post_obj.metadata)
    post_data["lang"] = lang_from_course_id(course_id)
    post_data["title"] = humanize_title(post_data.get("title", ""))
    post_data = attach_seo_fields(post_data, page_kind="course")

    course_path = course_href(base_id, post_data["lang"])
    card_path_val = card_path(base_id, post_data["lang"])

    return render_template(
        "social_card.html",
        lang=post_data["lang"],
        title=post_data["title"],
        seo_title=post_data["seo_title"],
        seo_desc=post_data["seo_description"],
        page_url=f"{SITE_URL}{course_path}",
        card_url=f"{SITE_URL}{card_path_val}",
        **og_image_context(base_id),
    )


_JP_COURSE_NAME = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
_HANGUL = re.compile(r"[\uac00-\ud7af]")

# Prefecture tokens for slug/address. Longer keys first. Never substring-match
# (sagamihara must not become Saga; body copy saying "Tokyo" must not steal Hyogo).
_EN_AREA: tuple[tuple[str, int], ...] = (
    ("hokkaido", 1),
    ("kanagawa", 14),
    ("yamanashi", 19),
    ("kagoshima", 46),
    ("yamaguchi", 35),
    ("tokushima", 36),
    ("hiroshima", 34),
    ("ishikawa", 17),
    ("fukuoka", 40),
    ("fukushima", 7),
    ("nagasaki", 42),
    ("miyazaki", 45),
    ("kumamoto", 43),
    ("wakayama", 30),
    ("yamagata", 6),
    ("shizuoka", 22),
    ("niigata", 15),
    ("ibaraki", 8),
    ("tochigi", 9),
    ("saitama", 11),
    ("okayama", 33),
    ("tottori", 31),
    ("shimane", 32),
    ("miyagi", 4),
    ("aomori", 2),
    ("akita", 5),
    ("iwate", 3),
    ("nagano", 20),
    ("toyama", 16),
    ("gifu", 21),
    ("aichi", 23),
    ("shiga", 25),
    ("kyoto", 26),
    ("osaka", 27),
    ("hyogo", 28),
    ("nara", 29),
    ("oita", 44),
    ("saga", 41),
    ("ehime", 38),
    ("kagawa", 37),
    ("kochi", 39),
    ("chiba", 12),
    ("tokyo", 13),
    ("gunma", 10),
    ("mie", 24),
    ("okinawa", 47),
    ("fukui", 18),
)

_PLACE_AREA: tuple[tuple[str, int], ...] = (
    ("sagamihara", 14),
    ("yokohama", 14),
    ("hakone", 14),
    ("takarazuka", 28),
    ("nishinomiya", 28),
    ("amagasaki", 28),
    ("karuizawa", 20),
    ("hamamatsu", 22),
    ("gotemba", 22),
    ("sapporo", 1),
    ("sendai", 4),
    ("nagoya", 23),
    ("narita", 12),
    ("beppu", 44),
    ("kobe", 28),
    ("nago", 47),
    ("nasu", 9),
    ("ito", 22),
    ("miki", 28),
)


def _word_in(blob: str, token: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", blob) is not None


def gora_area_code(content: str, *, base_id: str, course_id: str = "") -> int:
    """Prefecture for GORA area[] — address + slug only (never summary/body)."""
    address = _yaml_field(content, "address").lower()
    for token, code in _EN_AREA + _PLACE_AREA:
        if _word_in(address, token):
            return code
    tokens = set(base_id.lower().replace("-", "_").split("_"))
    tokens.update((course_id or "").lower().replace("-", "_").split("_"))
    tokens.discard("en")
    tokens.discard("ko")
    tokens.discard("ja")
    for token, code in _EN_AREA + _PLACE_AREA:
        if token in tokens:
            return code
    # Japanese prefecture name only inside the address line.
    pref = extract_prefecture(address)
    if pref:
        return AREA_MAP.get(pref, 0)
    return 0


def _is_private_categories(categories) -> bool:
    if isinstance(categories, str):
        cats = [c.strip() for c in categories.split(",")]
    elif isinstance(categories, (list, tuple, set)):
        cats = [str(c).strip() for c in categories]
    else:
        cats = []
    markers = ("Private Club", "회원제", "会員制")
    return any(any(m in c for m in markers) for c in cats)


def _yaml_field(content: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*(.*)$", content)
    if not match:
        return ""
    raw = match.group(1).strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        raw = raw[1:-1]
    return raw.strip()


def _yaml_title(content: str) -> str:
    return _yaml_field(content, "title")


def _usable_gora_name(raw: str) -> str:
    name = humanize_title(raw)
    if not name or _HANGUL.search(name) or not _JP_COURSE_NAME.search(name):
        return ""
    return name[:40]


def gora_search_name(content: str, *, from_course_md: bool, base_id: str = "") -> str:
    """GORA is a Japanese catalog — EN/KO SEO titles return zero courses."""
    if not from_course_md:
        return ""
    for raw in (
        _yaml_field(content, "gora_name"),
        GORA_SEARCH_NAMES.get(base_id, ""),
        _yaml_title(content),
    ):
        name = _usable_gora_name(raw)
        if name:
            return name
    return ""


def _noindex_redirect(url: str, code: int = 302):
    response = redirect(url, code=code)
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@courses_bp.route("/booking/<course_id>")
def booking_redirect(course_id):
    area_code = 0
    search_name = ""
    base_id, _legacy = split_localized_id(course_id)
    md_path = os.path.join(CONTENT_DIR, f"{course_id}.md")
    if not os.path.exists(md_path):
        # Accept bare base_id or wrong-suffix IDs from old share links.
        for candidate in (f"{base_id}_en", f"{base_id}_ko", f"{base_id}_ja"):
            alt = os.path.join(CONTENT_DIR, f"{candidate}.md")
            if os.path.exists(alt):
                md_path = alt
                break

    # Guides live under GUIDE_DIR — still map area for GORA region search.
    guide_path = None
    try:
        from ..paths import GUIDE_DIR
    except ImportError:
        from paths import GUIDE_DIR
    for candidate in (course_id, f"{base_id}_en", f"{base_id}_ko", f"{base_id}_ja"):
        gp = os.path.join(GUIDE_DIR, f"{candidate}.md")
        if os.path.exists(gp):
            guide_path = gp
            break

    content = ""
    path = md_path if os.path.exists(md_path) else guide_path
    gora_cid = ""
    country = "jp"
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        gora_cid = _yaml_field(content, "gora_cid").strip()
        country = (_yaml_field(content, "country") or "jp").strip().lower() or "jp"

    if not gora_cid:
        gora_cid = str(GORA_COURSE_IDS.get(base_id) or "").strip()

    overseas = country != "jp" or is_overseas_slug(base_id)
    if overseas:
        return _noindex_redirect(
            overseas_booking_dest(gora_cid=gora_cid, slug=base_id)
        )

    if gora_cid:
        dest = japan_booking_dest(gora_cid)
        if dest:
            return _noindex_redirect(dest)

    if path and os.path.exists(path):
        area_code = gora_area_code(content, base_id=base_id, course_id=course_id)
        search_name = gora_search_name(
            content, from_course_md=path == md_path, base_id=base_id
        )

    target_date = datetime.now() + timedelta(days=14)

    rakuten_params = [
        ("year", str(target_date.year)),
        ("month", str(target_date.month)),
        ("day", str(target_date.day)),
        ("widthday", "7"),
        ("search_mode", "normal"),
        ("l-id", "search_btn_search"),
        ("order", "rec"),
    ]
    if search_name:
        rakuten_params.insert(0, ("search_c_name", search_name))
    if area_code > 0:
        rakuten_params.append(("area[]", area_code))

    target_url = "https://gora.golf.rakuten.co.jp/search/result/?" + urllib.parse.urlencode(rakuten_params)
    final_url = (
        "https://hb.afl.rakuten.co.jp/hgc/53117f43.0bea4fc1.53117f44.cd5b3814/?pc="
        + urllib.parse.quote(target_url)
        + "&link_type=text&ut=eyJwYWdlIjoidXJsIiwidHlwZSI6InRleHQiLCJjb2wiOjF9"
    )

    return _noindex_redirect(final_url)


@courses_bp.route("/go/<banner_id>")
def affiliate_go(banner_id):
    """Crawlers must not follow affiliate click URLs; robots.txt disallows /go/."""
    dest = a8_dest_url(
        banner_id,
        city=request.args.get("city"),
        lang=request.args.get("lang") or request.args.get("hl"),
    )
    if not dest:
        abort(404)
    return _noindex_redirect(dest)


@courses_bp.route("/travel/<item_type>/<course_id>")
def travel_redirect(item_type, course_id):
    """Legacy Klook hotel paths → GORA tee-time search, not Agoda."""
    return booking_redirect(course_id)
