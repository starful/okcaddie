import os, csv, time, sys, re
import concurrent.futures
from datetime import datetime
from google import genai
from dotenv import load_dotenv

from topic_queue_csv import resolve as resolve_queue_csv

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================
load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

CSV_PATH = 'script/csv/courses.csv'
CONTENT_DIR = "app/content"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from course_content import normalize_course_markdown  # noqa: E402


def _courses_csv_path() -> str:
    return resolve_queue_csv("items", CSV_PATH)


os.makedirs(CONTENT_DIR, exist_ok=True)

# 생성할 코스 주제(Topic)의 개수 제한 (명령행 인자가 없을 경우 기본값)
DEFAULT_LIMIT = 30

LANG_FULL = {"en": "English", "ko": "Korean"}

# 모델이 본문 끝에 자기점검 메타텍스트(영문 보일러플레이트)를 붙이는 경우가 있음 → 저장 직전 제거
_SELFCHECK_RES = [
    re.compile(r"^\s*\*{0,2}\s*\(?\s*Total\s+character", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*\*{0,2}\s*\(?\s*Character\s+count\s+check", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*Markdown\s+formatting\s+with", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*YAML\s+frontmatter\s+is\s+correctly", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*The\s+tone\s+is\s+professional,?\s+technical", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*The\s+generated\s+(?:Korean|English)\s+content\s+is\s+~?\s*\d", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*\d+\.\s+\*\*(?:Character\s+Count|Tone|Language|YAML\s+Frontmatter)\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*```(?:markdown|yaml)\s*$", re.IGNORECASE | re.MULTILINE),
]

def _strip_selfcheck(text):
    earliest = len(text)
    for pat in _SELFCHECK_RES:
        m = pat.search(text)
        if m and m.start() < earliest:
            earliest = m.start()
    if earliest < len(text):
        return text[:earliest].rstrip() + "\n"
    return text

def _dedupe_h2(text):
    """첫 번째 ## 헤더가 두 번 등장하면 두 번째 직전까지만 보존."""
    lines = text.splitlines()
    first_h2 = None
    first_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("## "):
            first_h2 = line.strip()
            first_idx = i
            break
    if first_h2 is None:
        return text
    for j in range(first_idx + 1, len(lines)):
        if lines[j].strip() == first_h2:
            return "\n".join(lines[:j]).rstrip() + "\n"
    return text


def _safe(row, *keys):
    """CSV에 컬럼이 없거나 값이 비면 빈 문자열을 반환하는 안전 추출 함수."""
    for k in keys:
        v = (row.get(k) or "").strip() if isinstance(row, dict) else ""
        if v:
            return v
    return ""


def build_prompt(data):
    """SEO·신뢰도를 위한 새 프롬프트.
    - 라벨 제거 (title에 (en)/(ko) 절대 안 들어감)
    - 보일러플레이트(공허한 칭찬) 금지, 길이 2,500~4,000자
    - CSV에 추가 컬럼이 있으면 사실로 활용, 없으면 일반 범위 제시
    """
    lang = data['lang']
    lang_full = LANG_FULL.get(lang, "English")
    safe_name = data['safe_name']
    name = data['name']
    today = datetime.now().strftime('%Y-%m-%d')

    # 선택 가능한 정량 컬럼 (CSV에 있을 때만 모델이 사용)
    facts_lines = []
    for label, key in [
        ("Holes", "Holes"),
        ("Total Yardage", "Yardage"),
        ("Par", "Par"),
        ("Designer", "Designer"),
        ("Opened Year", "OpenedYear"),
        ("Green Fee Range (JPY)", "GreenFee"),
        ("Phone", "Phone"),
        ("Website", "Website"),
    ]:
        v = data.get(key) or ""
        if v:
            facts_lines.append(f"- {label}: {v}")
    known_facts_block = ("\n[KNOWN FACTS — TREAT AS GROUND TRUTH]\n" + "\n".join(facts_lines)) if facts_lines else ""

    summary_hint = (
        "Provide a concrete 1-sentence summary in Korean (<=140 chars) including at least one numeric or location-specific detail."
        if lang == "ko"
        else "Provide a concrete 1-sentence summary in English (<=155 chars) including at least one numeric or location-specific detail."
    )

    return f"""You are a senior Japan golf travel writer producing a course profile for OKCaddie.
Write in {lang_full}. Be specific and useful for trip planning. Avoid generic praise.

Course: {name}
Address: {data['address']}
Coordinates: {data['lat']}, {data['lng']}
Tags: {data['features']}{known_facts_block}

[GOAL]
- Total length: 2,500 to 4,000 characters (no padding, no filler).
- 2-3 sentences max per paragraph.
- Use H2 (##). Use at most 6 H2 sections.
- Do NOT use phrases like "world-class", "unforgettable", "must-visit", "every golfer's dream", "breath-taking".
- Only include numeric facts you are confident about. If unsure, give a typical range (e.g. "around 6,800-7,100 yards") rather than fabricating exact figures.
- Do NOT invent phone numbers, websites, or addresses beyond the address provided.

[SECTIONS — IN THIS ORDER, MAX 6]
1. ## Course Overview
   Holes, par, total yardage range, designer, opening year, fairway/green grass type, signature characteristics. Use [KNOWN FACTS] when present.
2. ## Layout & Strategy
   Pick 2-3 strategic holes by number. For each: tee-shot view, hidden hazards, recommended club, putting line.
3. ## Practical Info
   Green fee range (weekday vs weekend in JPY), reservation policy (member-only vs public), cart vs walking, dress code specifics, caddie option.
4. ## Access
   Nearest train station, drive time/distance from the closest major hub city, parking note.
5. ## Clubhouse Notes
   1 paragraph: locker room, bath/onsen, restaurant signature dish.
6. ## Tips
   1 paragraph of caddie-grade advice: best months, common mistakes, weather risk, peak season pricing.

[FORMATTING]
- Output raw Markdown. NO code fences. NO leading "```yaml".
- Start IMMEDIATELY with the YAML frontmatter below. Wrap ALL values in double quotes.

[YAML FRONTMATTER FORMAT — required exactly]
---
lang: "{lang}"
title: "{name}"
lat: "{data['lat']}"
lng: "{data['lng']}"
categories: "{data['features']}"
thumbnail: "/static/images/{safe_name}.jpg"
address: "{data['address']}"
date: "{today}"
booking: "/booking/{safe_name}_{lang}"
summary: "{summary_hint}"
---
"""


def generate_course_task(data):
    """실제 Gemini API를 호출하여 코스 리뷰를 생성하는 워커 함수"""
    safe_name = data['safe_name']
    lang = data['lang']
    filepath = os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md")

    prompt = build_prompt(data)

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        content = response.text.strip()

        # AI가 넣은 코드 블록 찌꺼기 제거
        content = re.sub(r'^```markdown\s*', '', content)
        content = re.sub(r'^```yaml\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        content = content.replace('## yaml', '').strip()

        # 안전망: 모델이 (en)/(ko) 라벨을 다시 붙였을 경우 제거
        content = re.sub(
            r'^(title:\s*"[^"]*?)\s*\(\s*(?:en|ko|EN|KO)\s*\)\s*"',
            r'\1"',
            content,
            count=1,
            flags=re.MULTILINE,
        )

        # 안전망: 자기점검 푸터·중복 본문 제거
        content = _strip_selfcheck(content)
        content = _dedupe_h2(content)
        content, _ = normalize_course_markdown(content)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return True, f"✅ Success: {safe_name}_{lang} ({len(content)} characters)"

    except Exception as e:
        return False, f"❌ Error: {safe_name}_{lang} -> {e}"


def process_courses(limit):
    """CSV를 읽어 생성 대상을 수집하고 병렬 처리를 실행"""
    csv_path = _courses_csv_path()
    if not os.path.exists(csv_path):
        print(f"❌ CSV 없음: {csv_path}")
        return 1

    tasks = []
    with open(csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        new_topic_count = 0

        for row in reader:
            name = row['Name'].strip()
            safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "").replace("&", "and").replace(".", "")

            if os.path.exists(os.path.join(CONTENT_DIR, f"{safe_name}_en.md")) and os.path.exists(
                os.path.join(CONTENT_DIR, f"{safe_name}_ko.md")
            ):
                continue

            base = {
                'safe_name': safe_name,
                'name': name,
                'lat': _safe(row, 'Lat'),
                'lng': _safe(row, 'Lng'),
                'address': _safe(row, 'Address'),
                'features': _safe(row, 'Features'),
                'booking': _safe(row, 'Booking'),
                'Holes': _safe(row, 'Holes'),
                'Yardage': _safe(row, 'Yardage'),
                'Par': _safe(row, 'Par'),
                'Designer': _safe(row, 'Designer'),
                'OpenedYear': _safe(row, 'OpenedYear', 'Opened'),
                'GreenFee': _safe(row, 'GreenFee', 'Fee'),
                'Phone': _safe(row, 'Phone'),
                'Website': _safe(row, 'Website', 'URL'),
            }
            row_tasks = []
            for lang in ['en', 'ko']:
                out_path = os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md")
                if not os.path.exists(out_path):
                    row_tasks.append({**base, 'lang': lang})
            if not row_tasks:
                continue
            if new_topic_count >= limit:
                break
            tasks.extend(row_tasks)
            new_topic_count += 1

    if not tasks:
        print("🙌 모든 코스 콘텐츠가 이미 최신 상태입니다.")
        return 0

    print(f"🔥 코스 리뷰 생성 시작 (주제: {new_topic_count}개, 파일: {len(tasks)}개)")
    print("🚀 동시 실행 쓰레드: 10")

    success_count = 0
    failure_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(generate_course_task, t) for t in tasks]
        for future in concurrent.futures.as_completed(futures):
            ok, message = future.result()
            if message:
                print(message)
            if ok:
                success_count += 1
            else:
                failure_count += 1

    if failure_count:
        print(f"⚠️  생성 실패: {failure_count}개 파일")
        return 1
    print(f"✅ 생성 완료: {success_count}개 파일")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            run_limit = int(sys.argv[1])
        except ValueError:
            run_limit = DEFAULT_LIMIT
    else:
        run_limit = DEFAULT_LIMIT

    start_time = time.time()
    exit_code = process_courses(limit=run_limit)
    print(f"\n✨ 모든 작업 완료! (소요 시간: {time.time() - start_time:.1f}초)")
    raise SystemExit(exit_code)
