import os
import json
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
CONTENT_DIR  = os.path.join(BASE_DIR, 'app', 'content')        # 코스 마크다운
GUIDE_DIR    = os.path.join(CONTENT_DIR, 'guides')            # 가이드 마크다운
STATIC_DIR   = os.path.join(BASE_DIR, 'app', 'static')
JSON_OUTPUT  = os.path.join(STATIC_DIR, 'json', 'courses_data.json')
SITEMAP_OUT  = os.path.join(STATIC_DIR, 'sitemap.xml')
BASE_URL     = 'https://okcaddie.net'

def strip_markdown(text):
    """마크다운/HTML 태그를 제거하고 순수 텍스트만 추출 (BeautifulSoup 사용)"""
    try:
        html = markdown.markdown(text)
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text()
    except:
        return text

def generate_sitemap(urls):
    """구글 검색 엔진을 위한 sitemap.xml 생성"""
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'
    ]

    today = datetime.now().strftime("%Y-%m-%d")

    def add_url(path, lastmod, changefreq, priority, alternates=None):
        loc = f"{BASE_URL}{path}"
        xml.append("  <url>")
        xml.append(f"    <loc>{escape(loc)}</loc>")
        if alternates:
            for lang_code, alt_path in alternates:
                href = f"{BASE_URL}{alt_path}"
                xml.append(
                    f'    <xhtml:link rel="alternate" hreflang="{escape(lang_code)}" href="{escape(href)}" />'
                )
        xml.append(f"    <lastmod>{escape(lastmod)}</lastmod>")
        xml.append(f"    <changefreq>{changefreq}</changefreq>")
        xml.append(f"    <priority>{priority}</priority>")
        xml.append("  </url>")

    # 1) 고정 핵심 페이지
    add_url("/", today, "daily", "1.0", [
        ("en", "/?lang=en"),
        ("ko", "/?lang=ko"),
        ("x-default", "/")
    ])
    add_url("/?lang=en", today, "daily", "0.9", [
        ("en", "/?lang=en"),
        ("ko", "/?lang=ko"),
        ("x-default", "/")
    ])
    add_url("/?lang=ko", today, "daily", "0.9", [
        ("en", "/?lang=en"),
        ("ko", "/?lang=ko"),
        ("x-default", "/")
    ])
    add_url("/guide", today, "weekly", "0.9", [
        ("en", "/guide?lang=en"),
        ("ko", "/guide?lang=ko"),
        ("x-default", "/guide")
    ])
    add_url("/guide?lang=en", today, "weekly", "0.8", [
        ("en", "/guide?lang=en"),
        ("ko", "/guide?lang=ko"),
        ("x-default", "/guide")
    ])
    add_url("/guide?lang=ko", today, "weekly", "0.8", [
        ("en", "/guide?lang=en"),
        ("ko", "/guide?lang=ko"),
        ("x-default", "/guide")
    ])
    add_url("/courses", today, "weekly", "0.9", [
        ("en", "/courses?lang=en"),
        ("ko", "/courses?lang=ko"),
        ("x-default", "/courses")
    ])
    add_url("/courses?lang=en", today, "weekly", "0.8", [
        ("en", "/courses?lang=en"),
        ("ko", "/courses?lang=ko"),
        ("x-default", "/courses")
    ])
    add_url("/courses?lang=ko", today, "weekly", "0.8", [
        ("en", "/courses?lang=en"),
        ("ko", "/courses?lang=ko"),
        ("x-default", "/courses")
    ])
    add_url("/about", today, "monthly", "0.4")
    add_url("/privacy", today, "monthly", "0.4")

    # 2) 언어별 짝을 가진 상세 URL 구축
    grouped = {}
    for entry in urls:
        key = (entry.get("kind", ""), entry.get("base_id", ""), entry.get("lang", ""))
        grouped[key] = entry

    for entry in urls:
        path = entry["url"]
        date_val = entry.get("date", today)
        kind = entry.get("kind", "")
        base_id = entry.get("base_id", "")
        lang = entry.get("lang", "en")
        changefreq = entry.get("changefreq", "monthly")
        priority = entry.get("priority", "0.8")

        alt_lang = "ko" if lang == "en" else "en"
        alt_key = (kind, base_id, alt_lang)
        alternates = [(lang, path)]
        if alt_key in grouped:
            alternates.append((alt_lang, grouped[alt_key]["url"]))
        alternates.append(("x-default", path if lang == "en" else grouped.get(alt_key, entry)["url"]))

        add_url(path, date_val, changefreq, priority, alternates)

    xml.append('</urlset>')
    return '\n'.join(xml)

