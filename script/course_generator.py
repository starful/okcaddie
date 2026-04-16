import os, csv, time, sys
import concurrent.futures
from google import genai
from dotenv import load_dotenv

# 설정 로드
load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

CSV_PATH = 'script/csv/courses.csv'
CONTENT_DIR = "app/content"
os.makedirs(CONTENT_DIR, exist_ok=True)

def generate_course_task(data):
    safe_name = data['safe_name']
    lang = data['lang']
    filepath = os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md")

    if os.path.exists(filepath):
        return None

    # [핵심] 초장문 생성을 위한 정교한 프롬프트
    prompt = f"""
    You are an elite Japanese golf travel journalist and a technical course rater. 
    Write an EXTREMELY COMPREHENSIVE, deeply technical, and engaging golf course review for "{data['name']}".
    
    [GOAL]
    The total length MUST be between 8,000 and 9,000 characters (including spaces). 
    Do not summarize. Provide deep, granular details for every section.
    Language: {lang} (ko=Korean, en=English).

    [Structure & Specific Requirements]
    1. **Introduction (1,000+ chars):** The history of the club, its prestige in Japan, the natural landscape, and the first impression upon arrival.
    2. **Architect & Design Philosophy (1,500+ chars):** Deep dive into the architect (e.g., Seiichi Inoue, Robert Trent Jones Jr., etc.), the strategic use of bunkers, water hazards, and terrain elevation. Explain the 'risk and reward' elements.
    3. **Signature Holes Analysis (2,000+ chars):** Pick at least 4 specific holes. Describe the yardage, the view from the tee, the landing zone, the green's undulation, and the exact strategy needed to save par.
    4. **Clubhouse & Luxury Facilities (1,500+ chars):** Detailed review of the clubhouse architecture, the locker rooms, and especially the Onsen (natural hot spring) facilities. Mention the dining experience and signature dishes.
    5. **Seasonal Guide & Logistics (1,000+ chars):** Best months to visit, turf condition (Bent vs Korai grass), wind patterns, and detailed access from major cities.
    6. **Expert Verdict (1,000+ chars):** Final rating, who this course is for, and a concluding professional recommendation.

    [YAML Frontmatter]
    ---
    lang: "{lang}"
    title: "The Ultimate Guide to {data['name']}: Strategy, Luxury, and Vibe ({lang})"
    lat: {data['lat']}
    lng: {data['lng']}
    categories: [{data['features']}]
    thumbnail: "/static/images/{safe_name}.jpg"
    address: "{data['address']}"
    date: "2026-04-15"
    booking: "{data['booking']}"
    summary: "A massive, expert-level 8,000-character guide to {data['name']}."
    ---
    
    (Start writing the long-form content now in {lang}. Ensure professional formatting with H2 and H3 tags.)
    """

    try:
        # 초장문 생성을 위해 gemini-2.0-flash 사용 (유료 API 권장)
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=prompt
        )
        content = response.text.replace("```markdown", "").replace("```", "").replace("## yaml", "").strip()
        
        # 실제 생성된 길이 체크 (로그용)
        actual_length = len(content)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"✅ Success: {safe_name}_{lang} ({actual_length} chars)"
    except Exception as e:
        return f"❌ Error: {safe_name}_{lang} -> {e}"

def process_courses(limit=5):
    if not os.path.exists(CSV_PATH):
        print(f"❌ CSV 없음: {CSV_PATH}")
        return

    tasks = []
    with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        new_topic_count = 0
        
        for row in reader:
            if new_topic_count >= limit: break
            
            name = row['Name'].strip()
            safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "").replace("&", "and").replace(".", "")
            
            if not (os.path.exists(os.path.join(CONTENT_DIR, f"{safe_name}_en.md")) and 
                    os.path.exists(os.path.join(CONTENT_DIR, f"{safe_name}_ko.md"))):
                for lang in ['en', 'ko']:
                    tasks.append({
                        'safe_name': safe_name, 'name': name, 'lat': row['Lat'], 'lng': row['Lng'],
                        'address': row['Address'], 'features': row['Features'], 
                        'booking': row['Booking'], 'lang': lang
                    })
                new_topic_count += 1

    print(f"🔥 초장문 컨텐츠 생성 시작 (목표: {new_topic_count}개 코스, 쓰레드 5개)")

    # 초장문 생성 시에는 쓰레드 수를 너무 높이면 API 응답이 끊길 수 있으므로 5~10개 권장
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(generate_course_task, t) for t in tasks]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: print(res)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_limit = int(sys.argv[1])
    else:
        run_limit = 5 # 초장문이므로 한 번에 2개 주제(4개 파일)씩 생성 권장
        
    process_courses(limit=run_limit)