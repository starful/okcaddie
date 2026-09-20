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


def test_home_pins_region_and_purpose_guides(client):
    r = client.get("/?lang=ko")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "region-guides-heading" in html
    assert "purpose-guides-heading" in html
    assert "/guide/okinawa-ocean-golf?lang=ko" in html
    assert "/guide/hokkaido-summer-golf?lang=ko" in html
    assert "/guide/value-for-money-golf?lang=ko" in html
    assert "홋카이도" in html
    assert "오키나와" in html
    assert "오사카 근교 가성비" in html
    assert "Mt. Fuji Golf Courses: Best Scenic Resorts" not in html
    assert "Latest Golf Guides" not in html


def test_okinawa_guide_related_courses_are_okinawa(client):
    r = client.get("/guide/okinawa-ocean-golf")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "/course/pgm_golf_resort_okinawa" in html
    assert "/course/kanucha_golf_course" in html


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


def test_course_ko_keeps_gora_and_one_partner_box(client):
    r = client.get("/course/pgm_golf_resort_okinawa?lang=ko")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "라쿠텐에서 골프 예약하기" in html
    assert "a8-banners" in html
    assert "Agoda — 골프장 주변 숙소" in html
    assert "라쿠텐 eSIM" in html
    assert "라쿠텐 트래블" in html
    assert 'href="/go/agoda"' in html
    assert 'href="/go/rakuten_travel"' in html
    assert 'href="/go/rakuten_esim"' in html
    assert 'href="/go/jalan_golf"' in html
    assert 'href="/go/fairway_golf"' in html
    assert 'href="/go/alpen_golf5"' not in html
    assert 'href="/go/victoria_golf"' not in html
    assert "じゃらんゴルフ" in html
    assert "Fairway Golf" in html
    assert "TORA" not in html
    assert "골프 여행 필수품" not in html
    assert "hinata" not in html.lower()


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
    assert "Disallow: /go/" in body


def test_ads_txt(client):
    r = client.get("/ads.txt")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "google.com, pub-8780435268193938, DIRECT, f08c47fec0942fa0" in body


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


def _gora_query(location: str) -> dict:
    from urllib.parse import parse_qs, unquote, urlparse

    wrapped = urlparse(location)
    pc = unquote(parse_qs(wrapped.query).get("pc", [""])[0])
    return parse_qs(urlparse(pc).query)


def test_gora_search_name_skips_en_ko_seo_titles():
    from routes.courses import gora_search_name

    assert gora_search_name(
        'title: "홋카이도 클래식 골프 클럽 마스터피스 리뷰"\n',
        from_course_md=True,
    ) == ""
    assert gora_search_name(
        "title: PGM Golf Resort Okinawa — Booking, Fees & Course Guide\n",
        from_course_md=True,
    ) == ""
    assert gora_search_name(
        'title: "PGMゴルフリゾート沖縄"\n',
        from_course_md=True,
    ) == "PGMゴルフリゾート沖縄"
    assert gora_search_name('title: "PGMゴルフリゾート沖縄"\n', from_course_md=False) == ""
    assert (
        gora_search_name(
            "title: PGM Golf Resort Okinawa\n",
            from_course_md=True,
            base_id="pgm_golf_resort_okinawa",
        )
        == "PGMゴルフリゾート沖縄"
    )
    assert (
        gora_search_name(
            'gora_name: "オーシャンキャッスルカントリークラブ"\ntitle: Ocean Castle\n',
            from_course_md=True,
        )
        == "オーシャンキャッスルカントリークラブ"
    )


def test_booking_redirect_uses_japanese_catalog_name(client):
    r = client.get("/booking/ocean_castle_golf_ko")
    assert r.status_code in (301, 302)
    loc = r.headers.get("Location", "")
    assert "hb.afl.rakuten.co.jp/hgc/" in loc
    from urllib.parse import parse_qs, unquote, urlparse

    dest = unquote(parse_qs(urlparse(loc).query).get("pc", [""])[0])
    assert "cal/disp/c_id/520083" in dest

    fuji = _gora_query(client.get("/booking/yamanashi_fuji_golf_en").headers.get("Location", ""))
    assert fuji.get("area[]") == ["19"]
    assert "search_c_name" not in fuji
    assert "Yamanashi Fuji Golf" not in client.get("/booking/yamanashi_fuji_golf_en").headers.get("Location", "")


def test_booking_area_not_stolen_from_body(client):
    hirono = _gora_query(client.get("/booking/hirono_golf_club_en").headers.get("Location", ""))
    assert hirono.get("area[]") == ["28"]
    assert hirono.get("search_c_name") == ["廣野ゴルフ倶楽部"]

    # Still on keyword search (no verified c_id yet).
    saga = _gora_query(client.get("/booking/sagamihara_golf_club_en").headers.get("Location", ""))
    assert saga.get("area[]") == ["14"]
    assert saga.get("search_c_name") == ["相模原ゴルフクラブ"]

    # Summary saying "Osaka" must not steal Hyogo from address.
    taka = _gora_query(client.get("/booking/takarazuka_golf_club_en").headers.get("Location", ""))
    assert taka.get("area[]") == ["28"]
    hanshin = _gora_query(client.get("/booking/hanshin_public_golf_en").headers.get("Location", ""))
    assert hanshin.get("area[]") == ["28"]


