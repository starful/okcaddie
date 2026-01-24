import os
import csv
import re
import time
import logging
import argparse
import unicodedata
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. 환경 설정 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

CSV_PATH = os.path.join(SCRIPT_DIR, 'csv', 'jinja.csv')
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
LOG_PATH = os.path.join(LOG_DIR, 'processed_jinja.txt')
ENV_PATH = os.path.join(BASE_DIR, '.env')
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')

load_dotenv(ENV_PATH)

if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, f"jinja_gen_{datetime.now().strftime('%Y%m%d')}.log"), encoding='utf-8')
    ]
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logging.error("❌ GEMINI_API_KEY not found in .env")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

# 모델을 'gemini-2.0-flash'로 고정
MODEL_NAME = "gemini-flash-latest"
model = genai.GenerativeModel(MODEL_NAME)
logging.info(f"✅ Using fixed model: {MODEL_NAME}")


# 한글 카테고리 -> 영어 매핑
CATEGORY_EN_MAP = {
    '재물': 'Wealth',
    '사랑': 'Love',
    '건강': 'Health',
    '학업': 'Success', # Study -> Success 통합
    '안전': 'Safety',
    '성공': 'Success',
    '역사': 'History'
}

# --- 2. 헬퍼 함수 ---
def normalize_text(text):
    if not text: return ""
    return unicodedata.normalize('NFKC', str(text)).strip()

def get_target_row():
    processed_items = set()
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, 'r', encoding='utf-8') as f:
                processed_items = set(normalize_text(line) for line in f)
        except Exception: pass

    if not os.path.exists(CSV_PATH):
        logging.error(f"❌ CSV file missing: {CSV_PATH}")
        return None, None

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            shrine_name = row.get('shrine_name', '').strip()
            if shrine_name and normalize_text(shrine_name) not in processed_items:
                return row, shrine_name
    return None, None

# --- 3. 프롬프트 생성 (온천 정보 추가됨) ---
def generate_jinja_prompt(shrine_name, region):
    return f"""
# Role
A professional travel writer specializing in Japanese history, mythology, and culture.

# Topic: Guide to "{shrine_name}" (Located in {region})

# Requirements
- Target Audience: Global tourists visiting Japan.
- Language: **English** (Native, engaging tone).
- Length: Around 1,200 ~ 1,500 words.
- **[CRITICAL]**: Do NOT write any intro. Start directly with the Title (H1).

# Output Format (Markdown)
1. The first line MUST be the Title starting with `#`.
2. The last line MUST be **FILENAME: shrine_name_english_slug**.

---
# Content Structure
# {shrine_name} (English Title)

### 1. 🙏 Introduction: Deities & History
- Who is enshrined here? (Kami)
- What is the origin story?

***
### 2. ⛩️ Exploring the Grounds
- Torii gates, Main Hall, Atmosphere.
- Must-see spots within the shrine.

***
### 3. 📜 Goshuin & Omamori
- Unique charms and stamps available here.

***
### 4. 🗺️ Access & Info
(Table: Address, Nearest Station, Hours)

***
### 5. ✨ Conclusion

***
### ♨️ Relax at a Nearby Onsen: [Name of Onsen]
- Please recommend ONE best nearby Onsen (Hot Spring) for a day-trip.
- Write 3~4 sentences about why it's good (water quality, view, etc).
- Include the Japanese name of the Onsen in parentheses.

---

FILENAME: (English slug here)
"""

# --- 4. 마크다운 저장 ---
def save_to_markdown(title, content, row_data, filename_slug):
    if not os.path.exists(CONTENT_DIR): os.makedirs(CONTENT_DIR)

    filename = f"{filename_slug}.md"
    filepath = os.path.join(CONTENT_DIR, filename)

    # 본문에서 요약문 추출
    body = re.sub(r'#.*?\n', '', content).strip()
    excerpt = body[:160].replace('\n', ' ') + "..."

    # 카테고리 변환
    kor_cat = row_data.get('Category', '역사')
    eng_cat = CATEGORY_EN_MAP.get(kor_cat, 'History')
    categories = [eng_cat]

    tags = ["Japan", "Shrine", "Travel", eng_cat]
    region_raw = row_data.get('Region', '')
    region_match = re.search(r'\((.*?)\)', region_raw)
    if region_match:
        tags.append(region_match.group(1))
    
    lat = row_data.get('lat', '35.6895') # CSV에 없으면 기본값
    lng = row_data.get('lng', '139.6917')
    addr = row_data.get('address', row_data.get('shrine_name', ''))
    
    image_path = f"/content/images/{filename_slug}.webp"

    md_content = f"""---
layout: post
title: "{title}"
date: {datetime.now().strftime('%Y-%m-%d')}
categories: {categories}
tags: {tags}
thumbnail: {image_path}
lat: {lat}
lng: {lng}
address: "{addr}"
excerpt: "{excerpt}"
---

{content}
"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        logging.info(f"💾 Saved: {filepath}")
        return True
    except Exception as e:
        logging.error(f"❌ Save Failed: {e}")
        return False

# --- 5. 메인 실행 ---
if __name__ == "__main__":
    # ==========================================
    # [수정] 생성 개수를 5개로 고정합니다.
    # ==========================================
    TARGET_COUNT = 15

    logging.info(f"🚀 Generator Started (Target: {TARGET_COUNT})")

    success_count = 0
    for i in range(TARGET_COUNT):
        row, shrine_name = get_target_row()
        if not shrine_name:
            logging.info("🎉 All shrines processed.")
            break

        logging.info(f"[{i+1}/{TARGET_COUNT}] Generating: {shrine_name}")
        
        try:
            region = "Japan"
            if '(' in row.get('Region', ''):
                region = row['Region'].split('(')[1].replace(')', '')

            prompt = generate_jinja_prompt(shrine_name, region)
            resp = model.generate_content(prompt)
            content = resp.text
            
            header_match = re.search(r'^#\s+.+', content, re.MULTILINE)
            if header_match:
                content = content[header_match.start():]
            else:
                content = f"# {shrine_name}\n\n" + content

            filename_slug = f"shrine_{int(time.time())}"
            file_match = re.search(r'FILENAME:\s*([\w_]+)', content)
            if file_match:
                filename_slug = file_match.group(1).strip().lower()
                content = content.replace(file_match.group(0), '').strip()

            t_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            title = t_match.group(1).strip().replace('**', '') if t_match else shrine_name
            
            content = re.sub(r'^#\s+.*?\n', '', content, count=1).strip()
            
            if save_to_markdown(title, content, row, filename_slug):
                with open(LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write(f"{normalize_text(shrine_name)}\n")
                success_count += 1
                time.sleep(5) # 유료 API라 5초면 충분

        except Exception as e:
            logging.error(f"❌ Error: {e}")
            time.sleep(5)
            continue

    logging.info(f"✨ Done. Generated {success_count} articles.")