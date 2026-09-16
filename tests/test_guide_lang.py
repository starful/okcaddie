"""Guide locale helpers must recognize ja, not collapse to en."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from guide_content import guide_id_parts  # noqa: E402
from ids import guide_href, split_localized_id  # noqa: E402


def test_guide_id_parts_detects_ja():
    base, lang = guide_id_parts("hokkaido-summer-golf_ja")
    assert base == "hokkaido-summer-golf"
    assert lang == "ja"


def test_guide_id_parts_ko_en():
    assert guide_id_parts("foo_ko") == ("foo", "ko")
    assert guide_id_parts("foo_en") == ("foo", "en")


def test_guide_href_ja():
    assert guide_href("tokyo-near-golf", "ja") == "/guide/tokyo-near-golf?lang=ja"
    assert guide_href("tokyo-near-golf", "en") == "/guide/tokyo-near-golf"


def test_split_localized_id_ja():
    assert split_localized_id("abc_ja") == ("abc", "ja")
