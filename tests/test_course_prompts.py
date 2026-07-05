"""Course prompt and short-target discovery tests."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "script"))

from course_prompts import MIN_BODY_CHARS, build_course_prompt  # noqa: E402
from expand_short_courses import find_short_targets  # noqa: E402


def test_build_course_prompt_requests_6k_minimum():
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
    assert "6,000 to 9,000 characters" in prompt
    assert str(MIN_BODY_CHARS) in prompt
    assert "## Layout & Strategy" in prompt


def test_find_short_targets_none_under_threshold_after_expand():
    targets = find_short_targets(min_chars=6000, langs=("en", "ko"))
    assert targets == []
