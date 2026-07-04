from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
)
from flask_compress import Compress
import copy
import frontmatter
import io
import json
import markdown
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

try:
    from .config import (
        AREA_MAP,
        FAMILY_SITE_ID,
        FEATURED_COURSE_BASE_IDS,
        GCS_ASSET_PREFIX,
        GOOGLE_MAPS_JS_API_KEY,
        GUIDE_IMAGES,
        GUIDE_RELATED_COURSES,
        SITE_URL,
        SUPPORTED_LANGS,
    )
    from .content_new import enrich_item
    from .course_content import load_course_post_file
    from .data_loader import CACHED_DATA, CACHED_GUIDES, ensure_course_cache, load_all_data
    from .family_sites import cross_links_for, inject_family_context
    from .ids import (
        course_href,
        extract_prefecture,
        resolve_course_id,
        resolve_guide_id,
        split_localized_id,
    )
    from .paths import BASE_DIR, CONTENT_DIR, GUIDE_DIR, STATIC_DIR
    from .reactions import reactions_bp
    from .sitemap import (
        course_sitemap_entries,
        guide_sitemap_entries,
        hub_sitemap_entries,
        render_urlset,
        sitemap_index_xml,
    )
    from .text_utils import clean_summary, humanize_title, short_summary, strip_llm_selfcheck, truncate_text
except ImportError:
    from config import (
        AREA_MAP,
        FAMILY_SITE_ID,
        FEATURED_COURSE_BASE_IDS,
        GCS_ASSET_PREFIX,
        GOOGLE_MAPS_JS_API_KEY,
        GUIDE_IMAGES,
        GUIDE_RELATED_COURSES,
        SITE_URL,
        SUPPORTED_LANGS,
    )
    from content_new import enrich_item
    from course_content import load_course_post_file
    from data_loader import CACHED_DATA, CACHED_GUIDES, ensure_course_cache, load_all_data
    from family_sites import cross_links_for, inject_family_context
    from ids import (
        course_href,
        extract_prefecture,
        resolve_course_id,
        resolve_guide_id,
        split_localized_id,
    )
    from paths import BASE_DIR, CONTENT_DIR, GUIDE_DIR, STATIC_DIR
    from reactions import reactions_bp
    from sitemap import (
        course_sitemap_entries,
        guide_sitemap_entries,
        hub_sitemap_entries,
        render_urlset,
        sitemap_index_xml,
    )
    from text_utils import clean_summary, humanize_title, short_summary, strip_llm_selfcheck, truncate_text

app = Flask(__name__)
Compress(app)
app.register_blueprint(reactions_bp)


def _gcs_image_url(filename: str) -> str:
    return f"https://storage.googleapis.com/ok-project-assets/{GCS_ASSET_PREFIX}/{filename}"


def _thumbnail_cache_v(published_or_date: str | None) -> str:
    v = str(published_or_date or "").strip()[:10]
    return v if len(v) >= 8 else ""


def _thumbnail_with_v(url: str, cache_v: str | None = None) -> str:
    if not url:
        return url
    v = _thumbnail_cache_v(cache_v)
    base = url.split("?", 1)[0]
    return f"{base}?v={v}" if v else base


def _public_course(row: dict) -> dict:
    out = copy.deepcopy(row)
    out["thumbnail"] = _thumbnail_with_v(out.get("thumbnail", ""), out.get("published"))
    return out


def _social_image_url(slug: str) -> str:
    safe = re.sub(r"[^a-z0-9_-]", "", slug.lower())
    return f"{SITE_URL}/social/{safe}.jpg"


def _og_image_context(base_id: str) -> dict:
    og_image_abs = _social_image_url(base_id)
    return {
        "og_image_abs": og_image_abs,
        "og_image_width": 1200,
        "og_image_height": 630,
    }


def _og_page_url(page_path: str) -> str:
    return f"{SITE_URL}{page_path}"


def _card_path(base_id: str, lang: str) -> str:
    path = f"/card/{base_id}"
    if lang == "ko":
        path += "?lang=ko"
    return path


def _linkedin_inspector_url(page_url: str) -> str:
    return f"https://www.linkedin.com/post-inspector/inspect/{quote(page_url, safe='')}"


