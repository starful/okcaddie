from flask import Flask, jsonify, render_template, abort, send_from_directory, redirect, request
from flask_compress import Compress
import json
import os
import frontmatter
import markdown
import re
import urllib.parse
from datetime import datetime, timedelta

app = Flask(__name__)
Compress(app)

# ==========================================
# ⚙️ 경로 및 데이터 설정
# ==========================================
BASE_DIR = app.root_path
STATIC_DIR = os.path.join(BASE_DIR, 'static')
CONTENT_DIR = os.path.join(BASE_DIR, 'content')
GUIDE_DIR = os.path.join(CONTENT_DIR, 'guides')
DATA_FILE = os.path.join(STATIC_DIR, 'json', 'courses_data.json')

# [고화질 골프 이미지 20개] 확실히 살아있는 링크 리스트
GUIDE_IMAGES = [
    "https://images.unsplash.com/photo-1587174486073-ae5e5cff23aa?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1535131749006-b7f58c99034b?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1591491640784-3232eb748d4b?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1563299796-17596ed6b017?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1590602847861-f357a9332bbc?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1586227740560-8cf2732c1531?auto=format&fit=crop&w=1200"
]

# 일본 도도부현별 라쿠텐 고라 지역 코드 매핑 (전체 47개주)
AREA_MAP = {
    '北海道': 1, '青森': 2, '岩手': 3, '宮城': 4, '秋田': 5, '山形': 6, '福島': 7,
    '茨城': 8, '栃木': 9, '群馬': 10, '埼玉': 11, '千葉': 12, '東京': 13, '神奈川': 14,
    '新潟': 15, '富山': 16, '石川': 17, '福井': 18, '山梨': 19, '長野': 20, '岐阜': 21,
    '静岡': 22, '愛知': 23, '三重': 24, '滋賀': 25, '京都': 26, '大阪': 27, '兵庫': 28,
    '奈良': 29, '和歌山': 30, '鳥取': 31, '島根': 32, '岡山': 33, '広島': 34, '山口': 35,
    '徳島': 36, '香川': 37, '愛媛': 38, '高知': 39, '福岡': 40, '佐賀': 41, '長崎': 42,
    '熊本': 43, '大分': 44, '宮崎': 45, '鹿児島': 46, '沖縄': 47
}

CACHED_DATA = {"courses": []}
CACHED_GUIDES = []

# ==========================================
# 🛠️ 유틸리티 및 데이터 로드 함수
# ==========================================

def get_meta_fallback(text, key):
    """YAML 파싱 실패 시 정규식으로 데이터를 강제 추출하는 백업 함수"""
    pattern = rf'{key}:\s*["\']?(.*?)["\']?\n'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else ""

def load_all_data():
    """서버 시작 시 메모리에 모든 마크다운 및 JSON 데이터를 로드"""
    global CACHED_DATA, CACHED_GUIDES
    
    # 1. 골프장 코스 JSON 데이터 로드
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                CACHED_DATA = json.load(f)
                print(f"✅ Course JSON loaded: {len(CACHED_DATA.get('courses', []))} items")
        except Exception as e:
            print(f"❌ Course Data error: {e}")
            CACHED_DATA = {"courses": []}

    # 2. AI 가이드 마크다운 로드 및 정제
    temp_guides = []
    if os.path.exists(GUIDE_DIR):
        files = sorted([f for f in os.listdir(GUIDE_DIR) if f.endswith('.md')], reverse=True)
        for filename in files:
            try:
                full_id = filename.replace('.md', '')
                if full_id.startswith('_') or '_' not in full_id:
                    continue

                with open(os.path.join(GUIDE_DIR, filename), 'r', encoding='utf-8') as f:
                    raw_text = f.read().strip()
                    # YAML 구분자 보정 (첫 줄에 --- 가 오도록 강제)
                    if '---' in raw_text:
                        raw_text = '---' + raw_text.split('---', 1)[1]
                    
                    post = frontmatter.loads(raw_text)
                    item = dict(post.metadata)
                    
                    base_id = full_id.rsplit('_', 1)[0]
                    # 파일명으로 언어 강제 분류 (en/ko)
                    detected_lang = 'ko' if full_id.endswith('_ko') else 'en'
                    
                    # 제목 및 요약문 로드 (누락 시 fallback 작동)
                    title = item.get('title') or get_meta_fallback(raw_text, 'title')
                    summary = item.get('summary') or get_meta_fallback(raw_text, 'summary')
                    
                    if not summary or 'lang:' in summary:
                        # 본문 첫 부분을 잘라서 요약문 생성
                        clean_body = re.sub(r'---.*?---', '', post.content, flags=re.DOTALL).strip()
                        summary = clean_body[:130].replace('\n', ' ') + '...'

                    temp_guides.append({
                        'id': full_id,
                        'base_id': base_id,
                        'lang': detected_lang,
                        'title': title.strip() or "Japan Golf Guide",
                        'summary': summary.strip(),
                        'date': str(item.get('date', '2026-04-12')),
                        'image': GUIDE_IMAGES[abs(hash(base_id) * 97) % len(GUIDE_IMAGES)]
                    })
            except Exception as e:
                print(f"❌ Guide load error ({filename}): {e}")
    
    CACHED_GUIDES = temp_guides
    print(f"✅ AI Guides loaded: {len(CACHED_GUIDES)} items")

