"""Cross-check detail-page hreflang alternates against the sitemap feeds.

Both sitemap.py (sitemap-courses.xml / sitemap-guides.xml) and the detail
templates (via ids.available_course_langs / available_guide_langs) are meant
to advertise the exact same set of languages for a given base_id. This module
flags any base_id where they drift apart.
"""

from __future__ import annotations

try:
    from .data_loader import CACHED_DATA, CACHED_GUIDES, load_all_data
    from .ids import available_course_langs, available_guide_langs, split_localized_id
except ImportError:
    from data_loader import CACHED_DATA, CACHED_GUIDES, load_all_data
    from ids import available_course_langs, available_guide_langs, split_localized_id

_LANGS = ("en", "ko", "ja")


def _sitemap_course_langs() -> dict[str, set[str]]:
    by_base: dict[str, set[str]] = {}
    for c in CACHED_DATA.get("courses", []):
        bid = c.get("base_id") or split_localized_id(c.get("id", ""))[0]
        lang = c.get("lang", "en")
        if lang in _LANGS:
            by_base.setdefault(bid, set()).add(lang)
    return by_base


def _sitemap_guide_langs() -> dict[str, set[str]]:
    by_base: dict[str, set[str]] = {}
    for g in CACHED_GUIDES:
        bid = g.get("base_id") or split_localized_id(g.get("id", ""))[0]
        lang = g.get("lang", "en")
        if lang in _LANGS:
            by_base.setdefault(bid, set()).add(lang)
    return by_base


def collect_hreflang_mismatches() -> list[str]:
    """Return human-readable mismatches between sitemap langs and page hreflang langs."""
    if not CACHED_DATA.get("courses") and not CACHED_GUIDES:
        load_all_data()

    errors: list[str] = []

    for bid, sitemap_langs in sorted(_sitemap_course_langs().items()):
        page_langs = set(available_course_langs(bid))
        if page_langs != sitemap_langs:
            errors.append(
                f"course/{bid}: sitemap-courses.xml has {sorted(sitemap_langs)} "
                f"but detail.html hreflang would emit {sorted(page_langs)}"
            )

    for bid, sitemap_langs in sorted(_sitemap_guide_langs().items()):
        page_langs = set(available_guide_langs(bid))
        if page_langs != sitemap_langs:
            errors.append(
                f"guide/{bid}: sitemap-guides.xml has {sorted(sitemap_langs)} "
                f"but guide_detail.html hreflang would emit {sorted(page_langs)}"
            )

    return errors