def main():
    print(f"🔨 OKCaddie 데이터 및 사이트맵 빌드 프로세스 시작")
    
    courses_for_json = []  # 지도를 위한 JSON 데이터
    urls_for_sitemap = [] # 사이트맵을 위한 URL 목록
    
    # 디렉토리 체크
    os.makedirs(os.path.dirname(JSON_OUTPUT), exist_ok=True)

    # ------------------------------------------
    # 1. 골프장 코스 데이터 처리 (app/content/*.md)
    # ------------------------------------------
    if os.path.exists(CONTENT_DIR):
        print(f"📂 코스 데이터 수집 중...")
        for filename in os.listdir(CONTENT_DIR):
            if not filename.endswith('.md') or filename.startswith('_'):
                continue
            
            filepath = os.path.join(CONTENT_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                
                # 좌표 데이터 숫자 변환 및 검증
                try:
                    lat = float(post.get('lat', 0))
                    lng = float(post.get('lng', 0))
                except (ValueError, TypeError):
                    lat, lng = 0.0, 0.0

                if lat == 0.0: continue # 좌표 없으면 지도 데이터에서 제외

                course_id = filename.replace('.md', '')
                date_val = str(post.get('date', datetime.now().strftime('%Y-%m-%d')))
                
                # 요약문 처리
                summary = post.get('summary', '')
                if not summary:
                    summary = strip_markdown(post.content)[:120] + '...'

                # 카테고리 리스트화
                cats = post.get('categories', [])
                if isinstance(cats, str):
                    cats = [c.strip() for c in cats.split(',')]

                # JSON 데이터 구성
                course_data = {
                    "id": course_id,
                    "base_id": course_id.rsplit('_', 1)[0] if '_' in course_id else course_id,
                    "lang": post.get('lang', 'en'),
                    "title": post.get('title', 'No Title'),
                    "lat": lat,
                    "lng": lng,
                    "categories": cats,
                    "thumbnail": post.get('thumbnail', f"/static/images/{course_id.rsplit('_',1)[0]}.jpg"),
                    "address": post.get('address', ''),
                    "published": date_val,
                    "summary": summary,
                    "booking": post.get('booking', ''),
                    "link": f"/course/{course_id.rsplit('_', 1)[0] if '_' in course_id else course_id}?lang={post.get('lang', 'en')}"
                }
                courses_for_json.append(course_data)
                
                # 사이트맵용 데이터 추가
                base_id = course_id.rsplit('_', 1)[0] if '_' in course_id else course_id
                urls_for_sitemap.append({
                    "url": f"/course/{base_id}?lang={post.get('lang', 'en')}",
                    "date": date_val,
                    "lang": post.get('lang', 'en'),
                    "base_id": base_id,
                    "kind": "course",
                    "changefreq": "monthly",
                    "priority": "0.8"
                })
                
            except Exception as e:
                print(f"  ❌ 코스 오류 ({filename}): {e}")

    # ------------------------------------------
    # 2. AI 가이드 데이터 처리 (app/content/guides/*.md)
    # ------------------------------------------
    if os.path.exists(GUIDE_DIR):
        print(f"📂 가이드 데이터 수집 중...")
        for filename in os.listdir(GUIDE_DIR):
            if not filename.endswith('.md'):
                continue
            
            guide_id = filename.replace('.md', '')
            try:
                with open(os.path.join(GUIDE_DIR, filename), 'r', encoding='utf-8') as f:
                    # 가이드는 사이트맵 주소만 수집 (JSON에는 넣지 않음)
                    post = frontmatter.load(f)
                    date_val = str(post.get('date', datetime.now().strftime('%Y-%m-%d')))
                    base_id = guide_id.rsplit('_', 1)[0] if '_' in guide_id else guide_id
                    urls_for_sitemap.append({
                        "url": f"/guide/{base_id}?lang={post.get('lang', 'en')}",
                        "date": date_val,
                        "lang": post.get('lang', 'en'),
                        "base_id": base_id,
                        "kind": "guide",
                        "changefreq": "monthly",
                        "priority": "0.8"
                    })
            except:
                fallback_date = datetime.now().strftime('%Y-%m-%d')
                base_id = guide_id.rsplit('_', 1)[0] if '_' in guide_id else guide_id
                lang = 'ko' if guide_id.endswith('_ko') else 'en'
                urls_for_sitemap.append({
                    "url": f"/guide/{base_id}?lang={lang}",
                    "date": fallback_date,
                    "lang": lang,
                    "base_id": base_id,
                    "kind": "guide",
                    "changefreq": "monthly",
                    "priority": "0.8"
                })

    # ------------------------------------------
    # 3. 결과물 저장
    # ------------------------------------------
    
    # JSON 정렬 (최신순)
    courses_for_json.sort(key=lambda x: x['published'], reverse=True)
    
    # 3-1. JSON 파일 저장
    final_json = {
        "last_updated": datetime.now().strftime("%Y.%m.%d"),
        "courses": courses_for_json
    }
    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON 생성 완료: {len(courses_for_json)}개 코스 포함")

    # 3-2. 사이트맵 XML 저장
    sitemap_xml = generate_sitemap(urls_for_sitemap)
    with open(SITEMAP_OUT, 'w', encoding='utf-8') as f:
        f.write(sitemap_xml)
    print(f"✅ 사이트맵 생성 완료: {len(urls_for_sitemap)}개 URL 포함")

if __name__ == "__main__":
    main()