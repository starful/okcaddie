from flask import Flask, jsonify, render_template, abort, send_from_directory, redirect, request
from flask_compress import Compress
import json, os, frontmatter, markdown, re

app = Flask(__name__)
Compress(app)

# [설정]
BASE_DIR = app.root_path
GUIDE_DIR = os.path.join(BASE_DIR, 'content', 'guides')
CONTENT_DIR = os.path.join(BASE_DIR, 'content')
DATA_FILE = os.path.join(BASE_DIR, 'static', 'json', 'courses_data.json')

GUIDE_IMAGES = [
    "https://images.unsplash.com/photo-1587174486073-ae5e5cff23aa?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1535131749006-b7f58c99034b?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1591491640784-3232eb748d4b?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1563299796-17596ed6b017?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1590602847861-f357a9332bbc?q=80&w=1200&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?q=80&w=1200&auto=format&fit=crop"
]

CACHED_DATA = {"courses": []}
CACHED_GUIDES = []

def get_meta_fallback(text, key):
    """라이브러리가 파싱 못할 때를 대비한 정규식 백업"""
    pattern = rf'{key}:\s*["\']?(.*?)["\']?\n'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else ""

def load_all_data():
    global CACHED_DATA, CACHED_GUIDES
    
    # 1. 골프장 코스 데이터 로드
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                CACHED_DATA = json.load(f)
        except: CACHED_DATA = {"courses": []}

    # 2. AI 가이드 데이터 로드 및 텍스트 보정
    temp_guides = []
    if os.path.exists(GUIDE_DIR):
        files = sorted([f for f in os.listdir(GUIDE_DIR) if f.endswith('.md')], reverse=True)
        for filename in files:
            try:
                full_id = filename.replace('.md', '')
                if full_id.startswith('_') or '_' not in full_id: continue

                with open(os.path.join(GUIDE_DIR, filename), 'r', encoding='utf-8') as f:
                    raw_text = f.read()
                    
                    # [강력 보정] YAML 구분자가 첫 줄에 없으면 찾아서 맞춰줌
                    if '---' in raw_text:
                        raw_text = '---' + raw_text.split('---', 1)[1]
                    
                    post = frontmatter.loads(raw_text)
                    item = dict(post.metadata)
                    
                    # [백업 로직] 라이브러리가 값을 못 읽으면 정규식으로 직접 추출
                    title = item.get('title') or get_meta_fallback(raw_text, 'title')
                    summary = item.get('summary') or get_meta_fallback(raw_text, 'summary')
                    lang = item.get('lang') or get_meta_fallback(raw_text, 'lang') or 'en'
                    date = item.get('date') or get_meta_fallback(raw_text, 'date') or '2026-04-12'

                    # 요약문에서 YAML 흔적(---, lang: 등) 강제 제거
                    summary = re.sub(r'---.*?---', '', summary, flags=re.DOTALL)
                    summary = re.sub(r'^(lang|title|summary|date):.*', '', summary, flags=re.MULTILINE).strip()
                    
                    # 만약 요약이 여전히 이상하거나 없으면 본문 첫 150자 사용
                    if not summary or len(summary) < 10:
                        clean_body = re.sub(r'---.*?---', '', post.content, flags=re.DOTALL).strip()
                        summary = clean_body[:150].replace('\n', ' ') + '...'

                    base_id = full_id.rsplit('_', 1)[0]
                    img_idx = abs(hash(base_id) * 97) % len(GUIDE_IMAGES)
                    
                    temp_guides.append({
                        'id': full_id,
                        'base_id': base_id,
                        'lang': lang.strip().lower(),
                        'title': title.strip() or "Japan Golf Guide",
                        'summary': summary,
                        'date': str(date).strip(),
                        'image': GUIDE_IMAGES[img_idx]
                    })
            except Exception as e:
                print(f"❌ Error parsing {filename}: {e}")
    
    CACHED_GUIDES = temp_guides
    print(f"✅ Loaded {len(CACHED_GUIDES)} Guides")

load_all_data()

# ==========================================
# 🌐 라우팅 (Routing)
# ==========================================

@app.route('/')
def index():
    lang = request.args.get('lang', 'en')
    featured = [g for g in CACHED_GUIDES if g['lang'] == lang][:3]
    if not featured: featured = CACHED_GUIDES[:3]
    return render_template('index.html', featured_guides=featured, active_lang=lang)

@app.route('/api/courses')
def api_courses():
    lang = request.args.get('lang', 'en')
    filtered = []
    for c in CACHED_DATA.get('courses', []):
        if c.get('lang') == lang:
            temp = dict(c)
            temp['lang'] = 'en' # main.js 호환
            filtered.append(temp)
    if not filtered: filtered = CACHED_DATA.get('courses', [])
    return jsonify({"last_updated": CACHED_DATA.get('last_updated'), "courses": filtered})

@app.route('/guide')
def guide_list():
    lang = request.args.get('lang', 'en')
    guides = [g for g in CACHED_GUIDES if g['lang'] == lang]
    return render_template('guide_list.html', guides=guides, lang=lang, active_lang=lang)

@app.route('/guide/<guide_id>')
def guide_detail(guide_id):
    path = os.path.join(GUIDE_DIR, f"{guide_id}.md")
    if not os.path.exists(path): abort(404)

    with open(path, 'r', encoding='utf-8') as f:
        raw_text = f.read()
        if '---' in raw_text:
            raw_text = '---' + raw_text.split('---', 1)[1]
        post = frontmatter.loads(raw_text)
    
    # 본문에서 메타데이터 찌꺼기 제거
    body = post.content
    body = re.sub(r'^(lang|title|summary|date):.*', '', body, flags=re.MULTILINE)
    clean_body = body.replace('```markdown', '').replace('```', '').strip()
    
    # 정규식 fallback으로 제목/날짜 재확인
    title = post.metadata.get('title') or get_meta_fallback(raw_text, 'title') or guide_id
    date = post.metadata.get('date') or get_meta_fallback(raw_text, 'date') or "2026-04-12"

    base_id = guide_id.rsplit('_', 1)[0]
    img_idx = abs(hash(base_id) * 97) % len(GUIDE_IMAGES)
    
    return render_template('guide_detail.html', 
                           post={'title': title, 'date': date, 'lang': post.metadata.get('lang', 'en'), 'id': guide_id}, 
                           content=markdown.markdown(clean_body, extensions=['tables', 'fenced_code']), 
                           image=GUIDE_IMAGES[img_idx])

@app.route('/course/<course_id>')
def course_detail(course_id):
    md_path = os.path.join(CONTENT_DIR, f"{course_id}.md")
    if not os.path.exists(md_path): abort(404)
    with open(md_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)
    return render_template('detail.html', post=post, content=markdown.markdown(post.content))

@app.route('/static/images/<path:filename>')
def serve_images(filename):
    return redirect(f"https://storage.googleapis.com/ok-project-assets/okcaddie/{filename}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)