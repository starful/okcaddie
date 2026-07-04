import os
import json
import sys
import frontmatter
import markdown
from bs4 import BeautifulSoup
from datetime import datetime
from xml.sax.saxutils import escape

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
BASE_DIR     = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)
APP_DIR      = os.path.join(BASE_DIR, 'app')
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from config import FEATURED_COURSE_BASE_IDS_SET as FEATURED_COURSE_BASE_IDS  # noqa: E402
from course_content import load_course_post_file  # noqa: E402
from md_dates import ensure_post_date, save_post  # noqa: E402
from text_utils import humanize_title  # noqa: E402
CONTENT_DIR  = os.path.join(BASE_DIR, 'app', 'content')        # 코스 마크다운
GUIDE_DIR    = os.path.join(CONTENT_DIR, 'guides')            # 가이드 마크다운
STATIC_DIR   = os.path.join(BASE_DIR, 'app', 'static')
JSON_OUTPUT  = os.path.join(STATIC_DIR, 'json', 'courses_data.json')
SITEMAP_OUT          = os.path.join(STATIC_DIR, 'sitemap.xml')           # 사이트맵 인덱스
SITEMAP_COURSES_OUT  = os.path.join(STATIC_DIR, 'sitemap-courses.xml')
SITEMAP_GUIDES_OUT   = os.path.join(STATIC_DIR, 'sitemap-guides.xml')
SITEMAP_HUB_OUT      = os.path.join(STATIC_DIR, 'sitemap-hub.xml')
BASE_URL     = 'https://okcaddie.net'

def strip_markdown(text):
    """마크다운/HTML 태그를 제거하고 순수 텍스트만 추출 (BeautifulSoup 사용)"""
    try:
        html = markdown.markdown(text)
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text()
    except Exception:
        return text

# ==========================================
# 🗺️ Sitemap 빌더
# ==========================================
def _xml_url_block(path, lastmod, changefreq, priority, alternates=None):
    out = ["  <url>"]
    out.append(f"    <loc>{escape(BASE_URL + path)}</loc>")
    if alternates:
        for lang_code, alt_path in alternates:
            href = BASE_URL + alt_path
            out.append(
                f'    <xhtml:link rel="alternate" hreflang="{escape(lang_code)}" href="{escape(href)}" />'
            )
    out.append(f"    <lastmod>{escape(lastmod)}</lastmod>")
    out.append(f"    <changefreq>{changefreq}</changefreq>")
    out.append(f"    <priority>{priority}</priority>")
    out.append("  </url>")
    return out

def _xml_open():
    return [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]

def _xml_close():
    return ['</urlset>']

def build_hub_sitemap(latest_course_date, latest_guide_date, fixed_date):
    """홈/허브 페이지: 실제 변동 시점에 가깝게 lastmod 산정 (오늘 날짜 일괄 업데이트 X)."""
    hub_alts_home = [("en", "/"), ("ko", "/?lang=ko"), ("x-default", "/")]
    hub_alts_guide = [("en", "/guide"), ("ko", "/guide?lang=ko"), ("x-default", "/guide")]
    hub_alts_courses = [("en", "/courses"), ("ko", "/courses?lang=ko"), ("x-default", "/courses")]
    hub_alts_about = [("en", "/about"), ("ko", "/about?lang=ko"), ("x-default", "/about")]
    hub_alts_privacy = [("en", "/privacy"), ("ko", "/privacy?lang=ko"), ("x-default", "/privacy")]

    home_mod = max(latest_course_date, latest_guide_date) if (latest_course_date and latest_guide_date) else (latest_course_date or latest_guide_date or fixed_date)

    xml = _xml_open()
    xml.extend(_xml_url_block("/", home_mod, "daily", "1.0", hub_alts_home))
    xml.extend(_xml_url_block("/?lang=ko", home_mod, "daily", "0.9", hub_alts_home))
    xml.extend(_xml_url_block("/courses", latest_course_date or fixed_date, "weekly", "0.9", hub_alts_courses))
    xml.extend(_xml_url_block("/courses?lang=ko", latest_course_date or fixed_date, "weekly", "0.8", hub_alts_courses))
    xml.extend(_xml_url_block("/guide", latest_guide_date or fixed_date, "weekly", "0.9", hub_alts_guide))
    xml.extend(_xml_url_block("/guide?lang=ko", latest_guide_date or fixed_date, "weekly", "0.8", hub_alts_guide))
    xml.extend(_xml_url_block("/about", fixed_date, "monthly", "0.4", hub_alts_about))
    xml.extend(_xml_url_block("/about?lang=ko", fixed_date, "monthly", "0.35", hub_alts_about))
    xml.extend(_xml_url_block("/privacy", fixed_date, "monthly", "0.4", hub_alts_privacy))
    xml.extend(_xml_url_block("/privacy?lang=ko", fixed_date, "monthly", "0.35", hub_alts_privacy))
    xml.extend(_xml_close())
    return "\n".join(xml)

