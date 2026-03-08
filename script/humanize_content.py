import os
import frontmatter
import google.generativeai as genai
import time
import re
from dotenv import load_dotenv

# --- 1. 설정 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')

# .env 파일 로드 (API 키 확인)
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("❌ Error: GEMINI_API_KEY not found in .env file.")
    exit(1)

genai.configure(api_key=API_KEY)
# 유료 API에 최적화된 가장 빠른 모델 사용
model = genai.GenerativeModel("gemini-flash-latest")

def humanize_file(filepath):
    """
    주어진 마크다운 파일을 읽고, AI를 사용하여 내용을 '인간적으로' 다듬은 후 저장합니다.
    """
    try:
        post = frontmatter.load(filepath)
        original_content = post.content
        lang = post.get('lang', 'en')
        
        # 이미 수정된 파일인지 확인
        if post.get('humanized') == True:
            # print(f"⏩ Skip: {os.path.basename(filepath)}")
            return

        print(f"⚡ Humanizing... [{lang.upper()}]: {os.path.basename(filepath)}")

        if lang == 'ko':
            prompt = f"""
            Role: 10년 차 일본 여행 전문 블로거.
            Task: 아래 설명문을 **생생한 1인칭 여행기(에세이 스타일)**로 다시 작성해주세요.
            
            [작성 지침]
            1. **말투:** "~해요", "~했답니다" 같은 친근하고 부드러운 구어체 사용.
            2. **시점:** "저는...", "제가 느낀 건..." 처럼 1인칭 주어 사용.
            3. **감각 묘사:** 시각, 소리, 냄새, 분위기를 구체적으로 묘사.
            4. **꿀팁 추가:** 문단 중간중간에 "💡 솔직한 팁:", "⚠️ 주의사항:" 포함.
            5. **구조 유지:** 기존 헤더(#, ##)와 이미지 링크(![...](...)) 위치 유지.
            6. **결론:** "## 6. ✨ Conclusion:" 섹션으로 마무리.

            [Original Content]:
            {original_content}
            """
        elif lang == 'ja':
            prompt = f"""
            Role: 日本の人気旅ブロガー。
            Task: 以下の文章を、**臨場感あふれる一人称の旅行記**にリライトしてください。

            [執筆ガイドライン]
            1. **文体:** 「〜です」「〜ます」調で親しみやすく。
            2. **視点:** 個人的な感想や体験談を交える。
            3. **五感の描写:** その場の空気感、音、香りなどを伝える。
            4. **アドバイス:** 「💡 ここだけの話：」「⚠️ 注意点：」を含める。
            5. **構成維持:** Markdownヘッダー(#, ##)や画像リンク(![...](...))は維持。
            6. **結び:** 「## 6. ✨ Conclusion:」セクションで締めくくる。

            [Original Content]:
            {original_content}
            """
        else: # English (en)
            prompt = f"""
            Role: Experienced Japan travel blogger.
            Task: Rewrite the text into an **engaging, first-person travel essay**.

            [Writing Guidelines]
            1. **Tone:** Conversational and warm using "I", "we", "you".
            2. **Sensory Details:** Describe sounds, smells, and feelings vividly.
            3. **Personal Touch:** Share specific moments and personal thoughts.
            4. **Pro Tips:** Include "💡 Pro Tip:" or "⚠️ Heads up:".
            5. **Structure:** KEEP headers (#, ##) and image links (![...](...)) exactly as is.
            6. **Conclusion:** End with "## 6. ✨ Conclusion:" section.

            [Original Content]:
            {original_content}
            """

        # AI 호출 (대기 시간 없음)
        response = model.generate_content(prompt)
        new_content = response.text.strip()
        
        # 마크다운 포맷팅 보정
        new_content = re.sub(r'([^\n])\n\*\s', r'\1\n\n* ', new_content)
        new_content = re.sub(r'([^\n])\n-\s', r'\1\n\n- ', new_content)

        # 메타데이터 업데이트
        post.content = new_content
        post['humanized'] = True 
        
        # 파일 저장
        with open(filepath, 'wb') as f:
            frontmatter.dump(post, f)
            
        # print(f"✅ Done: {os.path.basename(filepath)}")
        # time.sleep(4)  <-- 유료 API 사용 시 주석 처리 또는 삭제

    except Exception as e:
        print(f"❌ Error processing {os.path.basename(filepath)}: {e}")

def main():
    print(f"🚀 Starting Fast Humanization Process...")
    
    files = [f for f in os.listdir(CONTENT_DIR) if f.endswith('.md')]
    total = len(files)
    
    print(f"📊 Found {total} Markdown files.")
    
    processed_count = 0
    for i, filename in enumerate(files):
        filepath = os.path.join(CONTENT_DIR, filename)
        humanize_file(filepath)
        processed_count += 1
        
        # 진행 상황 표시 (너무 자주 출력하면 로그가 지저분하므로 10개마다 출력)
        if processed_count % 10 == 0:
            print(f"   Progress: {processed_count}/{total} files processed.")

    print("\n🎉 All files processed! Don't forget to rebuild data.")
    print("👉 Run: python script/build_data.py")

if __name__ == "__main__":
    main()