def _share_context(slug: str, title: str, lang: str, page_path: str, base_id: str = "") -> dict:
    share_url = f"{SITE_URL}{page_path}"
    card_id = base_id or slug.rsplit("_", 1)[0]
    share_url_x = f"{SITE_URL}{_card_path(card_id, lang)}"
    if lang == "ko":
        share_tweet = f"{title} — OKCaddie"
    else:
        share_tweet = f"{title} — Japan golf guide on OKCaddie"
    return {
        "share_id": slug,
        "share_url": share_url,
        "share_url_x": share_url_x,
        "share_tweet": share_tweet,
        "share_lang": lang,
        "og_page_url": _og_page_url(page_path),
        "linkedin_inspector_url": _linkedin_inspector_url(share_url),
    }


def _jpeg_bytes(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=78, optimize=True, progressive=True)
    return buf.getvalue()


def _courses_by_base_lang():
    index = {}
    for c in CACHED_DATA.get("courses", []):
        bid = c.get("base_id") or split_localized_id(c.get("id", ""))[0]
        lang = c.get("lang", "en")
        index[(bid, lang)] = c
    return index


def _course_cards(base_ids, lang="en", limit=None):
    by_bl = _courses_by_base_lang()
    cards = []
    for bid in base_ids:
        c = by_bl.get((bid, lang)) or by_bl.get((bid, "en"))
        if not c:
            continue
        title = humanize_title(c.get("title", "")) or bid
        cards.append(
            enrich_item(
                {
                    "base_id": bid,
                    "lang": lang,
                    "link": course_href(bid, lang),
                    "title": title,
                    "short_title": truncate_text(title, 72),
                    "address": c.get("address", ""),
                    "thumbnail": _thumbnail_with_v(c.get("thumbnail", ""), c.get("published")),
                    "summary": short_summary(clean_summary(c.get("summary", ""), title, lang), 110),
                    "published": c.get("published", ""),
                }
            )
        )
        if limit and len(cards) >= limit:
            break
    return cards


def _crawl_course_links(limit=60, lang="en"):
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
            truncate_text(f"{title} | {hook} | OKCaddie", 60) if title else "일본 골프 가이드 | OKCaddie"
        )
    else:
        hook = "green fees, tee times & booking" if is_course else "Japan golf travel guide"
        tail = (
            " Green fees, Rakuten GORA booking, map & course tips on OKCaddie."
            if is_course
            else " Practical tips and course links for your Japan golf trip on OKCaddie."
        )
        default_title = (
            truncate_text(f"{title} | {hook} | OKCaddie", 60) if title else "Japan Golf Guide | OKCaddie"
        )

    post["seo_title"] = truncate_text(override_title, 60) if override_title else default_title
    if override_desc:
        post["seo_description"] = truncate_text(override_desc, 160)
    else:
        core = (summary or title).strip()
        post["seo_description"] = truncate_text(f"{core}{tail}", 155)
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


load_all_data()


@app.context_processor
def inject_site_url():
    n_courses = len(
        {c.get("base_id") or split_localized_id(c.get("id", ""))[0] for c in CACHED_DATA.get("courses", [])}
    )
    lang = request.args.get("lang", "en") if request else "en"
    return {
        "site_url": SITE_URL,
        "total_course_count": n_courses or len(CACHED_DATA.get("courses", [])),
        **inject_family_context(FAMILY_SITE_ID, lang),
    }


@app.before_request
def seo_url_normalization():
    if request.method != "GET":
        return None
    p = request.path
    if (
        p.startswith("/static/")
        or p.startswith("/api/")
        or p.startswith("/booking/")
        or p.startswith("/travel/")
    ):
        return None

    if request.headers.get("X-Forwarded-Proto", "").lower() == "http":
        return redirect(request.url.replace("http://", "https://", 1), code=301)

    args = request.args
    keys = set(args.keys())

    if p == "/" and keys == {"lang"} and args.get("lang") == "en":
        return redirect("/", code=301)
    if p == "/guide" and keys == {"lang"} and args.get("lang") == "en":
        return redirect("/guide", code=301)
    if p == "/about" and keys == {"lang"} and args.get("lang") == "en":
        return redirect("/about", code=301)
    if p == "/privacy" and keys == {"lang"} and args.get("lang") == "en":
        return redirect("/privacy", code=301)

    if p == "/courses":
        if keys == {"lang"} and args.get("lang") == "en":
            return redirect("/courses", code=301)
        if keys == {"lang", "page"} and args.get("lang") == "en":
            pg = args.get("page") or "1"
            if pg == "1":
                return redirect("/courses", code=301)
            return redirect(f"/courses?page={pg}", code=301)

    if p.startswith("/course/") and len(p) > len("/course/"):
        if keys == {"lang"} and args.get("lang") == "en":
            return redirect(p, code=301)
    if p.startswith("/guide/") and p != "/guide" and len(p) > len("/guide/"):
        if keys == {"lang"} and args.get("lang") == "en":
            return redirect(p, code=301)

    return None


