"""Guide list and detail pages."""

from __future__ import annotations

import os
import re

import markdown
from flask import Blueprint, abort, redirect, render_template, request

try:
    from ..config import FAMILY_SITE_ID, GUIDE_RELATED_COURSES, SUPPORTED_LANGS
    from ..data_loader import CACHED_GUIDES
    from ..family_sites import cross_links_for, inject_family_context
    from ..guide_content import guide_image_url, load_guide_post
    from ..ids import resolve_guide_id, split_localized_id
    from ..paths import GUIDE_DIR
    from ..text_utils import clean_summary, humanize_title, short_summary, strip_llm_selfcheck
    from ..view_helpers import attach_seo_fields, course_cards, share_context
except ImportError:
    from config import FAMILY_SITE_ID, GUIDE_RELATED_COURSES, SUPPORTED_LANGS
    from data_loader import CACHED_GUIDES
    from family_sites import cross_links_for, inject_family_context
    from guide_content import guide_image_url, load_guide_post
    from ids import resolve_guide_id, split_localized_id
    from paths import GUIDE_DIR
    from text_utils import clean_summary, humanize_title, short_summary, strip_llm_selfcheck
    from view_helpers import attach_seo_fields, course_cards, share_context

guides_bp = Blueprint("guides", __name__)


@guides_bp.route("/guide")
def guide_list():
    lang = request.args.get("lang", "en")
    guides = [g for g in CACHED_GUIDES if g["lang"] == lang]
    return render_template("guide_list.html", guides=guides, lang=lang, active_lang=lang)


@guides_bp.route("/guide/<guide_ref>")
def guide_detail(guide_ref):
    base_id, legacy_lang = split_localized_id(guide_ref)
    if legacy_lang:
        return redirect(f"/guide/{base_id}?lang={legacy_lang}", code=301)

    lang = request.args.get("lang", "en").strip().lower()
    if lang not in SUPPORTED_LANGS:
        lang = "en"

    guide_id = resolve_guide_id(base_id, lang)
    if not guide_id:
        abort(404)

    path = os.path.join(GUIDE_DIR, f"{guide_id}.md")
    if not os.path.exists(path):
        abort(404)

    post_obj = load_guide_post(path)
    post_data = dict(post_obj.metadata)
    post_data["id"] = guide_id
    post_data["base_id"] = base_id
    post_data["lang"] = post_data.get("lang", "en").strip().lower()
    post_data["title"] = humanize_title(post_data.get("title", "")) or "Japan Golf Guide"
    post_data["summary"] = short_summary(
        clean_summary(post_data.get("summary", ""), post_data["title"], post_data["lang"]),
        200,
    )
    post_data = attach_seo_fields(post_data, page_kind="guide")

    clean_body = re.sub(r"^(lang|title|summary|date):.*", "", post_obj.content, flags=re.MULTILINE).strip()
    clean_body = strip_llm_selfcheck(clean_body)

    html_content = markdown.markdown(clean_body, extensions=["tables", "fenced_code"])
    img_base_id = guide_id.rsplit("_", 1)[0]
    img_url = guide_image_url(img_base_id)
    related_courses = course_cards(
        GUIDE_RELATED_COURSES.get(guide_id, []),
        lang=post_data["lang"],
        limit=6,
    )

    guide_path = f"/guide/{base_id}{'?lang=ko' if post_data['lang'] == 'ko' else ''}"
    share_ctx = share_context(guide_id, post_data["title"], post_data["lang"], guide_path)

    return render_template(
        "guide_detail.html",
        post=post_data,
        content=html_content,
        image=img_url,
        active_lang=post_data["lang"],
        related_courses=related_courses,
        og_image_abs=img_url,
        og_image_width=1200,
        og_image_height=630,
        cross_site_links=cross_links_for(FAMILY_SITE_ID, post_data["lang"]),
        **inject_family_context(FAMILY_SITE_ID, post_data["lang"]),
        **share_ctx,
    )
