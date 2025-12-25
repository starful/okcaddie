import os
import json
import frontmatter
from datetime import datetime

# 설정
CONTENT_DIR = 'app/content'
JSON_OUTPUT = 'app/static/json/shrines_data.json'
SITEMAP_OUTPUT = 'app/static/sitemap.xml'
BASE_URL = 'https://jinjamap.com'  # 실제 도메인으로 변경 필수

def generate_sitemap(shrines):
    """사이트맵 XML 내용을 생성하는 함수"""
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # 1. 메인 페이지 (항상 최신)
    xml += '  <url>\n'
    xml += f'    <loc>{BASE_URL}/</loc>\n'
    xml += f'    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>\n'
    xml += '    <changefreq>daily</changefreq>\n'
    xml += '    <priority>1.0</priority>\n'
    xml += '  </url>\n'

    # 2. 각 신사 상세 페이지
    for shrine in shrines:
        link = shrine['link'] # /shrine/id 형식
        date_str = shrine['published'] # YYYY-MM-DD
        
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
    
    # 디렉토리 생성
    os.makedirs(os.path.dirname(JSON_OUTPUT), exist_ok=True)
    os.makedirs(os.path.dirname(SITEMAP_OUTPUT), exist_ok=True)

    if not os.path.exists(CONTENT_DIR):
        os.makedirs(CONTENT_DIR)

    # 마크다운 파일 읽기
    for filename in os.listdir(CONTENT_DIR):
        if not filename.endswith('.md'):
            continue
            
        filepath = os.path.join(CONTENT_DIR, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                
                if not post.get('lat') or not post.get('lng'):
                    continue

                # 날짜 처리 (없으면 오늘 날짜)
                date_val = post.get('date')
                if date_val:
                    published_date = str(date_val)
                else:
                    published_date = datetime.now().strftime('%Y-%m-%d')

                shrine = {
                    "id": filename.replace('.md', ''),
                    "title": post.get('title', 'No Title'),
                    "lat": post.get('lat'),
                    "lng": post.get('lng'),
                    "categories": post.get('categories', []),
                    "thumbnail": post.get('thumbnail', '/static/images/default.png'),
                    "address": post.get('address', ''),
                    "published": published_date,
                    "summary": post.get('summary', post.content[:100] + '...'),
                    "link": f"/shrine/{filename.replace('.md', '')}" 
                }
                shrines.append(shrine)

        except Exception as e:
            print(f"❌ 에러 발생 ({filename}): {e}")

    # 최신순 정렬
    shrines.sort(key=lambda x: x['published'], reverse=True)

    # 1. JSON 파일 저장
    final_data = {
        "last_updated": datetime.now().strftime("%Y.%m.%d"),
        "shrines": shrines
    }
    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    # 2. Sitemap.xml 파일 저장 (추가된 부분)
    sitemap_content = generate_sitemap(shrines)
    with open(SITEMAP_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(sitemap_content)

    print(f"\n🎉 빌드 완료! 총 {len(shrines)}개")
    print(f"   - JSON: {JSON_OUTPUT}")
    print(f"   - Sitemap: {SITEMAP_OUTPUT}")

if __name__ == "__main__":
    main()