@app.route("/")
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
        featured_courses=_course_cards(FEATURED_COURSE_BASE_IDS, lang=lang),
        crawl_course_links=_crawl_course_links(limit=60, lang=lang),
        active_lang=lang,
        google_maps_js_api_key=GOOGLE_MAPS_JS_API_KEY,
    )


@app.route("/about")
@app.route("/about.html")
def about():
    lang = request.args.get("lang", "en")
    return render_template("about.html", active_lang=lang)


@app.route("/privacy")
@app.route("/privacy.html")
def privacy():
    lang = request.args.get("lang", "en")
    return render_template("privacy.html", active_lang=lang)


@app.route("/api/courses")
def api_courses():
    ensure_course_cache()
    lang = request.args.get("lang", "en")
    filtered = []
    for c in CACHED_DATA.get("courses", []):
        if c.get("lang") == lang:
            temp = _public_course(c)
            temp["lang"] = lang
            temp["title"] = humanize_title(temp.get("title", ""))
            temp["summary"] = clean_summary(temp.get("summary", ""), temp["title"], lang)
            filtered.append(temp)
    if not filtered:
        filtered = [
            {
                **_public_course(c),
                "title": humanize_title(c.get("title", "")),
                "summary": clean_summary(
                    c.get("summary", ""),
                    humanize_title(c.get("title", "")),
                    c.get("lang", "en"),
                ),
            }
            for c in CACHED_DATA.get("courses", [])
        ]
    response = jsonify({"last_updated": CACHED_DATA.get("last_updated"), "courses": filtered})
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@app.route("/course/<course_ref>")
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
    post_data = _attach_seo_fields(post_data, page_kind="course")
    _enrich_course_detail_post(post_data)

    if isinstance(post_data.get("categories"), str):
        post_data["categories"] = [c.strip() for c in post_data["categories"].split(",")]

    cache_v = _thumbnail_cache_v(post_data.get("date") or post_data.get("published"))
    base_id_for_img = post_data.get("base_id") or base_id
    thumb = post_data.get("thumbnail") or f"/static/images/{base_id_for_img}.jpg"
    post_data["thumbnail"] = _thumbnail_with_v(thumb, cache_v)

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
        c = _public_course(course)
        c["title"] = humanize_title(c.get("title", ""))
        related_courses.append(c)

    related_guides = [g for g in CACHED_GUIDES if g.get("lang") == post_data["lang"]][:3]

    course_path = f"/course/{base_id}{'?lang=ko' if post_data['lang'] == 'ko' else ''}"
    share_ctx = _share_context(course_id, post_data["title"], post_data["lang"], course_path, base_id=base_id)

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
        **_og_image_context(base_id),
        **share_ctx,
    )


@app.route("/card/<course_ref>")
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
    post_data = _attach_seo_fields(post_data, page_kind="course")

    course_path = f"/course/{base_id}{'?lang=ko' if post_data['lang'] == 'ko' else ''}"
    card_path = _card_path(base_id, post_data["lang"])

    return render_template(
        "social_card.html",
        lang=post_data["lang"],
        title=post_data["title"],
        seo_title=post_data["seo_title"],
        seo_desc=post_data["seo_description"],
        page_url=f"{SITE_URL}{course_path}",
        card_url=f"{SITE_URL}{card_path}",
        **_og_image_context(base_id),
    )


@app.route("/courses")
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


@app.route("/guide")
def guide_list():
    lang = request.args.get("lang", "en")
    guides = [g for g in CACHED_GUIDES if g["lang"] == lang]
    return render_template("guide_list.html", guides=guides, lang=lang, active_lang=lang)


