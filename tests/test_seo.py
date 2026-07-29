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
    data = r.get_json()
    assert data["courses"]
    assert "is_new" in data["courses"][0]


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
    assert "?v=" not in html.split('name="twitter:image"')[1][:120]
    assert 'name="twitter:image"' in html
    assert "card/pgm_golf_resort_okinawa" in html


def test_social_image_endpoint(client):
    r = client.get("/social/pgm_golf_resort_okinawa.jpg")
    assert r.status_code == 200
    assert r.headers.get("Content-Type", "").startswith("image/jpeg")
    assert len(r.get_data()) > 1000


def test_social_card_page(client):
    r = client.get("/card/pgm_golf_resort_okinawa")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'name="robots" content="noindex,follow"' in html
    assert 'rel="canonical" href="https://okcaddie.net/course/pgm_golf_resort_okinawa"' in html
    assert 'property="og:url" content="https://okcaddie.net/card/pgm_golf_resort_okinawa"' in html
    assert "/social/pgm_golf_resort_okinawa.jpg" in html
    assert "?v=" not in html.split('name="twitter:image"')[1][:120]
    assert "View course guide" in html


def test_robots_txt_disallows_affiliate_paths(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Disallow: /api/" in body
    assert "Disallow: /booking/" in body
    assert "Disallow: /travel/" in body


def test_booking_and_travel_noindex(client):
    r = client.get("/booking/pgm_golf_resort_okinawa_en")
    assert r.status_code in (301, 302)
    assert "noindex" in r.headers.get("X-Robots-Tag", "").lower()
    r2 = client.get("/travel/rental/pgm_golf_resort_okinawa_en")
    assert r2.status_code in (301, 302)
    assert "noindex" in r2.headers.get("X-Robots-Tag", "").lower()


def test_card_guide_slug_redirects(client):
    r = client.get("/card/luxury-golf-experience")
    assert r.status_code == 301
    assert r.headers["Location"].endswith("/guide/luxury-golf-experience")


def test_retired_cafe_course_redirects(client):
    r = client.get("/course/kobe_harborland_cafe")
    assert r.status_code == 301
    assert "/courses" in r.headers["Location"]


def test_sample_golf_club_excluded_from_sitemap(client):
    r = client.get("/sitemap-courses.xml")
    assert r.status_code == 200
    assert "sample_golf_club" not in r.get_data(as_text=True)


def test_lang_en_query_redirects(client):
    r = client.get("/course/pgm_golf_resort_okinawa?lang=en")
    assert r.status_code == 301
    assert r.headers["Location"].endswith("/course/pgm_golf_resort_okinawa")


def test_legacy_suffix_redirects(client):
    r = client.get("/course/pgm_golf_resort_okinawa_en")
    assert r.status_code == 301
    assert r.headers["Location"].endswith("/course/pgm_golf_resort_okinawa")
    r_ko = client.get("/course/pgm_golf_resort_okinawa_ko")
    assert r_ko.status_code == 301
    assert r_ko.headers["Location"].endswith("/course/pgm_golf_resort_okinawa?lang=ko")


def test_retired_guide_legacy_suffix_single_hop(client):
    r = client.get("/guide/golf-score-terms-japanese_ko")
    assert r.status_code == 301
    assert r.headers["Location"].endswith("/guide/understanding-scorecards?lang=ko")

