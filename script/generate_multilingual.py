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

# .env 파일 로드
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("❌ Error: GEMINI_API_KEY not found in .env file.")
    exit(1)

genai.configure(api_key=API_KEY)
# 유료 API라면 속도가 가장 빠른 모델 사용 (Flash)
model = genai.GenerativeModel("gemini-flash-latest")

# 카테고리 매핑
CAT_MAP_KO = { "Wealth": "재물", "Love": "사랑", "Health": "건강", "Success": "성공", "Safety": "안전", "History": "역사" }
CAT_MAP_JA = { "Wealth": "金運", "Love": "縁結び", "Health": "健康", "Success": "合格・必勝", "Safety": "安全", "History": "歴史" }

def generate_version(en_post, target_lang, output_path):
    if os.path.exists(output_path):
        return

    print(f"⚡ Generating [{target_lang.upper()}]: {os.path.basename(output_path)}")

    original_content = en_post.content
    original_title = en_post.get('title', '')

    if target_lang == 'ko':
        prompt = f"""
        Role: 10년 차 일본 여행 전문 파워블로거.
        Task: 아래 영어 신사 가이드를 바탕으로 **한국인을 위한 생생한 1인칭 여행기(블로그 포스팅)**를 새로 작성해주세요.
        
        [작성 지침]
        1. **말투:** "~해요", "~했답니다" 같은 친근하고 부드러운 구어체 사용. (딱딱한 번역투 절대 금지)
        2. **내용 확장:** 원문 내용을 기반으로 하되, 역사적 배경, 신화, 주변 분위기 묘사를 풍부하게 추가하여 분량을 늘릴 것.
        3. **구성:** 
           - **도입부:** 호기심을 자극하는 인사말과 방문 이유.
           - **본문:** 1인칭 시점의 생생한 탐방기 (시각, 청각, 후각 묘사 포함).
           - **꿀팁:** "💡 솔직한 팁:", "⚠️ 주의사항:" 섹션 포함.
           - **결론:** "## 6. ✨ Conclusion:" 섹션으로 마무리하며 따뜻한 추천사 작성.
        4. **형식:** 마크다운 헤더(#, ##)와 이미지 링크(![...](...)) 구조는 유지. 리스트 항목 앞뒤엔 빈 줄 추가.

        [Original Title]: {original_title}
        [Original Content]:
        {original_content}
        """
        cat_map = CAT_MAP_KO

    elif target_lang == 'ja':
        prompt = f"""
        Role: 日本の神社仏閣巡りが趣味の人気旅ブロガー。
        Task: 以下の英語ガイドを元に、**日本人読者に向けた臨場感あふれる一人称の旅行記（ブログ記事）**を作成してください。

        [執筆ガイドライン]
        1. **文体:** 「〜です」「〜ます」調で、親しみやすく語りかけるように。（翻訳調はNG）
        2. **内容拡充:** 原文をベースにしつつ、ご由緒、神話、境内の空気感を大幅に加筆して読み応えを持たせること。
        3. **構成:**
           - **導入:** 読者を引き込む挨拶と、その神社を訪れたきっかけ。
           - **本文:** 五感を使った臨場感ある参拝レポート。
           - **アドバイス:** 「💡 ここだけの話：」「⚠️ 注意点：」などの実用的なヒント。
           - **結び:** 「## 6. ✨ Conclusion:」セクションで締めくくり、再訪したくなるようなメッセージ。
        4. **形式:** Markdownヘッダー(#, ##)や画像リンク(![...](...))は維持。リストの前後には空行を入れる。

        [Original Title]: {original_title}
        [Original Content]:
        {original_content}
        """
        cat_map = CAT_MAP_JA

    try:
        # AI 생성 요청 (유료 API는 여기서 대기 시간 없음)
        response = model.generate_content(prompt)
        new_content = response.text.strip()

        new_content = re.sub(r'([^\n])\n\*\s', r'\1\n\n* ', new_content)
        new_content = re.sub(r'([^\n])\n-\s', r'\1\n\n- ', new_content)

        new_post = frontmatter.Post(new_content)
        new_post.metadata = en_post.metadata.copy()
        new_post['lang'] = target_lang
        
        title_match = re.search(r'^#\s+(.+)$', new_content, re.MULTILINE)
        if title_match:
            new_post['title'] = title_match.group(1).strip()

        new_post['categories'] = [cat_map.get(c, c) for c in en_post.get('categories', [])]
        
        tag_prompt = f"Generate 10 relevant SEO tags in {target_lang} for '{new_post['title']}', comma separated."
        tag_resp = model.generate_content(tag_prompt)
        new_post['tags'] = [t.strip() for t in tag_resp.text.split(',')]

        summary_prompt = f"Summarize in {target_lang} for SEO (120 chars):\n{new_content[:500]}"
        summary_resp = model.generate_content(summary_prompt)
        new_post['excerpt'] = summary_resp.text.strip()
        new_post['humanized'] = True

        with open(output_path, 'wb') as f:
            frontmatter.dump(new_post, f)
        
        # [속도 최적화] 대기 시간 제거 (time.sleep 삭제)
        # time.sleep(5) 

    except Exception as e:
        print(f"❌ Error generating {target_lang} version: {e}")

def main():
    print(f"🚀 Starting Fast Multilingual Generation...")
    
    files = [f for f in os.listdir(CONTENT_DIR) if f.endswith('.md') and not ('_ko.md' in f or '_ja.md' in f)]
    total = len(files)
    
    print(f"📊 Found {total} English source files.")

    for i, filename in enumerate(files):
        en_path = os.path.join(CONTENT_DIR, filename)
        
        try:
            en_post = frontmatter.load(en_path)
        except Exception as e:
            print(f"⚠️ Failed to load {filename}: {e}")
            continue

        # 순차 실행 (유료 API는 매우 빠름)
        ko_filename = filename.replace('.md', '_ko.md')
        ko_path = os.path.join(CONTENT_DIR, ko_filename)
        generate_version(en_post, 'ko', ko_path)

        ja_filename = filename.replace('.md', '_ja.md')
        ja_path = os.path.join(CONTENT_DIR, ja_filename)
        generate_version(en_post, 'ja', ja_path)
        
        # 진행 상황 표시
        if (i+1) % 5 == 0:
            print(f"   Progress: {i+1}/{total} files processed.")

    print("\n🎉 All multilingual versions generated!")

if __name__ == "__main__":
    main()