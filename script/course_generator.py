import os
import csv
import time
from datetime import datetime
from google import genai
from dotenv import load_dotenv
import concurrent.futures

# ==========================================
# ⚙️ 설정
# ==========================================
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')
IMAGES_DIR  = os.path.join(BASE_DIR, 'app', 'static', 'images')

TARGET_LANGS = ['en', 'ko']

CATEGORIES = {
    "en": ["Scenic View", "Links Style", "Mountain Course", "Resort", "Championship", "Beginner Friendly", "Private Club"],
    "ko": ["절경", "링크스", "산악코스", "리조트", "챔피언십", "초보자 환영", "프라이빗 클럽"],
}

def generate_course_md(safe_name, name, lat, lng, address, thumbnail, lang, features, booking_link):
    if not API_KEY:
        return False

    client = genai.Client(api_key=API_KEY)
    current_date = datetime.now().strftime('%Y-%m-%d')
    allowed_categories = ", ".join(CATEGORIES.get(lang, CATEGORIES["en"]))
    filename = f"{safe_name}_{lang}.md"
    filepath = os.path.join(CONTENT_DIR, filename)

    if os.path.exists(filepath):
        print(f"  ⏭️  이미 존재 → 스킵: {filename}")
        return True

    print(f"🚀 [{lang.upper()}] '{name}' 생성 중...")

    prompt = f"""
You are an elite golf travel journalist and SEO expert specializing in Japanese golf courses.
Write an EXTREMELY comprehensive, deeply detailed, and highly engaging golf course guide.
The total length MUST be 7,000 to 8,000 characters.

[Target Golf Course]
- Name: {name}
- Location: {address}
- Key Features: {features}
- Target Language: {lang} (ko=Korean, en=English)
- Allowed Categories: {allowed_categories}

[Instructions]
1. Output MUST be valid Markdown with YAML frontmatter.
2. Do NOT wrap in ```markdown blocks. Output raw text only.
3. Wrap 'title', 'summary', and 'image_prompt' values in double quotes (""). No line breaks inside quotes.
4. YAML frontmatter format:
---
lang: {lang}
title: "A highly catchy, SEO-optimized title for this golf course (single line)"
lat: {lat}
lng: {lng}
categories: ["Category 1", "Category 2"]
thumbnail: "{thumbnail}"
address: "{address}"
date: "{current_date}"
booking: "{booking_link}"
summary: "3-sentence highly engaging summary (single line)"
image_prompt: "A detailed Imagen prompt IN ENGLISH for a photorealistic wide aerial or fairway-level photo of this golf course. Include: lush green fairways, course layout, surrounding landscape (mountains/ocean/forest), weather, lighting, no people, cinematic golf photography (single line)"
---

5. CATEGORY RULE: Select 1 to 3 categories from the Allowed Categories that BEST MATCH the Key Features.
6. Write the body in the Target Language ({lang}).
7. To reach 7,000~8,000 characters, include ALL these sections:
   - **Introduction:** The unique appeal and atmosphere of this course.
   - **Course Overview:** Number of holes, par, total yardage, course rating/slope, architect.
   - **Hole-by-Hole Highlights:** Describe the most iconic and challenging holes in detail.
   - **Course Conditions & Facilities:** Greens quality, fairway conditions, clubhouse, pro shop, restaurant, locker rooms.
   - **Caddie & Cart Information:** Caddie system, GPS cart availability, caddie fees.
   - **Scenic Beauty & Surroundings:** Views, nature, seasonal highlights (cherry blossoms, autumn foliage).
   - **Access Guide:** Step-by-step from major cities, nearest station, shuttle bus info.
   - **Green Fees & Booking Tips:** Weekday/weekend rates, peak season, reservation advice.
   - **FAQ & Tips:** Dress code, rental clubs, best season to visit.
   - **Conclusion:** A powerful closing recommendation.

8. Write eloquently, passionately, and informatively for golf enthusiasts.
"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        content = response.text.strip()

        if content.startswith("```markdown"): content = content[11:]
        elif content.startswith("```"): content = content[3:]
        if content.endswith("```"): content = content[:-3]
        content = content.strip()

        os.makedirs(CONTENT_DIR, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ 완료: {filename} (약 {len(content)}자)")
        return True

    except Exception as e:
        print(f"❌ 에러 ({name} - {lang}): {e}")
        return False


def process_csv(csv_filename="courses.csv", limit=5):
    csv_path = os.path.join(SCRIPT_DIR, 'csv', csv_filename)
    if not os.path.exists(csv_path):
        print(f"❌ CSV 없음: {csv_path}")
        return

    tasks = []
    processed = set()
    skipped = 0

    with open(csv_path, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if len(processed) >= limit:
                break

            name = (row.get('Name') or '').strip()
            if not name:
                continue

            safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "").replace("&", "and")
            lat      = (row.get('Lat') or '').strip()
            lng      = (row.get('Lng') or '').strip()
            address  = (row.get('Address') or '').strip()
            features = (row.get('Features') or '').strip()
            booking  = (row.get('Booking') or '').strip()

            thumbnail = f"/static/images/{safe_name}.jpg"
            needs_gen = False

            for lang in TARGET_LANGS:
                fp = os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md")
                if os.path.exists(fp):
                    skipped += 1
                else:
                    tasks.append((safe_name, name, lat, lng, address, thumbnail, lang, features, booking))
                    needs_gen = True

            if needs_gen:
                processed.add(safe_name)

    if not tasks:
        print("💡 새로 생성할 파일이 없습니다.")
        return

    print(f"\n⛳ {len(tasks)}개 작업 동시 처리 시작...\n")
    generated = 0
    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(generate_course_md, *t) for t in tasks]
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                generated += 1

    elapsed = time.time() - start
    print("-" * 50)
    print(f"🎉 완료! ({elapsed:.1f}초)")
    print(f"   골프장: {len(processed)}곳 / 파일: {generated}개 생성 / {skipped}개 스킵")


if __name__ == "__main__":
    print("\n⛳ OKCaddie 골프장 컨텐츠 자동 생성 봇 ⛳")
    print("-" * 50)
    if not API_KEY:
        print("⚠️ GEMINI_API_KEY가 없습니다!")
    else:
        process_csv(csv_filename="courses.csv", limit=2)
