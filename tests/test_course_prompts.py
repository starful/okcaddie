"""Course/guide prompt and content-quality tests."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "script"))

from content_quality import (  # noqa: E402
    find_banned_phrases,
    is_blocked_guide_id,
    is_non_golf_course_slug,
    validate_course_body,
    validate_guide_body,
)
from course_prompts import MIN_BODY_CHARS, build_course_prompt  # noqa: E402
from expand_short_courses import find_short_targets  # noqa: E402
from guide_prompts import build_guide_prompt  # noqa: E402


def test_build_course_prompt_requests_practical_structure():
    prompt = build_course_prompt(
        {
            "lang": "en",
            "safe_name": "sample_golf_club",
            "name": "Sample Golf Club",
            "lat": "35.0",
            "lng": "139.0",
            "address": "Tokyo",
            "features": "Public",
        }
    )
    assert "3,500 to 7,000 characters" in prompt
    assert str(MIN_BODY_CHARS) in prompt
    assert "## Quick Facts" in prompt
    assert "## Green Fees & Booking" in prompt
    assert "Hole-by-Hole Masterclass" in prompt  # banned list mention
    assert "as an elite" in prompt


def test_build_guide_prompt_blocks_fluff_voice():
    prompt = build_guide_prompt(
        topic_id="booking-tips-japan",
        topic_name="How to book golf in Japan",
        lang="en",
        keywords="rakuten gora, tee time",
        today="2026-07-12",
    )
    assert "date: \"2026-07-12\"" in prompt
    assert "## Bottom Line" in prompt
    assert "SKIP_NOT_GOLF" in prompt
    assert "as an elite" in prompt


def test_blocked_guide_ids():
    assert is_blocked_guide_id("guide_seed_001")
    assert is_blocked_guide_id("guide_expand_008")
    assert is_blocked_guide_id("kanto-vs-kansai-golf")
    assert not is_blocked_guide_id("booking-tips-japan")


def test_non_golf_course_slug():
    assert is_non_golf_course_slug("kobe_harborland_cafe", "Kobe Harborland Cafe")
    assert is_non_golf_course_slug("asahikawa_winter_roast")
    assert not is_non_golf_course_slug("pgm_golf_resort_okinawa", "PGM Golf Resort Okinawa")


def test_validate_course_body_rejects_masterclass_voice():
    bad = """
## Quick Facts
x
## Who This Course Is For
x
## Course Overview
As an elite Japanese golf rater with two decades of experience...
## Green Fees & Booking
x
## Access
x
## Dress Code & Tips
x
## Bottom Line
x
"""
    errs = validate_course_body(bad)
    assert errs
    assert find_banned_phrases(bad)


def test_validate_guide_body_requires_golf():
    body = """
## Quick Facts
tea ceremony tips
## Who This Guide Is For
tourists
## How It Works / Steps
1. drink tea
## Costs & Booking Reality
n/a
## Common Mistakes
- none
## Bottom Line
enjoy tea
"""
    errs = validate_guide_body(body, topic_name="Tokyo tea")
    assert any("golf" in e.lower() for e in errs)


def test_find_short_targets_callable():
    # Threshold mirrors generator gate; rewritten practical pages may sit near the floor.
    targets = find_short_targets(min_chars=MIN_BODY_CHARS, langs=("en",))
    assert isinstance(targets, list)
    for item in targets:
        assert len(item) == 3
