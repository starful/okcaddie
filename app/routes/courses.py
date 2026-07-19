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
    from ..config import AREA_MAP, FAMILY_SITE_ID, GUIDE_RELATED_COURSES, SITE_URL, SUPPORTED_LANGS
    from ..course_content import load_course_post_file
    from ..data_loader import CACHED_DATA, CACHED_GUIDES, ensure_course_cache
    from ..family_sites import cross_links_for, inject_family_context
    from ..ids import extract_prefecture, resolve_course_id, split_localized_id
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
    from config import AREA_MAP, FAMILY_SITE_ID, GUIDE_RELATED_COURSES, SITE_URL, SUPPORTED_LANGS
    from course_content import load_course_post_file
    from data_loader import CACHED_DATA, CACHED_GUIDES, ensure_course_cache
    from family_sites import cross_links_for, inject_family_context
    from ids import extract_prefecture, resolve_course_id, split_localized_id
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


@courses_bp.route("/course/<course_ref>")
def course_detail(course_ref):
    base_id, legacy_lang = split_localized_id(course_ref)
    if legacy_lang:
        return redirect(f"/course/{base_id}?lang={legacy_lang}", code=301)

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
        r"^(lang|title|lat|lng|categories|thumbnail|address|date|booking|summary):.*$",
        "",
        post_obj.content,
        flags=re.MULTILINE | re.IGNORECASE,
    ).strip()
    post_content = strip_llm_selfcheck(post_content)

    post_data["id"] = course_id
    post_data["base_id"] = base_id
    post_data["lang"] = "ko" if course_id.endswith("_ko") else "en"
    post_data["title"] = humanize_title(post_data.get("title", ""))
    post_data["summary"] = short_summary(
        clean_summary(post_data.get("summary", ""), post_data["title"], post_data["lang"]),
        200,
    )
    post_data = attach_seo_fields(post_data, page_kind="course")
    enrich_course_detail_post(post_data)

    if isinstance(post_data.get("categories"), str):
        post_data["categories"] = [c.strip() for c in post_data["categories"].split(",")]

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

    related_guides = [g for g in CACHED_GUIDES if g.get("lang") == post_data["lang"]][:3]

    course_path = f"/course/{base_id}{'?lang=ko' if post_data['lang'] == 'ko' else ''}"
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
        **og_image_context(base_id),
        **share_ctx,
    )


@courses_bp.route("/card/<course_ref>")
def course_social_card(course_ref):
    base_id, legacy_lang = split_localized_id(course_ref)
    if legacy_lang:
        return redirect(f"/card/{base_id}?lang={legacy_lang}", code=301)

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
    post_data["lang"] = "ko" if course_id.endswith("_ko") else "en"
    post_data["title"] = humanize_title(post_data.get("title", ""))
    post_data = attach_seo_fields(post_data, page_kind="course")

    course_path = f"/course/{base_id}{'?lang=ko' if post_data['lang'] == 'ko' else ''}"
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


@courses_bp.route("/booking/<course_id>")
def booking_redirect(course_id):
    area_code = 0
    md_path = os.path.join(CONTENT_DIR, f"{course_id}.md")

    if os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
            for pref, code in AREA_MAP.items():
                if pref in content:
                    area_code = code
                    break

    target_date = datetime.now() + timedelta(days=7)

    rakuten_params = [
        ("search_c_name", ""),
        ("year", str(target_date.year)),
        ("month", str(target_date.month)),
        ("day", str(target_date.day)),
        ("widthday", "1"),
        ("search_mode", "normal"),
        ("l-id", "search_btn_search"),
        ("area[]", area_code if area_code > 0 else 12),
        ("order", "rec"),
    ]

    target_url = "https://gora.golf.rakuten.co.jp/search/result/?" + urllib.parse.urlencode(rakuten_params)
    final_url = (
        "https://hb.afl.rakuten.co.jp/hgc/53117f43.0bea4fc1.53117f44.cd5b3814/?pc="
        + urllib.parse.quote(target_url)
        + "&link_type=text&ut=eyJwYWdlIjoidXJsIiwidHlwZSI6InRleHQiLCJjb2wiOjF9"
    )

    return redirect(final_url)


@courses_bp.route("/travel/<item_type>/<course_id>")
def travel_redirect(item_type, course_id):
    is_ko = course_id.endswith("_ko")
    # "guide" = general Klook landing from guide pages (not GORA /booking/).
    links = {
        "rental": "https://klook.tpo.mx/llRQoxrb" if is_ko else "https://klook.tpo.mx/skGztuAJ",
        "pickup": "https://klook.tpo.mx/8qLZKsBY" if is_ko else "https://klook.tpo.mx/zPN5kiip",
        "esim": "https://klook.tpo.mx/OBHJbySq" if is_ko else "https://klook.tpo.mx/696NKlPT",
        "guide": "https://klook.tpo.mx/470RSray",
    }
    return redirect(links.get(item_type, "https://klook.tpo.mx/470RSray"))
