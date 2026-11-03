from app.a8_affiliate import a8_banners_context
from app.amazon_affiliate import AMAZON_GOLF_URL, amazon_kind, amazon_url


def _amazon_url(ctx):
    return next(b["click_url"] for b in ctx["a8_banners"] if b["id"] == "amazon_golf")


def test_amazon_kind_from_guide_id():
    assert amazon_kind("beginner-golf-japan") == "beginner"
    assert amazon_kind("autumn-leaves-golf") == "foliage"
    assert amazon_kind("autumn-foliage-golf-jp") == "foliage"
    assert amazon_kind("dress-code-guide") == "golf"
    assert amazon_kind(None) == "golf"


def test_amazon_urls_by_kind():
    assert amazon_url("golf") == AMAZON_GOLF_URL
    assert "tag=starful06-22" in amazon_url("beginner")
    assert "%E3%82%B4%E3%83%AB%E3%83%95%20%E5%88%9D%E5%BF%83%E8%80%85" in amazon_url("beginner")
    assert "%E3%82%A6%E3%82%A7%E3%82%A2" in amazon_url("foliage")


def test_banners_context_picks_keywords_and_keeps_rakuten_esim():
    assert _amazon_url(a8_banners_context(lang="en")) == AMAZON_GOLF_URL
    assert "%E5%88%9D%E5%BF%83%E8%80%85" in _amazon_url(
        a8_banners_context(lang="ja", guide_id="beginner-golf-japan")
    )
    ko = a8_banners_context(lang="ko", guide_id="autumn-leaves-golf")
    ids = [b["id"] for b in ko["a8_banners"]]
    assert ids == ["agoda", "amazon_golf", "rakuten_esim"]
    assert next(b for b in ko["a8_banners"] if b["id"] == "rakuten_esim")["click_url"] == "/go/rakuten_esim"


def test_enabled_env_fallback(monkeypatch):
    monkeypatch.delenv("AFFILIATE_OKCADDIE_ENABLED", raising=False)
    monkeypatch.setenv("A8_OKCADDIE_ENABLED", "0")
    assert a8_banners_context(lang="en")["show_a8_banners"] is False
    monkeypatch.setenv("AFFILIATE_OKCADDIE_ENABLED", "1")
    assert a8_banners_context(lang="en")["show_a8_banners"] is True
