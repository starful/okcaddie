import os
import json
import frontmatter
import markdown
from bs4 import BeautifulSoup
from datetime import datetime

# 설정
CONTENT_DIR = 'app/content'
JSON_OUTPUT = 'app/static/json/shrines_data.json'
SITEMAP_OUTPUT = 'app/static/sitemap.xml'
BASE_URL = 'https://jinjamap.com'

def strip_markdown(text):
    """마크다운을 순수 텍스트로 변환 (요약문 생성용)"""
    try:
        html = markdown.markdown(text)
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text()
    except Exception as e:
        print(f"Warning: Text strip failed - {e}")
        return text

def generate_sitemap(shrines):
    """사이트맵 XML 생성"""
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    xml += '  <url>\n'
    xml += f'    <loc>{BASE_URL}/</loc>\n'
    xml += f'    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>\n'
    xml += '    <changefreq>daily</changefreq>\n'
    xml += '    <priority>1.0</priority>\n'
    xml += '  </url>\n'

    for shrine in shrines:
        link = shrine['link']
        date_str = shrine['published']
        
        xml += '  <url>\n'
        xml += f'    <loc>{BASE_URL}{link}</loc>\n'
        xml += f'    <lastmod>{date_str}</lastmod>\n'
        xml += '    <changefreq>weekly</changefreq>\n'
        xml += '    <priority>0.8</priority>\n'
        xml += '  </url>\n'
        
    xml += '</urlset>'
    return xml

def main():
    print("🔨 로컬 마크다운 데이터 빌드 시작...")
    
    shrines = []
    
    os.makedirs(os.path.dirname(JSON_OUTPUT), exist_ok=True)
    os.makedirs(os.path.dirname(SITEMAP_OUTPUT), exist_ok=True)

    if not os.path.exists(CONTENT_DIR):
        os.makedirs(CONTENT_DIR)

    for filename in os.listdir(CONTENT_DIR):
        if not filename.endswith('.md'):
            continue
            
        filepath = os.path.join(CONTENT_DIR, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                
                # Draft 기능 (개발환경 변수 없으면 스킵)
                if post.get('draft') == True and not os.environ.get('DEV_MODE'):
                    continue

                if not post.get('lat') or not post.get('lng'):
                    continue

                date_val = post.get('date')
                if date_val:
                    published_date = str(date_val)
                else:
                    published_date = datetime.now().strftime('%Y-%m-%d')

                # 요약문 생성
                summary = post.get('summary')
                if not summary:
                    clean_text = strip_markdown(post.content)
                    summary = clean_text[:120] + '...'
                
                # [핵심] 온천 정보 유무 확인
                content_str = str(post.content)
                has_onsen = "Relax at a Nearby Onsen" in content_str or "Nearby Attractions: Hot Springs" in content_str

                shrine = {
                    "id": filename.replace('.md', ''),
                    "title": post.get('title', 'No Title'),
                    "lat": post.get('lat'),
                    "lng": post.get('lng'),
                    "categories": post.get('categories', []),
                    "thumbnail": post.get('thumbnail', '/static/images/default.png'),
                    "address": post.get('address', ''),
                    "published": published_date,
                    "summary": summary,
                    "link": f"/shrine/{filename.replace('.md', '')}",
                    "has_onsen": has_onsen # 👈 JSON 필드 추가
                }
                shrines.append(shrine)

        except Exception as e:
            print(f"❌ 에러 발생 ({filename}): {e}")

    # 최신순 정렬
    shrines.sort(key=lambda x: x['published'], reverse=True)

    final_data = {
        "last_updated": datetime.now().strftime("%Y.%m.%d"),
        "shrines": shrines
    }
    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    sitemap_content = generate_sitemap(shrines)
    with open(SITEMAP_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(sitemap_content)

    print(f"\n🎉 빌드 완료! 총 {len(shrines)}개")

if __name__ == "__main__":
    main()