import os, csv, time, sys, re
import concurrent.futures
from google import genai
from dotenv import load_dotenv

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================
load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

CSV_PATH = 'script/csv/courses.csv'
CONTENT_DIR = "app/content"
os.makedirs(CONTENT_DIR, exist_ok=True)

# 생성할 코스 주제(Topic)의 개수 제한 (명령행 인자가 없을 경우 기본값)
DEFAULT_LIMIT = 30

def generate_course_task(data):
    """실제 Gemini API를 호출하여 초장문 리뷰를 생성하는 워커 함수"""
    safe_name = data['safe_name']
    lang = data['lang']
    filepath = os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md")

    # 이미 파일이 존재하면 건너뜀 (이미 있는 파일을 다시 쓰고 싶다면 이 부분을 주석 처리하세요)
    # if os.path.exists(filepath):
    #     return f"  ⏭️  Skip: {safe_name}_{lang}"

    # [핵심] 구글 색인을 위한 고도화된 프롬프트
    prompt = f"""
    You are an elite Japanese golf course rater and a professional senior caddy with 20 years of experience.
    Your mission is to write a MASTERPIECE review for "{data['name']}".
    This content is for a premium golf travel media 'OKCaddie' and must be SEO-optimized to rank #1 on Google.

    [GOAL]
    - Total length: 8,000 to 9,000 characters (including spaces).
    - Tone: Highly professional, technical, yet engaging.
    - Language: {lang} (ko=Korean, en=English).

    [Required Sections & Depth]
    1. **Historical Prestige (1,000+ chars):** Deep dive into the club's history, founding story, and its status in the Japanese golf hierarchy.
    2. **Strategic Architectural Analysis (2,000+ chars):** Detail the design philosophy of the architect. Analyze the fairway grass (Bent vs Korai), bunker placement logic, and the challenge of the greens. Explain the 'Risk and Reward' for high/low handicappers.
    3. **Hole-by-Hole Masterclass (2,500+ chars):** Pick 4 specific, crucial holes. For each, describe the tee-shot view, hidden hazards, yardage strategy, and the exact putting line. Use technical terms like 'undulation', 'stimpmeter', 'gradient'.
    4. **Clubhouse & The Onsen Experience (1,500+ chars):** Describe the clubhouse vibe. Critically review the locker rooms and the 'Daikokujo' (Grand Bath/Onsen). Mention the mineral quality of the water and the relaxation it provides after 18 holes.
    5. **Gourmet Dining (1,000+ chars):** Specific menu recommendations. Don't just say 'good food'. Mention specific dishes like 'Kurobuta Tonkatsu', 'Local Soba', or 'Premium Unagi' and their taste profiles.
    6. **Seasonal Tips & Final Verdict (1,000+ chars):** Best months for the best turf. Detailed access guide from major cities (Tokyo/Osaka/Fukuoka). Conclude with a 'Caddy's Secret Tip'.

    [Formatting Instructions]
    - Output raw Markdown.
    - Use H2 (##) and H3 (###) for structure.
    - Start IMMEDIATELY with YAML frontmatter. Wrap ALL values in double quotes.
    
    [YAML Frontmatter Format]
    ---
    lang: "{lang}"
    title: "The Definitive Guide to {data['name']}: An Expert Review ({lang})"
    lat: "{data['lat']}"
    lng: "{data['lng']}"
    categories: "{data['features']}"
    thumbnail: "/static/images/{safe_name}.jpg"
    address: "{data['address']}"
    date: "2026-04-15"
    booking: "/booking/{safe_name}_{lang}"
    summary: "A comprehensive 9,000-character master guide to {data['name']}, covering strategy, history, and luxury facilities."
    ---
    """

    try:
        # gemini-2.0-flash 모델 사용 (장문 생성에 최적화)
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=prompt
        )
        content = response.text.strip()

        # AI가 넣은 코드 블록 찌꺼기 제거
        content = re.sub(r'^```markdown\s*', '', content)
        content = re.sub(r'^```yaml\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        content = content.replace('## yaml', '').strip()

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"✅ Success: {safe_name}_{lang} ({len(content)} characters)"

    except Exception as e:
        return f"❌ Error: {safe_name}_{lang} -> {e}"

def process_courses(limit):
    """CSV를 읽어 생성 대상을 수집하고 병렬 처리를 실행"""
    if not os.path.exists(CSV_PATH):
        print(f"❌ CSV 없음: {CSV_PATH}")
        return

    tasks = []
    with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        new_topic_count = 0
        
        for row in reader:
            if new_topic_count >= limit: 
                break
            
            name = row['Name'].strip()
            # 파일명 안전하게 변환
            safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "").replace("&", "and").replace(".", "")
            
            # 영문/국문 세트 중 하나라도 없으면 생성 시도
            if not (os.path.exists(os.path.join(CONTENT_DIR, f"{safe_name}_en.md")) and 
                    os.path.exists(os.path.join(CONTENT_DIR, f"{safe_name}_ko.md"))):
                for lang in ['en', 'ko']:
                    tasks.append({
                        'safe_name': safe_name, 'name': name, 'lat': row['Lat'], 'lng': row['Lng'],
                        'address': row['Address'], 'features': row['Features'], 
                        'booking': row['Booking'], 'lang': lang
                    })
                new_topic_count += 1

    if not tasks:
        print("🙌 모든 코스 콘텐츠가 이미 최신 상태입니다.")
        return

    print(f"🔥 초장문 전문가 리뷰 생성 시작 (주제: {new_topic_count}개, 파일: {len(tasks)}개)")
    print(f"🚀 동시 실행 쓰레드: 5 (장문 생성을 위해 속도 조절 중...)")

    # 장문 생성 시에는 쓰레드를 너무 많이 쓰면 API 타임아웃 확률이 높으므로 5개로 제한
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(generate_course_task, t) for t in tasks]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: print(res)

if __name__ == "__main__":
    # 사용법: python script/course_generator.py [숫자]
    if len(sys.argv) > 1:
        try:
            run_limit = int(sys.argv[1])
        except ValueError:
            run_limit = DEFAULT_LIMIT
    else:
        run_limit = DEFAULT_LIMIT
        
    start_time = time.time()
    process_courses(limit=run_limit)
    print(f"\n✨ 모든 작업 완료! (소요 시간: {time.time() - start_time:.1f}초)")