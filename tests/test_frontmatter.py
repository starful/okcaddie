"""Frontmatter lang/title validation tests."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from frontmatter_validate import validate_meta_text, validate_file  # noqa: E402


def test_en_rejects_korean_title():
    err = validate_meta_text("en", "title", "하코네 아시노코 CC 예약·그린피 가이드")
    assert err is not None
    assert "Korean-heavy" in err


def test_en_accepts_english_title():
    assert validate_meta_text("en", "title", "Ashinoko Country Club") is None


def test_ko_english_proper_noun_title_allowed():
    assert validate_meta_text("ko", "title", "Ashinoko Country Club Guide") is None


def test_fixed_ashinoko_en_passes():
    path = ROOT / "app" / "content" / "ashinoko_country_club_en.md"
    assert validate_file(str(path)) == []


def test_fixed_golf_etiquette_en_passes():
    path = ROOT / "app" / "content" / "guides" / "golf-etiquette-japan_en.md"
    assert validate_file(str(path)) == []