def build_detail_sitemap(urls, kind):
    """코스/가이드 상세 sitemap. lastmod = frontmatter 날짜를 그대로 사용 (오늘로 매번 갱신 금지)."""
    grouped = {}
    for entry in urls:
        if entry.get("kind") != kind:
            continue
        key = (entry.get("base_id", ""), entry.get("lang", ""))
        grouped[key] = entry

    xml = _xml_open()
    for entry in urls:
        if entry.get("kind") != kind:
            continue
        path = entry["url"]
        date_val = entry.get("date") or entry.get("fallback_date")
        base_id = entry.get("base_id", "")
        en_key = (base_id, "en")
        ko_key = (base_id, "ko")
        alternates = []
        if en_key in grouped:
            alternates.append(("en", grouped[en_key]["url"]))
        if ko_key in grouped:
            alternates.append(("ko", grouped[ko_key]["url"]))
        xd = grouped[en_key]["url"] if en_key in grouped else path
        alternates.append(("x-default", xd))
        xml.extend(_xml_url_block(
            path,
            date_val,
            entry.get("changefreq", "monthly"),
            entry.get("priority", "0.7"),
            alternates,
        ))
    xml.extend(_xml_close())
    return "\n".join(xml)

def build_sitemap_index(today):
    """Google이 처음 받는 인덱스. 각 sub-sitemap이 자체 lastmod를 가지므로 여기서는 today 사용 OK."""
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for name in ("sitemap-hub.xml", "sitemap-courses.xml", "sitemap-guides.xml"):
        xml.append("  <sitemap>")
        xml.append(f"    <loc>{escape(f'{BASE_URL}/{name}')}</loc>")
        xml.append(f"    <lastmod>{escape(today)}</lastmod>")
        xml.append("  </sitemap>")
    xml.append('</sitemapindex>')
    return "\n".join(xml)

