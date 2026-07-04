"""Dynamic sitemap generation for runtime routes."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from xml.sax.saxutils import escape

try:
    from .config import FEATURED_COURSE_BASE_IDS, SITE_URL
    from .data_loader import CACHED_DATA, CACHED_GUIDES
    from .ids import course_href, split_localized_id
    from .paths import BASE_DIR, CONTENT_DIR, GUIDE_DIR
except ImportError:
    from config import FEATURED_COURSE_BASE_IDS, SITE_URL
    from data_loader import CACHED_DATA, CACHED_GUIDES
    from ids import course_href, split_localized_id
    from paths import BASE_DIR, CONTENT_DIR, GUIDE_DIR


def safe_iso_date(value, fallback):
    if not value:
        return fallback
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return fallback


def file_lastmod(path, fallback):
    if not os.path.exists(path):
        return fallback
    ts = os.path.getmtime(path)
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def xml_url_block(loc, lastmod, changefreq, priority, alternates=None):
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


def course_sitemap_entries(now_iso):
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
        path = course_href(bid, lang)
        if path in seen_paths:
            continue
        seen_paths.add(path)
        course_id = c.get("id") or f"{bid}_{lang}"
        md_path = os.path.join(CONTENT_DIR, f"{course_id}.md")
        fallback = safe_iso_date(c.get("published"), now_iso)
        lastmod = file_lastmod(md_path, fallback)
        priority = "0.85" if bid in FEATURED_COURSE_BASE_IDS else "0.7"
        alternates = []
        if (bid, "en") in grouped:
            alternates.append(("en", f"{SITE_URL}{course_href(bid, 'en')}"))
        if (bid, "ko") in grouped:
            alternates.append(("ko", f"{SITE_URL}{course_href(bid, 'ko')}"))
        xd = f"{SITE_URL}{course_href(bid, 'en')}"
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


def guide_sitemap_entries(now_iso):
    entries = []
    for g in CACHED_GUIDES:
        base_id = g.get("base_id") or split_localized_id(g.get("id", ""))[0]
        lang = g.get("lang", "en")
        path = f"/guide/{base_id}" + ("?lang=ko" if lang == "ko" else "")
        guide_id = g.get("id") or f"{base_id}_{lang}"
        md_path = os.path.join(GUIDE_DIR, f"{guide_id}.md")
        fallback = safe_iso_date(g.get("date"), now_iso)
        lastmod = file_lastmod(md_path, fallback)
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


def render_urlset(entries):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for e in entries:
        lines.extend(
            xml_url_block(
                e["loc"],
                e["lastmod"],
                e["changefreq"],
                e["priority"],
                e.get("alternates"),
            )
        )
    lines.append("</urlset>")
    return "\n".join(lines)


def hub_sitemap_entries(now_iso):
    about_lastmod = file_lastmod(os.path.join(BASE_DIR, "templates", "about.html"), now_iso)
    privacy_lastmod = file_lastmod(os.path.join(BASE_DIR, "templates", "privacy.html"), now_iso)
    course_entries = course_sitemap_entries(now_iso)
    guide_entries = guide_sitemap_entries(now_iso)
    latest_course = max((e["lastmod"] for e in course_entries), default=now_iso)
    latest_guide = max((e["lastmod"] for e in guide_entries), default=now_iso)
    home_mod = max(latest_course, latest_guide)

    return [
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


def sitemap_index_xml(now_iso):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for name in ("sitemap-hub.xml", "sitemap-courses.xml", "sitemap-guides.xml"):
        lines.extend(
            [
                "  <sitemap>",
                f"    <loc>{escape(f'{SITE_URL}/{name}')}</loc>",
                f"    <lastmod>{escape(now_iso)}</lastmod>",
                "  </sitemap>",
            ]
        )
    lines.append("</sitemapindex>")
    return "\n".join(lines)
