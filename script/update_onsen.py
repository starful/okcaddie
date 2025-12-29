import os
import time
import frontmatter
import google.generativeai as genai
from dotenv import load_dotenv
import warnings

warnings.filterwarnings("ignore")

# --- 설정 ---
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
CONTENT_DIR = os.path.join(os.path.dirname(__file__), '../app/content')
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# 모델 자동 선택 (생략 가능하지만 안전하게 유지)
def get_best_model():
    try:
        available_models = [m.name for m in genai.list_models()]
        for m in available_models:
            if 'gemini-1.5-pro' in m: return genai.GenerativeModel(m)
        for m in available_models:
            if 'gemini-1.5-flash' in m: return genai.GenerativeModel(m)
        return genai.GenerativeModel("gemini-pro")
    except:
        return genai.GenerativeModel("gemini-pro")

model = get_best_model()

def generate_onsen_content(shrine_name, address):
    prompt = f"""
    You are a travel guide editor.
    I will provide a Japanese shrine name and its address.
    Please find ONE best **nearby Onsen (Hot Spring)** for a day-trip traveler.
    
    Target Shrine: {shrine_name}
    Address: {address}

    Requirements:
    1. Output Language: English.
    2. Format: Markdown.
    3. Content Structure:
       - Header: ### ♨️ Relax at a Nearby Onsen: [Onsen Name in English] ([Japanese Name])
       - Description: 3~4 sentences about why it's good (water quality, view, or atmosphere).
       - SEO Keywords to include naturally: "day-trip onsen", "relaxing", "nearby {shrine_name}".
    
    Output ONLY the Markdown content. Do not say "Here is the info".
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except:
            time.sleep(2)
            continue
    return None

def main():
    print(f"🚀 온천 정보 업데이트 (재시도) 시작")
    
    files = [f for f in os.listdir(CONTENT_DIR) if f.endswith('.md')]
    total = len(files)
    success_count = 0
    skip_count = 0
    
    for idx, filename in enumerate(files):
        filepath = os.path.join(CONTENT_DIR, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            # [수정] 단순히 이모지(♨️)가 아니라, "Relax at a Nearby Onsen" 문구가 있는지 확인
            # 이렇게 하면 기존에 온천 언급이 있어도, '새로 만든 추천 섹션'이 없으면 추가함
            if "Relax at a Nearby Onsen" in post.content: 
                skip_count += 1
                if skip_count % 10 == 0:
                    print(f"⏩ 스킵 중... (누적 {skip_count}개)")
                continue
                
            shrine_name = post.get('title', 'Unknown Shrine')
            address = post.get('address', '')
            
            print(f"[{idx+1}/{total}] 🤖 생성 중: {shrine_name}...")
            
            new_content = generate_onsen_content(shrine_name, address)
            
            if new_content:
                post.content += "\n\n***\n\n" + new_content
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(frontmatter.dumps(post))
                print(f"   ✅ 완료")
                success_count += 1
                time.sleep(1)
            else:
                print(f"   ❌ 실패")
                
        except Exception as e:
            print(f"   ❌ 에러: {filename} - {e}")

    print(f"\n🎉 작업 종료. 총 {success_count}개 업데이트 됨.")

if __name__ == "__main__":
    main()