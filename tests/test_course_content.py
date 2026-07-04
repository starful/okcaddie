from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from course_content import load_course_post_file, loads_course_post


def test_loads_course_post_repairs_embedded_frontmatter():
    raw = """---
date: "2026-07-04"
---

lang: "en"
title: "Sample Course"
lat: "35.1"
lng: "139.2"
categories: "Private Club, Championship"
thumbnail: "/static/images/sample_course.jpg"
address: "Tokyo, Japan"
summary: "Sample summary"
---

## Course Overview
Body starts here.
"""
    post, normalized = loads_course_post(raw)

    assert normalized is True
    assert post["lang"] == "en"
    assert post["title"] == "Sample Course"
    assert post["lat"] == "35.1"
    assert post["lng"] == "139.2"
    assert post.content.startswith("## Course Overview")


def test_load_course_post_file_reads_current_abiko_metadata():
    post, _ = load_course_post_file(str(ROOT / "app" / "content" / "abiko_golf_club_en.md"))

    assert post["lang"] == "en"
    assert post["title"]
    assert str(post["lat"]) == "35.8544"
    assert str(post["lng"]) == "140.0356"


def test_load_course_post_file_falls_back_to_sibling_metadata(tmp_path):
    ko_path = tmp_path / "sample_course_ko.md"
    ko_path.write_text(
        "---\n"
        "date: \"2026-07-04\"\n"
        "---\n\n"
        "# 샘플 코스\n\n"
        "본문입니다.\n",
        encoding="utf-8",
    )
    en_path = tmp_path / "sample_course_en.md"
    en_path.write_text(
        "---\n"
        "lang: \"en\"\n"
        "title: \"Sample Course\"\n"
        "lat: \"35.9\"\n"
        "lng: \"139.9\"\n"
        "categories: \"Private Club\"\n"
        "thumbnail: \"/static/images/sample_course.jpg\"\n"
        "address: \"Tokyo, Japan\"\n"
        "booking: \"/booking/sample_course_en\"\n"
        "---\n\n"
        "Body\n",
        encoding="utf-8",
    )

    post, changed = load_course_post_file(str(ko_path))

    assert changed is True
    assert post["lang"] == "ko"
    assert post["title"] == "샘플 코스"
    assert str(post["lat"]) == "35.9"
    assert str(post["lng"]) == "139.9"
    assert post["address"] == "Tokyo, Japan"
