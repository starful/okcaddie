"""Unit tests for text normalization helpers."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from text_utils import clean_summary, humanize_title, strip_llm_selfcheck  # noqa: E402


def test_humanize_title_strips_lang_suffix():
    assert humanize_title("Foo Club (en)") == "Foo Club"
    assert humanize_title("Foo Club (ko)") == "Foo Club"


def test_humanize_title_strips_review_boilerplate():
    result = humanize_title("The Definitive Guide to Hirono Golf Club: An Expert Review")
    assert "Hirono" in result
    assert "Expert Review" not in result


def test_clean_summary_replaces_promo_text():
    summary = "A comprehensive 9,000-character master guide to the course."
    result = clean_summary(summary, "ABC Golf Club", "en")
    assert "9,000" not in result
    assert "ABC Golf Club" in result


def test_strip_llm_selfcheck_removes_footer():
    body = "Course overview text.\n\n**Total character count check:** 8000"
    result = strip_llm_selfcheck(body)
    assert "Total character" not in result
    assert "Course overview" in result
