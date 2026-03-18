import os
import csv
import time
from datetime import datetime
from google import genai
from dotenv import load_dotenv

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')
IMAGES_DIR = os.path.join(BASE_DIR, 'app', 'static', 'images')

TARGET_LANGS = ['en', 'ko']

CATEGORIES = {
    "en":["Private Bath", "Tattoo OK", "Great View", "Luxury", "Local"],
    "ko":["가족탕", "타투 허용", "절경", "고급 료칸", "로컬"],
    "ja":["貸切風呂", "タトゥーOK", "絶景", "高級", "秘湯"]
}

def generate_onsen_md(safe_name, name, lat, lng, address, thumbnail, lang, features, agoda_link):
    if not API_KEY:
        print("❌ 오류: .env 파일에서 GEMINI_API_KEY를 찾을 수 없습니다.")
        return False

    client = genai.Client(api_key=API_KEY)
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    allowed_categories = ", ".join(CATEGORIES.get(lang, CATEGORIES["en"]))
    filename = f"{safe_name}_{lang}.md"
    
    print(f"⏳ '{name}' 메가 콘텐츠 작성 중... (약 7~8천자 목표) -> {filename}")

    # 💡 [수정] categories 콜론 뒤에 띄어쓰기를 추가하고, AI에게 절대 줄바꿈을 하지 말라고 강력히 지시했습니다.
    prompt = f"""
    You are an elite travel journalist and SEO expert specializing in Japanese Onsens and luxury Ryokans.
    Your task is to write an EXTREMELY comprehensive, deeply detailed, and highly engaging travel guide about the following onsen. 
    The total length of your response MUST be very long, aiming for 7,000 to 8,000 characters.[Target Onsen Information]
    - Name: {name}
    - Location: {address}
    - Key Features: {features}
    - Target Language: {lang} (ko=Korean, en=English)[Instructions]
    1. The output MUST be a valid Markdown file containing YAML frontmatter.
    2. Do NOT wrap the output in ```markdown blocks, just output the raw text.
    3. VERY IMPORTANT: You MUST wrap the values for 'title', 'summary', and 'image_prompt' in double quotes (""). Do NOT use line breaks inside the quotes.
    4. The YAML frontmatter must be exactly in this format (pay attention to the spaces after colons):
    ---
    lang: {lang}
    title: "Write a highly catchy, emotional, and attractive SEO title here (single line)"
    lat: {lat}
    lng: {lng}
    categories: [{allowed_categories}]
    thumbnail: "{thumbnail}"
    address: "{address}"
    date: "{current_date}"
    agoda: "{agoda_link}"
    summary: "Write a 3-sentence highly engaging summary here (single line)"
    image_prompt: "Write a highly detailed Midjourney image generation prompt IN ENGLISH here (single line)"
    ---

    5. After the frontmatter, write the body of the blog post in the Target Language ({lang}).
    6. VERY IMPORTANT: Translate all 'Key Features' into the Target Language. Do NOT use the original language of the 'Key Features' in the body text.
    7. To reach the 7,000 - 8,000 character goal, you MUST include the following deeply detailed sections using Markdown headings (##, ###):
       - **Introduction:** Deep dive into the vibe, the first impression, and why this onsen is special.
       - **History & Tradition:** The rich history of the ryokan or the local hot spring town.
       - **Deep Dive into the Baths:** Detailed description of the open-air baths (rotemburo), private baths (kashikiri), water quality, minerals, health benefits, and the exact view from the bath.
       - **Rooms & Accommodation:** A vivid description of the traditional tatami rooms, western-style beds, architecture, and wabi-sabi aesthetics.
       - **Gastronomy (Kaiseki Dinner):** A mouth-watering description of the traditional multi-course dinner, local seasonal ingredients, and breakfast.
       - **Things to Do Around the Area:** Detailed guide to nearby tourist spots, nature walks, or local streets.
       - **Access Guide:** Step-by-step instructions on how to get there from major cities or airports.
       - **FAQ & Practical Tips:** Tattoo policy, best season to visit, and booking tips.
       - **Conclusion:** A powerful closing statement.

    8. Write eloquently, passionately, and informatively. Expand on details rather than repeating the same points. Use bold text for emphasis.
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

        filepath = os.path.join(CONTENT_DIR, filename)
        os.makedirs(CONTENT_DIR, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ 완료: {filename} (생성된 길이: 약 {len(content)}자)")
        return True

    except Exception as e:
        print(f"❌ 오류 발생 ({name}): {e}")
        return False

def process_csv_auto(csv_filename="onsens.csv", limit=5):
    csv_path = os.path.join(SCRIPT_DIR, 'csv', csv_filename)
    
    if not os.path.exists(csv_path):
        print(f"❌ 오류: {csv_path} 파일을 찾을 수 없습니다.")
        return

    processed_onsen_count = 0 
    total_files_generated = 0 
    skipped_files_count = 0   

    with open(csv_path, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            if processed_onsen_count >= limit:
                break
            
            name = (row.get('Name') or '').strip()
            if not name: continue
            
            safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "")
            
            lat = (row.get('Lat') or '').strip()
            lng = (row.get('Lng') or '').strip()
            address = (row.get('Address') or '').strip()
            features = (row.get('Features') or '').strip()
            agoda_link = (row.get('Agoda') or '').strip()

            thumbnail = ""
            for ext in['.jpg', '.jpeg', '.png', '.webp']:
                img_path = os.path.join(IMAGES_DIR, f"{safe_name}{ext}")
                if os.path.exists(img_path):
                    thumbnail = f"/static/images/{safe_name}{ext}"
                    break 
            
            if not thumbnail:
                thumbnail = f"/static/images/{safe_name}.jpg"

            onsen_processed_flag = False

            for lang in TARGET_LANGS:
                filename = f"{safe_name}_{lang}.md"
                filepath = os.path.join(CONTENT_DIR, filename)
                
                if os.path.exists(filepath):
                    skipped_files_count += 1
                    continue 
                
                success = generate_onsen_md(safe_name, name, lat, lng, address, thumbnail, lang, features, agoda_link)
                if success:
                    total_files_generated += 1
                    onsen_processed_flag = True
                    time.sleep(5) 
            
            if onsen_processed_flag:
                processed_onsen_count += 1
            
    print("-" * 50)
    print(f"🎉 자동 생성 완료!")
    print(f"   - 이번에 처리된 온천 장소: {processed_onsen_count} 곳")
    print(f"   - 이번에 새로 생성된 파일: {total_files_generated} 개")
    print(f"   - 이미 있어서 건너뛴 파일: {skipped_files_count} 개")

if __name__ == "__main__":
    print("\n♨️ OKOnsen 메가 콘텐츠 한/영 자동 생성 봇 (Powered by Gemini) ♨️")
    print("-" * 50)
    
    if not API_KEY:
        print("⚠️ 경고: .env 파일에서 GEMINI_API_KEY를 읽어오지 못했습니다!\n")
    else:
        process_csv_auto(csv_filename="onsens.csv", limit=5)