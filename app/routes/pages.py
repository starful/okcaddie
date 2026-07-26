"""Hub pages, about/privacy, sitemaps."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, make_response, render_template, request

try:
    from ..config import FEATURED_COURSE_BASE_IDS, GOOGLE_MAPS_JS_API_KEY, SUPPORTED_LANGS
    from ..data_loader import CACHED_DATA, CACHED_GUIDES, ensure_course_cache
    from ..sitemap import (
        course_sitemap_entries,
        guide_sitemap_entries,
        hub_sitemap_entries,
        render_urlset,
        sitemap_index_xml,
    )
    from ..view_helpers import course_cards, crawl_course_links, public_course
except ImportError:
    from config import FEATURED_COURSE_BASE_IDS, GOOGLE_MAPS_JS_API_KEY, SUPPORTED_LANGS
    from data_loader import CACHED_DATA, CACHED_GUIDES, ensure_course_cache
    from sitemap import (
        course_sitemap_entries,
        guide_sitemap_entries,
        hub_sitemap_entries,
        render_urlset,
        sitemap_index_xml,
    )
    from view_helpers import course_cards, crawl_course_links, public_course

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    lang = request.args.get("lang", "en")
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    featured = [g for g in CACHED_GUIDES if g["lang"] == lang][:3]
    if not featured:
        featured = CACHED_GUIDES[:3]
    return render_template(
        "index.html",
        featured_guides=featured,
        featured_courses=course_cards(FEATURED_COURSE_BASE_IDS, lang=lang),
        crawl_course_links=crawl_course_links(limit=60, lang=lang),
        active_lang=lang,
        google_maps_js_api_key=GOOGLE_MAPS_JS_API_KEY,
    )


@pages_bp.route("/about")
@pages_bp.route("/about.html")
def about():
    lang = request.args.get("lang", "en")
    return render_template("about.html", active_lang=lang)


@pages_bp.route("/privacy")
@pages_bp.route("/privacy.html")
def privacy():
    lang = request.args.get("lang", "en")
    return render_template("privacy.html", active_lang=lang)


@pages_bp.route("/contact")
@pages_bp.route("/contact.html")
def contact():
    lang = request.args.get("lang", "en")
    return render_template("contact.html", active_lang=lang)


@pages_bp.route("/compare")
def compare_page():
    lang = request.args.get("lang", "en")
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    raw_ids = [x.strip() for x in (request.args.get("ids") or "").split(",") if x.strip()]
    ids = []
    for rid in raw_ids:
        base = rid.replace("_en", "").replace("_ko", "") if rid.endswith(("_en", "_ko")) else rid
        # also handle already-base ids
        if base.endswith("_en") or base.endswith("_ko"):
            base = base.rsplit("_", 1)[0]
        if base not in ids:
            ids.append(base)
        if len(ids) >= 3:
            break
    ensure_course_cache()
    by_base = {}
    for row in CACHED_DATA.get("courses", []):
        if row.get("lang") != lang:
            continue
        base = row.get("base_id") or str(row.get("id", "")).rsplit("_", 1)[0]
        item = public_course(row)
        item["base_id"] = base
        by_base[base] = item
    selected = [by_base[i] for i in ids if i in by_base]
    meta_title = "골프장 비교 | OKCaddie" if lang == "ko" else "Compare golf courses | OKCaddie"
    meta_desc = (
        "선택한 골프장을 테마·지역·요약으로 비교합니다."
        if lang == "ko"
        else "Compare selected golf courses by theme, area, and summary."
    )
    return render_template(
        "compare.html",
        lang=lang,
        active_lang=lang,
        selected=selected,
        meta_title=meta_title,
        meta_desc=meta_desc,
    )


@pages_bp.route("/sitemap.xml")
def sitemap_xml():
    now_iso = datetime.now(timezone.utc).date().isoformat()
    response = make_response(sitemap_index_xml(now_iso))
    response.headers["Content-Type"] = "application/xml"
    return response


@pages_bp.route("/sitemap-courses.xml")
def sitemap_courses_xml():
    now_iso = datetime.now(timezone.utc).date().isoformat()
    response = make_response(render_urlset(course_sitemap_entries(now_iso)))
    response.headers["Content-Type"] = "application/xml"
    return response


@pages_bp.route("/sitemap-guides.xml")
def sitemap_guides_xml():
    now_iso = datetime.now(timezone.utc).date().isoformat()
    response = make_response(render_urlset(guide_sitemap_entries(now_iso)))
    response.headers["Content-Type"] = "application/xml"
    return response


@pages_bp.route("/sitemap-hub.xml")
def sitemap_hub_xml():
    now_iso = datetime.now(timezone.utc).date().isoformat()
    response = make_response(render_urlset(hub_sitemap_entries(now_iso)))
    response.headers["Content-Type"] = "application/xml"
    return response
