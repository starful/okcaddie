import os
import csv
import re
import frontmatter

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COURSE_CSV = os.path.join(BASE_DIR, "script", "csv", "courses.csv")
CONTENT_DIR = os.path.join(BASE_DIR, "app", "content")

def generate_ko_name(en_name):
    """영문 이름을 기반으로 한글 핵심 키워드 추측 (헤리스틱 매핑)"""
    name = en_name.split(' ')[0] # 첫 단어 추출 (예: 'Miyazaki', 'Hirono')
    # 많이 쓰이는 이름들에 대한 한글 변환 규칙
    mapping = {
        'Hirono': '히로노', 'Kawana': '가와나', 'Phoenix': '피닉스', 'Naruo': '나루오',
        'Kasumigaseki': '가스미가세키', 'Taiheiyo': '태평양', 'Ishioka': '이시오카',
        'Accordia': '아코디아', 'Fujizakura': '후지자쿠라', 'Karuizawa': '가루이자와',
        'Kanucha': '카누차', 'Oarai': '오아라이', 'Katsura': '계수', 'Sapporo': '삿포로',
        'Otaru': '오타루', 'Nikko': '닛코', 'Hakone': '하코네', 'Ibusuki': '이부스키',
        'Kochi': '고치', 'Keya': '케야', 'Eniwa': '에니와', 'Windsor': '윈저',
        'Natsudomari': '나츠도마리', 'Jun': '준 클래식', 'Nishinasuno': '니시나스노',
        'Nagano': '나가노', 'Musashi': '무사시', 'Sayama': '사야마', 'Chiba': '치바',
        'Narita': '나리타', 'Caledonian': '캘러도니안', 'Camellia': '카멜리아',
        'Eagle': '이글 포인트', 'Ibaraki': '이바라키', 'Shishido': '시시도 힐스',
        'Fuji': '후지', 'Izuo': '이즈오히토', 'Katsuragi': '가쓰라기', 'Seta': '세타',
        'Golden': '골든 밸리', 'Aso': '아소', 'Southern': '서던 링크스',
        'Ryukyu': '류큐', 'Koganei': '고가네이', 'Yokohama': '요코하마',
        'Lakewood': '레이크우드', 'JFE': 'JFE 세토나이카이', 'Kinojo': '키노조',
        'Sodegaura': '소데가우라', 'Toba': '도바', 'Mie': '미에', 'Ehime': '에히메',
        'Wakayama': '와카야마', 'Kishu': '기슈', 'Takachiho': '다카치호',
        'Oita': '오이타', 'Saga': '사가', 'Shizukuishi': '시즈쿠이시'
    }
    return mapping.get(name, name)

def load_keywords():
    """CSV에서 모든 언어별 링크 타겟 수집"""
    keywords = {'ko': [], 'en': []}
    if not os.path.exists(COURSE_CSV): return keywords

    with open(COURSE_CSV, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            en_name = row['Name'].strip()
            safe_id = en_name.lower().replace(" ", "_").replace("'", "").replace(",", "").replace("&", "and").replace(".", "")
            
            # 1. 영어 키워드 추가
            keywords['en'].append({'key': en_name, 'url': f"/course/{safe_id}_en"})
            
            # 2. 한국어 키워드 추가 (풀네임 + 핵심단어)
            ko_core = generate_ko_name(en_name)
            # '아코디아 골프' 같은 핵심 단어로 본문에서 찾음
            keywords['ko'].append({'key': ko_core, 'url': f"/course/{safe_id}_ko"})
            # 본문에 영문 이름이 섞여 있을 경우를 대비해 한국어 문서에도 영문 키워드 추가
            keywords['ko'].append({'key': en_name, 'url': f"/course/{safe_id}_ko"})

    # 긴 단어 우선순위 정렬
    keywords['en'].sort(key=lambda x: len(x['key']), reverse=True)
    keywords['ko'].sort(key=lambda x: len(x['key']), reverse=True)
    return keywords

def apply_internal_links():
    master_keywords = load_keywords()
    all_files = []
    for root, dirs, files in os.walk(CONTENT_DIR):
        for file in files:
            if file.endswith(".md"): all_files.append(os.path.join(root, file))

    print(f"🔗 링크 삽입 시작 (파일 {len(all_files)}개)...")
    total_count = 0

    for file_path in all_files:
        filename = os.path.basename(file_path)
        lang = 'ko' if filename.endswith('_ko.md') else 'en'
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            original_body = post.content
            updated_body = original_body
            
            # 현재 페이지 언어에 맞는 키워드 목록만 사용
            for item in master_keywords[lang]:
                key = item['key']
                url = item['url']

                # 자기 자신 링크 방지 및 이미 링크된 경우 제외
                if key in updated_body and url not in updated_body and url.split('/')[-1] not in filename:
                    # 마크다운 문법 내부(이미지 alt 등)에 링크가 걸리지 않도록 간단한 체크
                    pattern = re.compile(re.escape(key))
                    if pattern.search(updated_body):
                        # 본문에서 해당 단어를 처음 만날 때만 링크로 교체
                        updated_body = pattern.sub(f"[{key}]({url})", updated_body, count=1)
                        total_count += 1

            if updated_body != original_body:
                post.content = updated_body
                with open(file_path, 'wb') as f:
                    frontmatter.dump(post, f)
                    
        except Exception as e:
            print(f"❌ Error in {filename}: {e}")

    print(f"✨ 완료! 총 {total_count}개의 링크가 생성되었습니다.")

if __name__ == "__main__":
    apply_internal_links()