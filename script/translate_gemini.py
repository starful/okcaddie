import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(message)s')

# 1. 환경 변수 로드
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logging.error("❌ .env 파일에서 GEMINI_API_KEY를 찾을 수 없습니다.")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

# 2. 모델 설정 (요청하신 gemini-pro-latest 적용)
# 참고: Google AI Studio 최신 모델 정책에 따라 'gemini-1.5-pro'가
# 현재 시점의 최신 Pro 모델로 매핑되는 경우가 많습니다.
MODEL_NAME = "gemini-pro-latest" 
model = genai.GenerativeModel(MODEL_NAME)

# 3. 작업 폴더 설정
TARGET_FOLDER = "app/content/"  # md 파일이 있는 폴더 경로

def translate_markdown(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if not content.strip():
            logging.warning(f"⚠️  빈 파일 스킵: {file_path}")
            return

        # 시스템 프롬프트 (마크다운 구조 유지 및 전문 번역 요청)
        prompt = f"""
        You are a professional technical translator.
        Translate the following Markdown content from Korean to English.
        
        CRITICAL RULES:
        1. Keep the Markdown syntax/structure exactly as it is (Headers, Lists, Tables, Code blocks).
        2. Do NOT translate content inside code blocks (``` ... ```).
        3. Do NOT translate YAML Frontmatter keys (metadata at the top), only translate the values if they are text.
        4. Output ONLY the translated content without any conversational filler.

        ---
        [CONTENT START]
        {content}
        [CONTENT END]
        """

        # 유료 API이므로 호출
        response = model.generate_content(prompt)
        translated_text = response.text

        # 저장 (파일명_en.md)
        new_file_path = file_path.replace(".md", "_en.md")
        with open(new_file_path, 'w', encoding='utf-8') as f:
            f.write(translated_text)
            
        logging.info(f"✅ 번역 완료: {os.path.basename(new_file_path)}")

    except Exception as e:
        logging.error(f"❌ 오류 발생 ({os.path.basename(file_path)}): {str(e)}")

def main():
    if not os.path.exists(TARGET_FOLDER):
        logging.error(f"❌ 폴더를 찾을 수 없습니다: {TARGET_FOLDER}")
        return

    # _en.md 파일은 제외하고 원본만 선택
    files = [f for f in os.listdir(TARGET_FOLDER) if f.endswith(".md") and "_en.md" not in f]
    total = len(files)
    
    logging.info(f"🚀 총 {total}개의 파일 번역을 시작합니다. (모델: {MODEL_NAME})")

    for index, filename in enumerate(files):
        full_path = os.path.join(TARGET_FOLDER, filename)
        translate_markdown(full_path)
        
        # 진행 상황 표시
        if (index + 1) % 10 == 0:
            logging.info(f"... {index + 1}/{total} 처리 중 ...")

    logging.info("\n🎉 모든 작업이 완료되었습니다!")

if __name__ == "__main__":
    main()