@app.route("/guide/<guide_ref>")
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

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
        if "---" in raw:
            raw = "---" + raw.split("---", 1)[1]
        post_obj = frontmatter.loads(raw)

    post_data = dict(post_obj.metadata)
    post_data["id"] = guide_id
    post_data["base_id"] = base_id
    post_data["lang"] = post_data.get("lang", "en").strip().lower()
    post_data["title"] = humanize_title(post_data.get("title", "")) or "Japan Golf Guide"
    post_data["summary"] = short_summary(
        clean_summary(post_data.get("summary", ""), post_data["title"], post_data["lang"]),
        200,
    )
    post_data = _attach_seo_fields(post_data, page_kind="guide")

    clean_body = re.sub(r"^(lang|title|summary|date):.*", "", post_obj.content, flags=re.MULTILINE).strip()
    clean_body = strip_llm_selfcheck(clean_body)

    html_content = markdown.markdown(clean_body, extensions=["tables", "fenced_code"])
    base_id = guide_id.rsplit("_", 1)[0]
    img_url = GUIDE_IMAGES[abs(hash(base_id) * 97) % len(GUIDE_IMAGES)]
    related_courses = _course_cards(
        GUIDE_RELATED_COURSES.get(guide_id, []),
        lang=post_data["lang"],
        limit=6,
    )

    guide_path = f"/guide/{base_id}{'?lang=ko' if post_data['lang'] == 'ko' else ''}"
    share_ctx = _share_context(guide_id, post_data["title"], post_data["lang"], guide_path)

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


@app.route("/booking/<course_id>")
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


@app.route("/travel/<item_type>/<course_id>")
def travel_redirect(item_type, course_id):
    is_ko = course_id.endswith("_ko")
    links = {
        "rental": "https://klook.tpo.mx/llRQoxrb" if is_ko else "https://klook.tpo.mx/skGztuAJ",
        "pickup": "https://klook.tpo.mx/8qLZKsBY" if is_ko else "https://klook.tpo.mx/zPN5kiip",
        "esim": "https://klook.tpo.mx/OBHJbySq" if is_ko else "https://klook.tpo.mx/696NKlPT",
    }
    return redirect(links.get(item_type, "https://klook.tpo.mx/470RSray"))


@app.route("/favicon.ico")
@app.route("/favicon-32x32.png")
@app.route("/favicon-48x48.png")
@app.route("/apple-touch-icon.png")
@app.route("/android-chrome-192x192.png")
@app.route("/android-chrome-512x512.png")
def serve_favicons():
    image_dir = os.path.join(app.root_path, "static", "images")
    filename = request.path[1:]
    if filename == "favicon.ico" and not os.path.exists(os.path.join(image_dir, filename)):
        filename = "favicons.ico"
    return send_from_directory(
        image_dir,
        filename,
        mimetype="image/png" if filename.endswith(".png") else "image/vnd.microsoft.icon",
    )


@app.route("/site.webmanifest")
def webmanifest():
    return send_from_directory(STATIC_DIR, "site.webmanifest", mimetype="application/manifest+json")


@app.route("/social/<slug>.jpg")
def social_image(slug):
    safe = re.sub(r"[^a-z0-9_-]", "", slug.lower())
    if not safe:
        abort(404)
    gcs_url = _gcs_image_url(f"{safe}.jpg")
    try:
        with urllib.request.urlopen(gcs_url, timeout=15) as resp:
            raw = resp.read()
            if not raw:
                abort(404)
    except Exception:
        abort(404)

    try:
        from PIL import Image, ImageOps

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        data = _jpeg_bytes(ImageOps.fit(img, (1200, 630), Image.Resampling.LANCZOS))
    except Exception:
        data = raw

    return Response(
        data,
        mimetype="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.route("/static/images/<path:filename>")
def serve_images(filename):
    images_root = os.path.join(app.root_path, "static", "images")
    if any(x in filename for x in ["favicon", "apple-touch"]):
        local_path = os.path.join(images_root, filename)
        if os.path.isfile(local_path):
            return send_from_directory(images_root, filename)
    url = f"https://storage.googleapis.com/ok-project-assets/okcaddie/{filename}"
    if request.query_string:
        url = f"{url}?{request.query_string.decode()}"
    return redirect(url, code=302)


@app.route("/sitemap.xml")
def sitemap_xml():
    now_iso = datetime.now(timezone.utc).date().isoformat()
    response = make_response(sitemap_index_xml(now_iso))
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/sitemap-courses.xml")
def sitemap_courses_xml():
    now_iso = datetime.now(timezone.utc).date().isoformat()
    response = make_response(render_urlset(course_sitemap_entries(now_iso)))
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/sitemap-guides.xml")
def sitemap_guides_xml():
    now_iso = datetime.now(timezone.utc).date().isoformat()
    response = make_response(render_urlset(guide_sitemap_entries(now_iso)))
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/sitemap-hub.xml")
def sitemap_hub_xml():
    now_iso = datetime.now(timezone.utc).date().isoformat()
    response = make_response(render_urlset(hub_sitemap_entries(now_iso)))
    response.headers["Content-Type"] = "application/xml"
    return response


@app.route("/robots.txt")
def robots_txt():
    return send_from_directory(STATIC_DIR, "robots.txt")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