# 초기 실행
load_all_data()

# ==========================================
# 🌐 라우팅 (Routing) - 사용자 페이지
# ==========================================

@app.route('/')
def index():
    """메인 페이지: 선택 언어에 맞는 가이드 하이라이트 노출"""
    lang = request.args.get('lang', 'en')
    featured = [g for g in CACHED_GUIDES if g['lang'] == lang][:3]
    # 가이드가 없으면 전체에서 상위 3개 노출 (안전장치)
    if not featured:
        featured = CACHED_GUIDES[:3]
    return render_template('index.html', featured_guides=featured, active_lang=lang)

@app.route('/api/courses')
def api_courses():
    """지도 및 리스트용 데이터 API: JS 호환을 위한 언어 속성 변조 포함"""
    lang = request.args.get('lang', 'en')
    filtered = []
    for c in CACHED_DATA.get('courses', []):
        if c.get('lang') == lang:
            temp = dict(c)
            temp['lang'] = 'en' # main.js가 en만 찾도록 고정되어 있어도 한국어 내용을 보여주게 함
            filtered.append(temp)
    # 필터링 결과가 없으면 전체 전송
    if not filtered:
        filtered = CACHED_DATA.get('courses', [])
    return jsonify({"last_updated": CACHED_DATA.get('last_updated'), "courses": filtered})

@app.route('/course/<course_id>')
def course_detail(course_id):
    """골프장 상세 페이지: 마크다운 파싱 및 본문 찌꺼기 제거"""
    md_path = os.path.join(CONTENT_DIR, f"{course_id}.md")
    if not os.path.exists(md_path):
        abort(404)
        
    with open(md_path, 'r', encoding='utf-8') as f:
        raw = f.read().strip()
    
    if '---' in raw:
        raw = '---' + raw.split('---', 1)[1]
    
    post_obj = frontmatter.loads(raw)
    post_data = dict(post_obj.metadata)
    
    # 본문 내 불필요한 메타데이터 텍스트 강제 삭제
    post_content = re.sub(r'^(lang|title|lat|lng|categories|thumbnail|address|date|booking|summary):.*$', '', post_obj.content, flags=re.MULTILINE | re.IGNORECASE).strip()
    
    post_data['id'] = course_id
    post_data['lang'] = 'ko' if course_id.endswith('_ko') else 'en'
    
    if isinstance(post_data.get('categories'), str):
        post_data['categories'] = [c.strip() for c in post_data['categories'].split(',')]

    # 가독성을 위한 줄바꿈 정규식 보정
    post_content = re.sub(r'([\.!?:])\s+(\*\s)', r'\1\n\n\2', post_content)
    post_content = re.sub(r'([^\n])\n\*\s', r'\1\n\n* ', post_content)
    
    content_html = markdown.markdown(post_content, extensions=['tables', 'fenced_code'])
    return render_template('detail.html', post=post_data, content=content_html, active_lang=post_data['lang'])

@app.route('/guide')
def guide_list():
    """가이드 전체 목록 페이지"""
    lang = request.args.get('lang', 'en')
    guides = [g for g in CACHED_GUIDES if g['lang'] == lang]
    return render_template('guide_list.html', guides=guides, lang=lang, active_lang=lang)