def test_japan_public_course_uses_gora_calendar_deep_link(client):
    from urllib.parse import parse_qs, unquote, urlparse

    r = client.get("/booking/pgm_golf_resort_okinawa_en")
    loc = r.headers.get("Location", "")
    assert r.status_code in (301, 302)
    dest = unquote(parse_qs(urlparse(loc).query).get("pc", [""])[0])
    assert "cal/disp/c_id/470006" in dest
    assert "search/result" not in dest

    abc = unquote(
        parse_qs(
            urlparse(client.get("/booking/abc_golf_club_en").headers.get("Location", "")).query
        ).get("pc", [""])[0]
    )
    assert "cal/disp/c_id/280028" in abc

    natsu = unquote(
        parse_qs(
            urlparse(
                client.get("/booking/natsudomari_golf_links_en").headers.get("Location", "")
            ).query
        ).get("pc", [""])[0]
    )
    assert "cal/disp/c_id/20008" in natsu

    totsuka = unquote(
        parse_qs(
            urlparse(client.get("/booking/totsuka_country_club_en").headers.get("Location", "")).query
        ).get("pc", [""])[0]
    )
    assert "cal/disp/c_id/140032" in totsuka


def test_affiliate_go_wraps_agoda(client):
    r = client.get("/go/agoda")
    assert r.status_code in (301, 302)
    assert "noindex" in r.headers.get("X-Robots-Tag", "").lower()
    assert "px.a8.net" in r.headers.get("Location", "")
    assert client.get("/go/not-a-banner").status_code == 404


def test_affiliate_go_wraps_new_golf_partners(client):
    # Visible partners + kept-but-hidden gear IDs still resolve via /go/.
    for banner_id, token in (
        ("jalan_golf", "1OQCCA"),
        ("fairway_golf", "1PBRY2"),
        ("alpen_golf5", "1X2ET6"),
        ("victoria_golf", "1LR6BE"),
    ):
        r = client.get(f"/go/{banner_id}")
        assert r.status_code in (301, 302)
        loc = r.headers.get("Location", "")
        assert "px.a8.net" in loc
        assert token in loc


def test_booking_omits_chiba_when_area_unknown(client):
    q = _gora_query(client.get("/booking/not_a_real_course_en").headers.get("Location", ""))
    assert "area[]" not in q
    assert "search_c_name" not in q


def test_legacy_travel_path_goes_to_gora_not_agoda(client):
    r = client.get("/travel/rental/pgm_golf_resort_okinawa_en")
    loc = r.headers.get("Location", "")
    assert r.status_code in (301, 302)
    assert "hb.afl.rakuten.co.jp/hgc/" in loc
    assert "a8.net" not in loc
    dest = _gora_query(loc)
    # Legacy /travel still goes to GORA affiliate; public courses deep-link to calendar.
    assert "hb.afl.rakuten.co.jp/hgc/" in loc
    from urllib.parse import parse_qs, unquote, urlparse

    pc = unquote(parse_qs(urlparse(loc).query).get("pc", [""])[0])
    assert "cal/disp/c_id/470006" in pc or dest.get("search_c_name") == ["PGMゴルフリゾート沖縄"]


def test_private_club_softens_gora_cta(client):
    r = client.get("/course/hirono_golf_club")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "Private club — public GORA booking may be limited" in html
    assert "Check GORA listing" in html
    assert 'class="booking-btn"' in html
    assert html.count("Check GORA listing") >= 1
    # Strong public CTA copy should not appear as the button label.
    assert ">Check on Rakuten GORA<" not in html
    assert "Book on Rakuten GORA" not in html


def test_public_course_keeps_strong_gora_cta(client):
    r = client.get("/course/pgm_golf_resort_okinawa")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert ">Check on Rakuten GORA<" in html or "Check on Rakuten GORA" in html
    assert "Book on Rakuten GORA" in html
    assert "Private club — public GORA booking may be limited" not in html


def test_overseas_booking_uses_gora_cid_not_japan_search(client):
    from urllib.parse import parse_qs, unquote, urlparse

    r = client.get("/booking/montgomerie_links_vietnam_en")
    loc = r.headers.get("Location", "")
    assert r.status_code in (301, 302)
    assert "noindex" in r.headers.get("X-Robots-Tag", "").lower()
    assert "hb.afl.rakuten.co.jp/hgc/" in loc
    dest = unquote(parse_qs(urlparse(loc).query).get("pc", [""])[0])
    assert "c_id/520472" in dest
    assert "search/result" not in dest
    assert "gora.golf.rakuten.co.jp/overseas" not in dest

    japan = client.get("/booking/pgm_golf_resort_okinawa_en").headers.get("Location", "")
    japan_pc = unquote(parse_qs(urlparse(japan).query).get("pc", [""])[0])
    assert "cal/disp/c_id/470006" in japan_pc
    assert "search/result" not in japan_pc


def test_overseas_course_page_keeps_gora_button(client):
    r = client.get("/course/montgomerie_links_vietnam")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "Check on Rakuten GORA" in html
    assert 'href="/booking/montgomerie_links_vietnam_en"' in html
    assert "Opens Rakuten GORA overseas booking" in html
    assert "addressCountry\": \"VN\"" in html or 'addressCountry": "VN"' in html

    ko = client.get("/course/montgomerie_links_vietnam?lang=ko")
    assert ko.status_code == 200
    ko_html = ko.get_data(as_text=True)
    assert "라쿠텐 GORA 해외 예약으로 연결됩니다" in ko_html
    assert "라쿠텐에서 골프 예약하기" in ko_html


def test_overseas_ja_page_and_booking(client):
    from urllib.parse import parse_qs, unquote, urlparse

    r = client.get("/course/montgomerie_links_vietnam?lang=ja")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "楽天GORAで予約" in html
    assert "楽天GORA海外予約へ移動します" in html
    assert 'hreflang="ja"' in html
    assert "このページは日本国内コースではありません" in html

    booking = client.get("/booking/montgomerie_links_vietnam_ja")
    loc = booking.headers.get("Location", "")
    assert booking.status_code in (301, 302)
    dest = unquote(parse_qs(urlparse(loc).query).get("pc", [""])[0])
    assert "c_id/520472" in dest

