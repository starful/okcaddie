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
        if '---' in raw_text: raw_text = '---' + raw_text.split('---', 1)[1]
        post_obj = frontmatter.loads(raw_text)

    # 헤더 버튼 활성화를 위해 데이터 강제 주입
    post_data = dict(post_obj.metadata)
    post_data['id'] = guide_id
    post_data['lang'] = post_data.get('lang', 'en').strip().lower()

    clean_body = re.sub(r'^(lang|title|summary|date):.*', '', post_obj.content, flags=re.MULTILINE).strip()
    
    return render_template('guide_detail.html', 
                           post=post_data, 
                           content=markdown.markdown(clean_body, extensions=['tables']), 
                           image=GUIDE_IMAGES[abs(hash(guide_id.rsplit('_', 1)[0]) * 97) % len(GUIDE_IMAGES)],
                           active_lang=post_data['lang'])

@app.route('/course/<course_id>')
def course_detail(course_id):
    md_path = os.path.join(CONTENT_DIR, f"{course_id}.md")
    if not os.path.exists(md_path): abort(404)
    
    with open(md_path, 'r', encoding='utf-8') as f:
        raw_text = f.read().strip()

    # [핵심] 설정값(YAML)과 본문을 강제로 분리하는 로직
    if '---' in raw_text:
        # 첫 번째 --- 이전의 쓰레기 값을 지우고 --- 부터 시작하게 만듦
        raw_text = '---' + raw_text.split('---', 1)[1]
    
    try:
        post_obj = frontmatter.loads(raw_text)
        post_data = dict(post_obj.metadata)
        post_content = post_obj.content
    except Exception as e:
        print(f"Error parsing course {course_id}: {e}")
        abort(500)

    # 본문에 메타데이터(lang:, title: 등)가 텍스트로 남아있는 경우 강제 제거 (정규식)
    post_content = re.sub(r'^(lang|title|lat|lng|categories|thumbnail|address|date|booking|summary):.*$', '', post_content, flags=re.MULTILINE | re.IGNORECASE).strip()

    # 템플릿에 필요한 데이터 정리
    post_data['id'] = course_id
    post_data['lang'] = 'ko' if course_id.endswith('_ko') else 'en'
    
    # 카테고리 리스트화
    if isinstance(post_data.get('categories'), str):
        post_data['categories'] = [c.strip() for c in post_data['categories'].split(',')]

    # 가독성을 위한 줄바꿈 보정
    fixed_content = re.sub(r'([\.!?:])\s+(\*\s)', r'\1\n\n\2', post_content)
    fixed_content = re.sub(r'([^\n])\n\*\s', r'\1\n\n* ', fixed_content)

    content_html = markdown.markdown(fixed_content, extensions=['tables', 'fenced_code'])
    
    return render_template('detail.html', 
                           post=post_data, 
                           content=content_html, 
                           active_lang=post_data['lang'])

# app/__init__.py 에 아래 함수를 추가하세요.

# app/__init__.py 에 추가/수정

@app.route('/booking/<course_id>')
def booking_redirect(course_id):
    """라쿠텐 고라: 실시간 티타임 예약 전용 (영문 페이지)"""
    # 제공해주신 라쿠텐 고라 파트너 링크
    RAKUTEN_GORA_URL = "https://a.r10.to/hF8a6l"
    return redirect(RAKUTEN_GORA_URL)

@app.route('/travel/<item_type>/<course_id>')
def travel_redirect(item_type, course_id):
    """클룩: 아이템 타입별 리다이렉트 관리"""
    
    # 1. 언어 판별
    is_ko = course_id.endswith('_ko')
    
    # 2. 아이템별 파트너 링크 설정 (생성하신 링크로 교체하세요)
    # 아래는 예시 코드입니다.
    links = {
        "rental": "https://klook.tpo.mx/ay7rwBk6" if is_ko else "https://klook.tpo.mx/XD9YKSl3",
        "pickup": "https://klook.tpo.mx/ZsgqPaTQ" if is_ko else "https://klook.tpo.mx/LrVOwYHu",
        "esim":   "https://klook.tpo.mx/of4QelX3" if is_ko else "https://klook.tpo.mx/bBQ8iRn2"
    }
    
    # 기본값은 이전에 만드신 일반 골프 검색 링크
    default_link = "https://klook.tpo.mx/dOzmfkTF" if is_ko else "https://klook.tpo.mx/VRJHMdHu"
    
    return redirect(links.get(item_type, default_link))

# 기존 serve_images 함수 위에 아래 라우트를 추가하세요.
@app.route('/favicon.ico')
@app.route('/favicon-32x32.png')
@app.route('/favicon-48x48.png')
@app.route('/apple-touch-icon.png')
def serve_favicons():
    # 리다이렉트 하지 않고 로컬 static/images 폴더에서 직접 서빙
    return send_from_directory(os.path.join(app.root_path, 'static', 'images'), request.path[1:])

@app.route('/static/images/<path:filename>')
def serve_images(filename):
    import time
    # 파비콘류 파일이 아닐 때만 GCS로 리다이렉트
    if filename in ['favicon.ico', 'favicon-32x32.png', 'favicon-48x48.png', 'apple-touch-icon.png']:
        return send_from_directory(os.path.join(app.root_path, 'static', 'images'), filename)
        
    return redirect(f"https://storage.googleapis.com/ok-project-assets/okcaddie/{filename}?v={int(time.time())}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)