@app.route('/guide/<guide_id>')
def guide_detail(guide_id):
    """가이드 상세 페이지: 본문 청소 및 맞춤 이미지 매핑"""
    path = os.path.join(GUIDE_DIR, f"{guide_id}.md")
    if not os.path.exists(path):
        abort(404)
        
    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read().strip()
        if '---' in raw:
            raw = '---' + raw.split('---', 1)[1]
        post_obj = frontmatter.loads(raw)

    post_data = dict(post_obj.metadata)
    post_data['id'] = guide_id
    post_data['lang'] = post_data.get('lang', 'en').strip().lower()
    
    # 본문 청소 (데이터 태그 제거)
    clean_body = re.sub(r'^(lang|title|summary|date):.*', '', post_obj.content, flags=re.MULTILINE).strip()
    
    html_content = markdown.markdown(clean_body, extensions=['tables', 'fenced_code'])
    base_id = guide_id.rsplit('_', 1)[0]
    img_url = GUIDE_IMAGES[abs(hash(base_id) * 97) % len(GUIDE_IMAGES)]
    
    return render_template('guide_detail.html', post=post_data, content=html_content, image=img_url, active_lang=post_data['lang'])

# ==========================================
# 💰 수익화 리다이렉트 (라쿠텐 & 클룩)
# ==========================================

@app.route('/booking/<course_id>')
def booking_redirect(course_id):
    """라쿠텐 고라: 본문에서 도도부현을 찾아 D+7일 날짜로 검색 리다이렉트"""
    area_code = 0
    md_path = os.path.join(CONTENT_DIR, f"{course_id}.md")
    
    if os.path.exists(md_path):
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for pref, code in AREA_MAP.items():
                if pref in content:
                    area_code = code
                    break

    # 일주일 뒤 날짜 계산
    target_date = datetime.now() + timedelta(days=7)
    
    rakuten_params = [
        ('search_c_name', ''),
        ('year', str(target_date.year)),
        ('month', str(target_date.month)),
        ('day', str(target_date.day)),
        ('widthday', '1'),
        ('search_mode', 'normal'),
        ('l-id', 'search_btn_search'),
        ('area[]', area_code if area_code > 0 else 12), # 못 찾으면 기본 12(지바)
        ('order', 'rec')
    ]
    
    target_url = "https://gora.golf.rakuten.co.jp/search/result/?" + urllib.parse.urlencode(rakuten_params)
    # 사용자 라쿠텐 파트너 ID 결합
    final_url = "https://hb.afl.rakuten.co.jp/hgc/53117f43.0bea4fc1.53117f44.cd5b3814/?pc=" + urllib.parse.quote(target_url) + "&link_type=text&ut=eyJwYWdlIjoidXJsIiwidHlwZSI6InRleHQiLCJjb2wiOjF9"
    
    return redirect(final_url)

@app.route('/travel/<item_type>/<course_id>')
def travel_redirect(item_type, course_id):
    """클룩: 렌터카, 픽업, eSIM 별 전용 파트너 링크 리다이렉트"""
    is_ko = course_id.endswith('_ko')
    links = {
        "rental": "https://klook.tpo.mx/llRQoxrb" if is_ko else "https://klook.tpo.mx/skGztuAJ",
        "pickup": "https://klook.tpo.mx/8qLZKsBY" if is_ko else "https://klook.tpo.mx/zPN5kiip",
        "esim":   "https://klook.tpo.mx/OBHJbySq" if is_ko else "https://klook.tpo.mx/696NKlPT"
    }
    return redirect(links.get(item_type, "https://klook.tpo.mx/470RSray"))

# ==========================================
# 🖼️ 파비콘 및 SEO 정적 서비스 (구글 봇 최적화)
# ==========================================

@app.route('/favicon.ico')
@app.route('/favicon-32x32.png')
@app.route('/favicon-48x48.png')
@app.route('/apple-touch-icon.png')
def serve_favicons():
    """구글 검색 아이콘 노출을 위해 루트 경로에서 직접 파일 서빙"""
    return send_from_directory(os.path.join(app.root_path, 'static', 'images'), 
                               request.path[1:], 
                               mimetype='image/png' if '.png' in request.path else 'image/vnd.microsoft.icon')

@app.route('/static/images/<path:filename>')
def serve_images(filename):
    """일반 이미지는 GCS로 리다이렉트하여 서버 부하 감소"""
    import time
    if any(x in filename for x in ['favicon', 'apple-touch']):
        return send_from_directory(os.path.join(app.root_path, 'static', 'images'), filename)
    return redirect(f"https://storage.googleapis.com/ok-project-assets/okcaddie/{filename}?v={int(time.time())}")

@app.route('/sitemap.xml')
def sitemap_xml(): return send_from_directory(STATIC_DIR, 'sitemap.xml')

@app.route('/robots.txt')
def robots_txt(): return send_from_directory(STATIC_DIR, 'robots.txt')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)