import os
import json
import frontmatter
import markdown
from bs4 import BeautifulSoup
from datetime import datetime

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
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 1. 메인 홈 페이지 (최우선순위)
    xml.append(f'  <url><loc>{BASE_URL}/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>')
    
    # 2. 가이드 목록 페이지
    xml.append(f'  <url><loc>{BASE_URL}/guide</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.9</priority></url>')

    # 3. 개별 코스 및 가이드 페이지들
    for entry in urls:
        xml.append(f'  <url>')
        xml.append(f'    <loc>{BASE_URL}{entry["url"]}</loc>')
        xml.append(f'    <lastmod>{entry.get("date", today)}</lastmod>')
        xml.append(f'    <changefreq>monthly</changefreq>')
        xml.append(f'    <priority>0.8</priority>')
        xml.append(f'  </url>')
        
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
                    "link": f"/course/{course_id}"
                }
                courses_for_json.append(course_data)
                
                # 사이트맵용 데이터 추가
                urls_for_sitemap.append({"url": f"/course/{course_id}", "date": date_val})
                
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
                    urls_for_sitemap.append({"url": f"/guide/{guide_id}", "date": date_val})
            except:
                urls_for_sitemap.append({"url": f"/guide/{guide_id}", "date": datetime.now().strftime('%Y-%m-%d')})

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