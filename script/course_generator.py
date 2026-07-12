import os, csv, time, sys, re
import concurrent.futures
from datetime import datetime
from google import genai
from dotenv import load_dotenv
import frontmatter

from topic_queue_csv import resolve as resolve_queue_csv


def _emit_pipeline_result(**kwargs):
    try:
        from generation_result import emit_generation_result

        emit_generation_result(**kwargs)
    except ImportError:
        pass

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
sys.path.insert(0, SCRIPT_DIR)

from content_quality import (  # noqa: E402
    is_non_golf_course_slug,
    strip_code_fences,
    validate_course_body,
)
from course_content import normalize_course_markdown  # noqa: E402
from course_prompts import MIN_BODY_CHARS, build_course_prompt  # noqa: E402
from text_utils import strip_llm_selfcheck  # noqa: E402


def _courses_csv_path() -> str:
    return resolve_queue_csv("items", CSV_PATH)


os.makedirs(CONTENT_DIR, exist_ok=True)

DEFAULT_LIMIT = 30


def _strip_selfcheck(text):
    trimmed = strip_llm_selfcheck(text)
    if trimmed != text:
        return trimmed.rstrip() + "\n"
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


def clean_generated_markdown(content: str) -> str:
    content = strip_code_fences(content)
    content = re.sub(
        r'^(title:\s*"[^"]*?)\s*\(\s*(?:en|ko|EN|KO)\s*\)\s*"',
        r'\1"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    content = _strip_selfcheck(content)
    content = _dedupe_h2(content)
    content, _ = normalize_course_markdown(content)
    return content


def build_prompt(data):
    """6k+ medium-depth course prompt (shared with expand_short_courses)."""
    return build_course_prompt(data, today=datetime.now().strftime('%Y-%m-%d'))


def _safe(row, *keys):
    """CSV에 컬럼이 없거나 값이 비면 빈 문자열을 반환하는 안전 추출 함수."""
    for k in keys:
        v = (row.get(k) or "").strip() if isinstance(row, dict) else ""
        if v:
            return v
    return ""


def generate_course_task(data):
    """실제 Gemini API를 호출하여 코스 리뷰를 생성하는 워커 함수"""
    safe_name = data['safe_name']
    lang = data['lang']
    filepath = os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md")
    if is_non_golf_course_slug(safe_name, data.get("name", "")):
        return False, f"⏭️  Skip non-golf slug: {safe_name}_{lang}"

    prompt = build_prompt(data)

    try:
        content = None
        body_len = 0
        quality_errors: list[str] = []
        for attempt in range(3):
            extra = ""
            if attempt == 1 and body_len and body_len < MIN_BODY_CHARS:
                extra = (
                    f"\n\nIMPORTANT: Previous draft body was only {body_len} chars. "
                    f"Write at least {MIN_BODY_CHARS} characters of useful trip-planning detail "
                    f"(not filler praise)."
                )
            elif attempt >= 1 and quality_errors:
                extra = (
                    "\n\nIMPORTANT: Previous draft failed quality checks: "
                    + "; ".join(quality_errors)
                    + ". Fix those issues. Keep the practical Quick Facts → Booking → Access structure. "
                    "Do not use masterclass / elite-caddy voice."
                )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt + extra,
            )
            content = clean_generated_markdown(response.text.strip())
            post = frontmatter.loads(content)
            body = post.content.strip()
            body_len = len(body)
            quality_errors = validate_course_body(body)
            if body_len >= MIN_BODY_CHARS and not quality_errors:
                break

        if quality_errors:
            return (
                False,
                f"❌ Quality fail: {safe_name}_{lang} -> {'; '.join(quality_errors)}",
            )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        short_flag = " ⚠️ under min" if body_len < MIN_BODY_CHARS else ""
        return True, f"✅ Success: {safe_name}_{lang} (body {body_len:,} chars{short_flag})"

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

            if is_non_golf_course_slug(safe_name, name):
                print(f"⏭️  Skip non-golf CSV row: {name} ({safe_name})")
                continue

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
        _emit_pipeline_result(step="items", topics=0, generated=0)
        return 0

    print(f"🔥 코스 리뷰 생성 시작 (주제: {new_topic_count}개, 파일: {len(tasks)}개, min body {MIN_BODY_CHARS} chars)")
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
        _emit_pipeline_result(
            step="items",
            topics=new_topic_count,
            generated=success_count,
            failed=failure_count,
            ok=False,
        )
        return 1
    print(f"✅ 생성 완료: {success_count}개 파일")
    _emit_pipeline_result(step="items", topics=new_topic_count, generated=success_count)
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
