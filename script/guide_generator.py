import os, csv, time, sys
import concurrent.futures
from google import genai
from dotenv import load_dotenv

# 설정 로드
load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

GUIDE_CSV = 'script/csv/guides.csv'
CONTENT_DIR = "app/content/guides"
os.makedirs(CONTENT_DIR, exist_ok=True)

def task_worker(topic_id, topic_name, lang, keywords):
    """실제 Gemini API를 호출하여 파일을 생성하는 워커 함수"""
    filepath = os.path.join(CONTENT_DIR, f"{topic_id}_{lang}.md")
    
    if os.path.exists(filepath):
        return None # 이미 있으면 스킵

    prompt = f"""
    Write a professional, DEEP-DIVE SEO guide for Japanese Golf.
    Topic: {topic_name}
    Keywords: {keywords}
    Language: {lang}
    
    [IMPORTANT: OUTPUT FORMAT]
    1. Start IMMEDIATELY with '---'. Do NOT write '```yaml' or the word 'yaml'.
    2. Minimum 4000 characters of rich, useful content.
    3. Use the following YAML frontmatter:
    ---
    lang: "{lang}"
    title: "{topic_name}"
    summary: "Provide a 3-sentence summary in {lang}"
    date: "2026-04-15"
    ---
    (Followed by Markdown content)
    """

    try:
        # Gemini 2.0 Flash는 유료 버전에서 매우 빠릅니다.
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        content = response.text.replace("```markdown", "").replace("```", "").replace("## yaml", "").strip()
        
        with open(filepath, 'w', encoding='utf-8') as mf:
            mf.write(content)
        return f"✅ Success: {topic_id}_{lang}"
    except Exception as e:
        return f"❌ Error: {topic_id}_{lang} -> {e}"

def generate_guides_parallel(limit=5):
    tasks = []
    
    # 1. 생성할 작업 리스트 수집
    with open(GUIDE_CSV, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        new_topics_count = 0
        for row in reader:
            if new_topics_count >= limit: break
            
            topic_id = row['id'].strip()
            # 영문/국문 파일이 하나라도 없으면 작업 추가
            if not (os.path.exists(os.path.join(CONTENT_DIR, f"{topic_id}_en.md")) and 
                    os.path.exists(os.path.join(CONTENT_DIR, f"{topic_id}_ko.md"))):
                
                for lang in ['en', 'ko']:
                    tasks.append({
                        'topic_id': topic_id,
                        'topic_name': row[f'topic_{lang}'],
                        'lang': lang,
                        'keywords': row['keywords']
                    })
                new_topics_count += 1

    print(f"🔥 병렬 처리 시작: 총 {len(tasks)}개 파일 생성 시도 (동시 작업 쓰레드: 10)")

    # 2. 멀티쓰레딩 실행 (max_workers로 동시 실행 수 조절)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # map을 사용하여 함수와 인자 리스트 연결
        futures = [executor.submit(task_worker, t['topic_id'], t['topic_name'], t['lang'], t['keywords']) for t in tasks]
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                print(result)

if __name__ == "__main__":
    # 실행 시 개수 지정 가능 (예: python script/guide_generator.py 20)
    if len(sys.argv) > 1:
        run_limit = int(sys.argv[1])
    else:
        run_limit = 5 # 기본값 5개 주제(파일 10개)

    start_time = time.time()
    generate_guides_parallel(limit=run_limit)
    end_time = time.time()
    
    print(f"\n⏱️ 소요 시간: {end_time - start_time:.2f}초")