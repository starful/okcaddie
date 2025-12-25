from flask import Flask, jsonify, render_template, abort, send_from_directory, Response
from flask_compress import Compress
import json
import os
import frontmatter
import markdown
from datetime import datetime

app = Flask(__name__)
Compress(app)

# [설정] 경로 설정
BASE_DIR = app.root_path
DATA_FILE = os.path.join(BASE_DIR, 'static', 'json', 'shrines_data.json')
CONTENT_DIR = os.path.join(BASE_DIR, 'content')

@app.route('/')
def index():
    return render_template('index.html')

# ==========================================
# [수정] ads.txt 라우트 (파일 없이 코드에서 직접 리턴)
# ==========================================
@app.route('/ads.txt')
def ads_txt():
    # 구글 애드센스 승인 코드 내용
    content = "google.com, pub-8780435268193938, DIRECT, f08c47fec0942fa0"
    return Response(content, mimetype='text/plain')

# ==========================================
# [수정] 사이트맵 라우트 (JSON 데이터를 읽어서 실시간 생성)
# ==========================================
@app.route('/sitemap.xml')
def sitemap_xml():
    base_url = "https://jinjamap.com"  # 실제 도메인
    
    # 1. 빌드된 JSON 데이터 읽기
    shrines = []
    last_updated = datetime.now().strftime("%Y-%m-%d")
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                shrines = data.get('shrines', [])
                # JSON에 있는 마지막 업데이트 날짜 사용 (없으면 오늘)
                if 'last_updated' in data:
                    last_updated = data['last_updated'].replace('.', '-')
        except Exception as e:
            print(f"Error reading JSON: {e}")

    # 2. XML 문자열 생성
    xml = []
    xml.append('<?xml version="1.0" encoding="UTF-8"?>')
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    # (1) 메인 페이지
    xml.append('  <url>')
    xml.append(f'    <loc>{base_url}/</loc>')
    xml.append(f'    <lastmod>{last_updated}</lastmod>')
    xml.append('    <changefreq>daily</changefreq>')
    xml.append('    <priority>1.0</priority>')
    xml.append('  </url>')

    # (2) 각 신사 상세 페이지
    for shrine in shrines:
        link = shrine['link'] # 예: /shrine/abc
        date_str = shrine.get('published', last_updated) # YYYY-MM-DD
        
        xml.append('  <url>')
        xml.append(f'    <loc>{base_url}{link}</loc>')
        xml.append(f'    <lastmod>{date_str}</lastmod>')
        xml.append('    <changefreq>weekly</changefreq>')
        xml.append('    <priority>0.8</priority>')
        xml.append('  </url>')

    xml.append('</urlset>')
    
    # 3. XML 응답 반환
    return Response('\n'.join(xml), mimetype='application/xml')

# ==========================================
# [추가] 개인정보처리방침 라우트
# ==========================================
@app.route('/privacy.html')
def privacy():
    return render_template('privacy.html')

@app.route('/api/shrines')
def api_shrines():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        else:
            return jsonify({"shrines": [], "error": "Data file not found"})
    except Exception as e:
        return jsonify({"shrines": [], "error": str(e)})

@app.route('/shrine/<shrine_id>')
def shrine_detail(shrine_id):
    md_path = os.path.join(CONTENT_DIR, f"{shrine_id}.md")
    if not os.path.exists(md_path):
        abort(404)
    with open(md_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)
    content_html = markdown.markdown(post.content, extensions=['tables'])
    return render_template('detail.html', post=post, content=content_html)

# [핵심] content/images 이미지 서빙
@app.route('/content/images/<path:filename>')
def serve_content_images(filename):
    images_dir = os.path.join(CONTENT_DIR, 'images')
    return send_from_directory(images_dir, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)