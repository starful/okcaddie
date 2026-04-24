import os
import csv
import re
import frontmatter

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COURSE_CSV = os.path.join(BASE_DIR, "script", "csv", "courses.csv")
GUIDE_CSV = os.path.join(BASE_DIR, "script", "csv", "guides.csv")
CONTENT_DIR = os.path.join(BASE_DIR, "app", "content")

def clean_title(title):
    """제목에 이미 들어간 마크다운 링크를 제거하여 순수 텍스트로 복구합니다."""
    # '[이름](/url)' 형태를 찾아 '이름'만 남깁니다.
    return re.sub(r'\[(.*?)\]\(.*?\)', r'\1', title)

def load_keywords():
    """CSV에서 링크 대상 키워드를 수집합니다."""
    keywords = {'ko': [], 'en': []}
    
    # 1. 코스 이름 수집
    if os.path.exists(COURSE_CSV):
        with open(COURSE_CSV, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row['Name'].strip()
                safe_id = name.lower().replace(" ", "_").replace("'", "").replace(",", "").replace("&", "and").replace(".", "")
                keywords['en'].append({'key': name, 'url': f"/course/{safe_id}_en"})
                keywords['ko'].append({'key': name, 'url': f"/course/{safe_id}_ko"})

    # 2. 가이드 주제 수집
    if os.path.exists(GUIDE_CSV):
        with open(GUIDE_CSV, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                gid = row['id'].strip()
                k_topic = row['topic_ko'].split('(')[0].split(':')[0].strip()
                e_topic = row['topic_en'].split(':')[0].strip()
                keywords['en'].append({'key': e_topic, 'url': f"/guide/{gid}_en"})
                keywords['ko'].append({'key': k_topic, 'url': f"/guide/{gid}_ko"})

    # 긴 단어부터 정렬
    keywords['en'].sort(key=lambda x: len(x['key']), reverse=True)
    keywords['ko'].sort(key=lambda x: len(x['key']), reverse=True)
    return keywords

def apply_internal_links():
    master_keywords = load_keywords()
    all_files = []
    for root, dirs, files in os.walk(CONTENT_DIR):
        for file in files:
            if file.endswith(".md"):
                all_files.append(os.path.join(root, file))

    print(f"🔗 내부 링크 최적화 및 제목 복구 시작 (파일 {len(all_files)}개)...")
    total_links = 0
    restored_titles = 0

    for file_path in all_files:
        filename = os.path.basename(file_path)
        lang = 'ko' if filename.endswith('_ko.md') else 'en'
        
        try:
            # 1. 파일 읽기 (Frontmatter 라이브러리 사용)
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            # 2. [복구 로직] 제목에 링크가 있다면 제거
            original_title = post.get('title', '')
            cleaned_title = clean_title(original_title)
            if original_title != cleaned_title:
                post['title'] = cleaned_title
                restored_titles += 1

            # 3. [본문 전용] 링크 작업
            original_body = post.content
            updated_body = original_body
            
            for item in master_keywords[lang]:
                key = item['key']
                url = item['url']

                if len(key) < 2: continue

                # 본문에 단어가 있고, 링크가 안 걸렸으며, 현재 페이지가 아닐 때만
                if key in updated_body and url not in updated_body and url.split('/')[-1] not in filename:
                    # 정규식으로 첫 번째 발견된 단어만 교체
                    pattern = re.compile(re.escape(key))
                    if pattern.search(updated_body):
                        updated_body = pattern.sub(f"[{key}]({url})", updated_body, count=1)
                        total_links += 1

            # 4. 변경 사항이 있으면 저장
            if (updated_body != original_body) or (original_title != cleaned_title):
                post.content = updated_body
                with open(file_path, 'wb') as f:
                    frontmatter.dump(post, f)
                    
        except Exception as e:
            print(f"❌ Error in {filename}: {e}")

    print(f"\n✨ 작업 완료!")
    print(f"   - 복구된 제목: {restored_titles}개")
    print(f"   - 삽입된 본문 링크: {total_links}개")

if __name__ == "__main__":
    apply_internal_links()