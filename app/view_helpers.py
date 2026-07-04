"""Shared view-layer helpers for course/guide pages."""

from __future__ import annotations

import copy
import io
import re
from urllib.parse import quote

try:
    from .badges import enrich_item
    from .config import FEATURED_COURSE_BASE_IDS, GCS_ASSET_PREFIX, SITE_URL
    from .data_loader import CACHED_DATA
    from .ids import course_href, split_localized_id
    from .text_utils import clean_summary, humanize_title, short_summary, truncate_text
except ImportError:
    from badges import enrich_item
    from config import FEATURED_COURSE_BASE_IDS, GCS_ASSET_PREFIX, SITE_URL
    from data_loader import CACHED_DATA
    from ids import course_href, split_localized_id
    from text_utils import clean_summary, humanize_title, short_summary, truncate_text


def gcs_image_url(filename: str) -> str:
    return f"https://storage.googleapis.com/ok-project-assets/{GCS_ASSET_PREFIX}/{filename}"


def thumbnail_cache_v(published_or_date: str | None) -> str:
    v = str(published_or_date or "").strip()[:10]
    return v if len(v) >= 8 else ""


def thumbnail_with_v(url: str, cache_v: str | None = None) -> str:
    if not url:
        return url
    v = thumbnail_cache_v(cache_v)
    base = url.split("?", 1)[0]
    return f"{base}?v={v}" if v else base


def public_course(row: dict) -> dict:
    out = copy.deepcopy(row)
    out["thumbnail"] = thumbnail_with_v(out.get("thumbnail", ""), out.get("published"))
    return out


def social_image_url(slug: str) -> str:
    safe = re.sub(r"[^a-z0-9_-]", "", slug.lower())
    return f"{SITE_URL}/social/{safe}.jpg"


def og_image_context(base_id: str) -> dict:
    og_image_abs = social_image_url(base_id)
    return {
        "og_image_abs": og_image_abs,
        "og_image_width": 1200,
        "og_image_height": 630,
    }


def og_page_url(page_path: str) -> str:
    return f"{SITE_URL}{page_path}"


def card_path(base_id: str, lang: str) -> str:
    path = f"/card/{base_id}"
    if lang == "ko":
        path += "?lang=ko"
    return path


def linkedin_inspector_url(page_url: str) -> str:
    return f"https://www.linkedin.com/post-inspector/inspect/{quote(page_url, safe='')}"


def share_context(slug: str, title: str, lang: str, page_path: str, base_id: str = "") -> dict:
    share_url = f"{SITE_URL}{page_path}"
    card_id = base_id or slug.rsplit("_", 1)[0]
    share_url_x = f"{SITE_URL}{card_path(card_id, lang)}"
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
        "og_page_url": og_page_url(page_path),
        "linkedin_inspector_url": linkedin_inspector_url(share_url),
    }


def jpeg_bytes(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=78, optimize=True, progressive=True)
    return buf.getvalue()


def courses_by_base_lang():
    index = {}
    for c in CACHED_DATA.get("courses", []):
        bid = c.get("base_id") or split_localized_id(c.get("id", ""))[0]
        lang = c.get("lang", "en")
        index[(bid, lang)] = c
    return index


def course_cards(base_ids, lang="en", limit=None):
    by_bl = courses_by_base_lang()
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
                    "thumbnail": thumbnail_with_v(c.get("thumbnail", ""), c.get("published")),
                    "summary": short_summary(clean_summary(c.get("summary", ""), title, lang), 110),
                    "published": c.get("published", ""),
                }
            )
        )
        if limit and len(cards) >= limit:
            break
    return cards


def crawl_course_links(limit=60, lang="en"):
    by_bl = courses_by_base_lang()
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
        card = course_cards([bid], lang=lang, limit=1)
        if not card:
            continue
        links.append({"link": card[0]["link"], "label": card[0]["short_title"]})
    return links


def attach_seo_fields(post, page_kind="course"):
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


def detail_trust_copy(lang):
    if str(lang or "en").lower() == "ko":
        return (
            "본 글은 여행 계획용 에디토리얼 콘텐츠입니다. 공식 클럽 사이트가 아니므로 그린피·영업·예약 조건은 방문 전 라쿠텐 고라 또는 클럽에 반드시 확인하세요.",
            "상단 이미지는 이해를 돕기 위한 예시이며, 실제 코스 전경·시설과 다를 수 있습니다.",
        )
    return (
        "Editorial trip-planning content—not the club's official site. Confirm green fees, access, and tee times on Rakuten GORA or with the club before you book.",
        "Lead images are illustrative; actual course conditions and facilities may differ.",
    )


def enrich_course_detail_post(post):
    lang = str(post.get("lang") or "en")
    if not post.get("editorial_note") or not post.get("illustration_note"):
        ed, ill = detail_trust_copy(lang)
        if not post.get("editorial_note"):
            post["editorial_note"] = ed
        if not post.get("illustration_note"):
            post["illustration_note"] = ill
