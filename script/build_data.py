import os
import json
import frontmatter
import markdown
from bs4 import BeautifulSoup
from datetime import datetime

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
BASE_DIR     = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR  = os.path.join(BASE_DIR, 'app', 'content')
STATIC_DIR   = os.path.join(BASE_DIR, 'app', 'static')
JSON_OUTPUT  = os.path.join(STATIC_DIR, 'json', 'courses_data.json')
SITEMAP_OUT  = os.path.join(STATIC_DIR, 'sitemap.xml')
BASE_URL     = 'https://okcaddie.net'

def strip_markdown(text):
    try:
        html = markdown.markdown(text)
        return BeautifulSoup(html, "html.parser").get_text()
    except:
        return text

def generate_sitemap(courses):
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    today = datetime.now().strftime("%Y-%m-%d")
    xml += [f'  <url><loc>{BASE_URL}/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>']
    for c in courses:
        xml.append(f'  <url><loc>{BASE_URL}{c["link"]}</loc><lastmod>{c.get("published", today)}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>')
    xml.append('</urlset>')
    return '\n'.join(xml)

def main():
    print(f"🔨 OKCaddie 빌드 시작")
    courses = []

    os.makedirs(os.path.dirname(JSON_OUTPUT), exist_ok=True)
    if not os.path.exists(CONTENT_DIR):
        print(f"❌ Content 디렉토리 없음: {CONTENT_DIR}")
        return

    for filename in os.listdir(CONTENT_DIR):
        if not filename.endswith('.md'):
            continue

        filepath = os.path.join(CONTENT_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)

            if post.get('draft') == True:
                continue

            # lat/lng 강제 float 변환
            try:
                lat = float(post.get('lat', 0) or 0)
                lng = float(post.get('lng', 0) or 0)
            except (ValueError, TypeError):
                lat, lng = 0.0, 0.0

            if lat == 0.0 or lng == 0.0:
                print(f"⚠️  Skip {filename}: invalid lat/lng")
                continue

            lang = post.get('lang', 'en')
            date_val = post.get('date')
            published = str(date_val) if date_val else datetime.now().strftime('%Y-%m-%d')

            summary = post.get('summary', '')
            if not summary:
                summary = strip_markdown(post.content)[:120] + '...'

            cats = post.get('categories', [])
            if isinstance(cats, str):
                cats = [c.strip() for c in cats.split(',')]

            courses.append({
                "id":         filename.replace('.md', ''),
                "lang":       lang,
                "title":      post.get('title', 'No Title'),
                "lat":        lat,
                "lng":        lng,
                "categories": cats,
                "thumbnail":  post.get('thumbnail', '/static/images/default.jpg'),
                "address":    post.get('address', ''),
                "published":  published,
                "summary":    summary,
                "booking":    post.get('booking', ''),
                "link":       f"/course/{filename.replace('.md', '')}"
            })

        except Exception as e:
            print(f"❌ {filename} 처리 오류: {e}")

    courses.sort(key=lambda x: x['published'], reverse=True)

    final_data = {
        "last_updated": datetime.now().strftime("%Y.%m.%d"),
        "courses": courses
    }

    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    with open(SITEMAP_OUT, 'w', encoding='utf-8') as f:
        f.write(generate_sitemap(courses))

    print(f"🎉 빌드 완료! 총 {len(courses)}개 골프장 데이터")

if __name__ == "__main__":
    main()