# ==========================================
# 🔨 메인 빌드
# ==========================================
def main():
    print("🔨 OKCaddie 데이터 및 사이트맵 빌드 시작")
    today = datetime.now().strftime("%Y-%m-%d")
    fixed_date = "2026-04-15"  # 정적 허브(about/privacy) lastmod 전용

    courses_for_json = []
    urls_for_sitemap = []
    latest_course_date = ""
    latest_guide_date = ""
    backfilled = 0

    os.makedirs(os.path.dirname(JSON_OUTPUT), exist_ok=True)

    # ------------------------------------------
    # 1. 골프장 코스 데이터 처리
    # ------------------------------------------
    if os.path.exists(CONTENT_DIR):
        print("📂 코스 데이터 수집 중...")
        for filename in os.listdir(CONTENT_DIR):
            if not filename.endswith('.md') or filename.startswith('_'):
                continue
            filepath = os.path.join(CONTENT_DIR, filename)
            try:
                post, normalized = load_course_post_file(filepath)

                date_val, changed = ensure_post_date(post, filepath)
                if changed or normalized:
                    save_post(filepath, post)
                if changed:
                    backfilled += 1

                try:
                    lat = float(post.get('lat', 0))
                    lng = float(post.get('lng', 0))
                except (ValueError, TypeError):
                    lat, lng = 0.0, 0.0

                if lat == 0.0:
                    continue

                course_id = filename.replace('.md', '')
                if date_val > latest_course_date:
                    latest_course_date = date_val

                summary = post.get('summary', '')
                if not summary:
                    summary = strip_markdown(post.content)[:120] + '...'

                cats = post.get('categories', [])
                if isinstance(cats, str):
                    cats = [c.strip() for c in cats.split(',')]

                base_id = course_id.rsplit('_', 1)[0] if '_' in course_id else course_id
                course_data = {
                    "id": course_id,
                    "base_id": base_id,
                    "lang": post.get('lang', 'en'),
                    "title": humanize_title(post.get('title', 'No Title')),
                    "lat": lat,
                    "lng": lng,
                    "categories": cats,
                    "thumbnail": post.get('thumbnail', f"/static/images/{base_id}.jpg"),
                    "address": post.get('address', ''),
                    "published": date_val,
                    "summary": summary,
                    "booking": post.get('booking', ''),
                    "link": (
                        f"/course/{base_id}"
                        + ("" if post.get('lang', 'en') == 'en' else "?lang=ko")
                    ),
                }
                courses_for_json.append(course_data)

                _clang = post.get('lang', 'en')
                _cpath = f"/course/{base_id}" if _clang == 'en' else f"/course/{base_id}?lang=ko"
                urls_for_sitemap.append({
                    "url": _cpath,
                    "date": date_val,
                    "lang": _clang,
                    "base_id": base_id,
                    "kind": "course",
                    "changefreq": "weekly",
                    "priority": "0.85" if base_id in FEATURED_COURSE_BASE_IDS else "0.7",
                })
            except Exception as e:
                print(f"  ❌ 코스 오류 ({filename}): {e}")

    # ------------------------------------------
    # 2. AI 가이드 데이터 처리
    # ------------------------------------------
    if os.path.exists(GUIDE_DIR):
        print("📂 가이드 데이터 수집 중...")
        for filename in os.listdir(GUIDE_DIR):
            if not filename.endswith('.md'):
                continue
            guide_id = filename.replace('.md', '')
            filepath = os.path.join(GUIDE_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                date_val, changed = ensure_post_date(post, filepath)
                if changed:
                    save_post(filepath, post)
                    backfilled += 1
                if date_val > latest_guide_date:
                    latest_guide_date = date_val
                base_id = guide_id.rsplit('_', 1)[0] if '_' in guide_id else guide_id
                _glang = post.get('lang', 'en')
                _gpath = f"/guide/{base_id}" if _glang == 'en' else f"/guide/{base_id}?lang=ko"
                urls_for_sitemap.append({
                    "url": _gpath,
                    "date": date_val,
                    "lang": _glang,
                    "base_id": base_id,
                    "kind": "guide",
                    "changefreq": "monthly",
                    "priority": "0.7",
                })
            except Exception:
                base_id = guide_id.rsplit('_', 1)[0] if '_' in guide_id else guide_id
                lang = 'ko' if guide_id.endswith('_ko') else 'en'
                _gpath_fb = f"/guide/{base_id}" if lang == 'en' else f"/guide/{base_id}?lang=ko"
                urls_for_sitemap.append({
                    "url": _gpath_fb,
                    "date": fixed_date,
                    "lang": lang,
                    "base_id": base_id,
                    "kind": "guide",
                    "changefreq": "monthly",
                    "priority": "0.7",
                })

    # ------------------------------------------
    # 3. JSON 저장
    # ------------------------------------------
    courses_for_json.sort(key=lambda x: (x['published'], x['id']), reverse=True)
    final_json = {
        "last_updated": datetime.now().strftime("%Y.%m.%d"),
        "courses": courses_for_json,
    }
    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON 생성 완료: {len(courses_for_json)}개 코스")
    if backfilled:
        print(f"📅 date 백필: {backfilled}개 MD")

    # ------------------------------------------
    # 4. Sitemap 분할 저장
    # ------------------------------------------
    courses_xml = build_detail_sitemap(urls_for_sitemap, kind="course")
    guides_xml  = build_detail_sitemap(urls_for_sitemap, kind="guide")
    hub_xml     = build_hub_sitemap(latest_course_date, latest_guide_date, fixed_date)
    index_xml   = build_sitemap_index(today)

    with open(SITEMAP_COURSES_OUT, 'w', encoding='utf-8') as f:
        f.write(courses_xml)
    with open(SITEMAP_GUIDES_OUT, 'w', encoding='utf-8') as f:
        f.write(guides_xml)
    with open(SITEMAP_HUB_OUT, 'w', encoding='utf-8') as f:
        f.write(hub_xml)
    with open(SITEMAP_OUT, 'w', encoding='utf-8') as f:
        f.write(index_xml)

    n_course = sum(1 for u in urls_for_sitemap if u.get("kind") == "course")
    n_guide = sum(1 for u in urls_for_sitemap if u.get("kind") == "guide")
    print(f"✅ Sitemap 분할 생성 완료: hub(10) / courses({n_course}) / guides({n_guide}) → sitemap.xml(index)")

if __name__ == "__main__":
    main()
