"""SEO regression tests (homepage crawl links, dynamic sitemap, API noindex)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from __init__ import app as flask_app  # noqa: E402


@pytest.fixture()
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_home_has_crawler_links_and_editor_picks(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "course-crawl-nav" in html
    assert "editor-picks-section" in html
    assert "/course/pgm_golf_resort_okinawa" in html


def test_api_courses_noindex(client):
    r = client.get("/api/courses")
    assert r.status_code == 200
    assert "noindex" in r.headers.get("X-Robots-Tag", "").lower()


def test_dynamic_sitemap_courses(client):
    r = client.get("/sitemap-courses.xml")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "<urlset" in body
    assert "pgm_golf_resort_okinawa" in body
    assert "<priority>0.85</priority>" in body


def test_reactions_api(client):
    r = client.get("/api/reactions/test-slug")
    assert r.status_code == 200
    data = r.get_json()
    assert "likes" in data
    assert "dislikes" in data


def test_course_detail_has_reaction_panel(client):
    r = client.get("/course/pgm_golf_resort_okinawa")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "reaction-panel" in html
    assert "/api/reactions/" in html
    assert "share-bar" in html
    assert "share-btn-x" in html
    assert "/social/pgm_golf_resort_okinawa.jpg" in html
    assert 'name="twitter:image"' in html


def test_social_image_endpoint(client):
    r = client.get("/social/pgm_golf_resort_okinawa.jpg")
    assert r.status_code == 200
    assert r.headers.get("Content-Type", "").startswith("image/jpeg")
    assert len(r.get_data()) > 1000
