import os
import csv
import time
from datetime import datetime
from google import genai
from dotenv import load_dotenv
import concurrent.futures

# ==========================================
# ⚙️ 설정 로드 및 경로 지정
# ==========================================
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')

TARGET_LANGS = ['en', 'ko']

# [중요] 필터 매칭을 위한 표준 영어 카테고리
ENG_CATEGORIES = ["Value for Money", "Premium / Luxury", "Public Tournament", "Stay & Play", "Easy Booking", "Private Club"]

def generate_course_md(safe_name, name, lat, lng, address, thumbnail, lang, features, booking_link):
    if not API_KEY:
        print("❌ GEMINI_API_KEY missing.")
        return False

    client = genai.Client(api_key=API_KEY)
    current_date = datetime.now().strftime('%Y-%m-%d')
    filename = f"{safe_name}_{lang}.md"
    filepath = os.path.join(CONTENT_DIR, filename)

    # 이미 파일이 있으면 건너뜀 (비용 절약)
    if os.path.exists(filepath):
        print(f"  ⏭️  Skip: {filename}")
        return True

    print(f"🚀 [{lang.upper()}] '{name}' Generating Content...")

    # [상세 프롬프트] 8,000자 이상의 고품질 컨텐츠 유도
    prompt = f"""
You are an elite Japanese golf travel journalist and SEO expert. 
Write an EXTREMELY comprehensive, deeply detailed, and highly engaging golf course guide for "{name}".
The total length MUST be 7,000 to 8,000 characters.

[Instructions]
1. Output RAW Markdown with YAML frontmatter. NO code blocks (```).
2. Use ONLY these English terms for 'categories' field in frontmatter: {", ".join(ENG_CATEGORIES)}
3. Body Language: {lang} (ko=Korean, en=English).

[YAML Frontmatter Format]
---
lang: {lang}
title: "Catchy SEO Title in {lang}"
lat: {lat}
lng: {lng}
categories: ["Category from list"]
thumbnail: "{thumbnail}"
address: "{address}"
date: "{current_date}"
booking: "{booking_link}"
summary: "3-sentence engaging summary in {lang}"
image_prompt: "High-end cinematic photography prompt in English"
---

[Body Content Sections - Write in {lang}]
- **Introduction:** The prestige and unique charm of this course.
- **Price & Booking:** Estimated weekday/weekend fees (JPY), seasonal tips.
- **Course Accessibility:** Explain if it's Public, Semi-Private, or Private (Member-only).
- **Course Highlights:** Strategic layout, architect, signature holes description.
- **Facilities:** Clubhouse, restaurant, pro-shop, and especially the Onsen/Bath quality.
- **Scenic Beauty:** Best season to visit, nature, and surrounding views.
- **Access:** Detailed directions from the nearest major city or station.
- **Final Verdict:** Expert recommendation for travelers.
"""

    try:
        # Gemini 2.0 Flash 모델 사용
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        content = response.text.strip()

        # 불필요한 마크다운 기호 제거 (백틱 등)
        if content.startswith("```"):
            content = "\n".join(content.splitlines()[1:-1]) if content.endswith("```") else "\n".join(content.splitlines()[1:])
        content = content.strip()

        os.makedirs(CONTENT_DIR, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ Success: {filename} ({len(content)} chars)")
        return True

    except Exception as e:
        print(f"❌ Error for {name}: {e}")
        return False

def process_csv(limit=25):
    csv_path = os.path.join(SCRIPT_DIR, 'csv', 'courses.csv')
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return

    tasks = []
    with open(csv_path, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for i, row in enumerate(reader):
            if i >= limit: break
            name = row.get('Name', '').strip()
            if not name: continue
            
            # 파일명 안전하게 변환
            safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "").replace("&", "and").replace(".", "")
            
            for lang in TARGET_LANGS:
                tasks.append((
                    safe_name, name, row.get('Lat'), row.get('Lng'), 
                    row.get('Address'), f"/static/images/{safe_name}.jpg", 
                    lang, row.get('Features'), row.get('Booking')
                ))

    # 최대 10개의 쓰레드로 병렬 처리
    print(f"⛳ Processing {len(tasks)} files...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(lambda p: generate_course_md(*p), tasks)

if __name__ == "__main__":
    process_csv(limit=20)