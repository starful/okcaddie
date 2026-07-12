"""Shared quality gates for generated course/guide markdown.

Keeps new Gemini output aligned with the 2026-07 content cleanup:
practical booking-focused pages, no seed/expand fluff, no cafe-as-course.
"""

from __future__ import annotations

import re

# Topic IDs that must never be generated again (deleted / off-brand).
BLOCKED_GUIDE_IDS = frozenset(
    {
        "guide_seed_001",
        "guide_seed_002",
        "guide_seed_003",
        "guide_expand_001",
        "guide_expand_002",
        "guide_expand_003",
        "guide_expand_004",
        "guide_expand_005",
        "guide_expand_006",
        "guide_expand_007",
        "guide_expand_008",
        "guide_expand_009",
        "best-souvenirs-proshop",
        "chipping-and-putting-practice",
        "golf-insurance-for-travelers",
        "kanto-vs-kansai-golf",
        "rental-clubs-japan",
        "self-play-vs-caddy",
        "spring-cherry-blossom-golf",
        "stay-and-play-karuizawa",
        "trash-and-smoking-rules",
    }
)

BLOCKED_GUIDE_ID_PREFIXES = ("guide_seed_", "guide_expand_")

# Slug / name markers for non-golf "cafe course" rows.
NON_GOLF_SLUG_MARKERS = (
    "cafe",
    "latte",
    "roast",
    "espresso",
    "kissaten",
    "dessert",
    "bakery",
    "coffee",
)

# Phrases that mark the old mass-produced masterclass voice.
BANNED_PHRASES = (
    "as an elite",
    "elite japanese golf",
    "two decades of",
    "with two decades",
    "hole-by-hole masterclass",
    "historical prestige",
    "definitive guide",
    "expert review",
    "masterpiece review",
    "symphony of challenge",
    "character-by-character",
    "unforgettable pilgrimage",
    "masterclass,",
    "20년 경력",
    "마스터피스",
    "심층 마스터",
    "elite golf course rater",
)

REQUIRED_COURSE_H2_HINTS = (
    ("overview", "quick fact", "한눈에", "코스 개요", "quick facts"),
    ("fee", "booking", "green fee", "요금", "예약", "그린피"),
    ("access", "접근", "getting there"),
)

REQUIRED_GUIDE_H2_HINTS = (
    ("who", "for", "대상", "이런"),
    ("how", "step", "방법", "흐름", "tips", "팁"),
    ("bottom", "summary", "정리", "key takeaway"),
)


def is_blocked_guide_id(topic_id: str) -> bool:
    tid = (topic_id or "").strip().lower()
    if not tid:
        return True
    if tid in BLOCKED_GUIDE_IDS:
        return True
    return any(tid.startswith(p) for p in BLOCKED_GUIDE_ID_PREFIXES)


def is_non_golf_course_slug(safe_name: str, display_name: str = "") -> bool:
    blob = f"{safe_name} {display_name}".lower()
    return any(m in blob for m in NON_GOLF_SLUG_MARKERS)


def find_banned_phrases(text: str) -> list[str]:
    low = (text or "").lower()
    hits = []
    for phrase in BANNED_PHRASES:
        if phrase.lower() in low:
            hits.append(phrase)
    return hits


def _h2_lines(body: str) -> list[str]:
    return [ln.strip().lower() for ln in (body or "").splitlines() if ln.startswith("## ")]


def missing_required_h2(body: str, hint_groups: tuple[tuple[str, ...], ...]) -> list[str]:
    """Return hint-group labels that are missing from H2 headings."""
    headings = " | ".join(_h2_lines(body))
    missing = []
    for group in hint_groups:
        if not any(h in headings for h in group):
            missing.append("/".join(group[:2]))
    return missing


def validate_course_body(body: str) -> list[str]:
    errors = []
    banned = find_banned_phrases(body)
    if banned:
        errors.append(f"banned phrases: {', '.join(banned[:3])}")
    missing = missing_required_h2(body, REQUIRED_COURSE_H2_HINTS)
    if missing:
        errors.append(f"missing H2 themes: {', '.join(missing)}")
    return errors


def validate_guide_body(body: str, *, topic_name: str = "") -> list[str]:
    errors = []
    banned = find_banned_phrases(body)
    if banned:
        errors.append(f"banned phrases: {', '.join(banned[:3])}")
    missing = missing_required_h2(body, REQUIRED_GUIDE_H2_HINTS)
    if missing:
        errors.append(f"missing H2 themes: {', '.join(missing)}")
    # Soft golf relevance: body should mention golf somehow for travel guides
    blob = f"{topic_name}\n{body}".lower()
    if "golf" not in blob and "골프" not in blob:
        errors.append("not golf-related (missing golf/골프)")
    return errors


def strip_code_fences(text: str) -> str:
    text = re.sub(r"^```(?:markdown|yaml)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text.strip())
    return text.replace("## yaml", "").strip()
