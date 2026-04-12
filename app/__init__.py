from flask import Flask, jsonify, render_template, abort, send_from_directory, redirect # redirect 추가
from flask_compress import Compress
import json
import os
import frontmatter
import markdown
import re

app = Flask(__name__)
Compress(app)

# [설정] 경로 설정
BASE_DIR = app.root_path
STATIC_DIR = os.path.join(BASE_DIR, 'static')
DATA_FILE = os.path.join(STATIC_DIR, 'json', 'courses_data.json') # 골프 데이터로 변경
CONTENT_DIR = os.path.join(BASE_DIR, 'content')

# [최적화] 서버 시작 시 데이터를 메모리에 로드
CACHED_DATA = {}
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            CACHED_DATA = json.load(f)
            print(f"✅ Golf Data loaded: {len(CACHED_DATA.get('courses',[]))} items")
    except Exception as e:
        print(f"❌ Data load error: {e}")
        CACHED_DATA = {"courses":[], "error": "Load failed"}

@app.route('/static/images/<path:filename>')
def serve_images(filename):
    import time
    # ok-project-assets/okcaddie 폴더를 바라보게 설정
    return redirect(f"https://storage.googleapis.com/ok-project-assets/okcaddie/{filename}?v={int(time.time())}")
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/courses') # 엔드포인트 변경
def api_courses():
    return jsonify(CACHED_DATA)

@app.route('/course/<course_id>') # 경로를 onsen -> course로 변경
def course_detail(course_id):
    md_path = os.path.join(CONTENT_DIR, f"{course_id}.md")
    if not os.path.exists(md_path):
        abort(404)
        
    with open(md_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)

    if isinstance(post.get('categories'), str):
        post['categories'] = [c.strip() for c in post['categories'].split(',')]

    # 가독성을 위한 정규식 처리
    fixed_content = re.sub(r'([\.!?:])\s+(\*\s)', r'\1\n\n\2', post.content)
    fixed_content = re.sub(r'([^\n])\n\*\s', r'\1\n\n* ', fixed_content)
    fixed_content = re.sub(r'([^\n])\n-\s', r'\1\n\n- ', fixed_content)

    content_html = markdown.markdown(fixed_content, extensions=['tables'])
    
    return render_template('detail.html', post=post, content=content_html)

@app.route('/ads.txt')
def ads_txt():
    return send_from_directory(STATIC_DIR, 'ads.txt')

@app.route('/sitemap.xml')
def sitemap_xml():
    return send_from_directory(STATIC_DIR, 'sitemap.xml')

@app.route('/robots.txt')
def robots_txt():
    return send_from_directory(STATIC_DIR, 'robots.txt')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)