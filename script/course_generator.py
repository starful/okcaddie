import os, csv, time, sys, re
import concurrent.futures
from datetime import datetime
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

def _claude_md(prompt: str) -> str:
    """MD text via Claude CLI subscription (not Claude API)."""
    import sys
    from pathlib import Path
    _shared = Path(__file__).resolve().parents[2] / "_shared"
    if str(_shared) not in sys.path:
        sys.path.insert(0, str(_shared))
    from site_llm import generate_md_text
    return generate_md_text(prompt)

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
from course_prompts import MIN_BODY_CHARS, build_course_prompt, min_body_chars  # noqa: E402
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
        r'^(title:\s*"[^"]*?)\s*\(\s*(?:en|ko|ja|EN|KO|JA)\s*\)\s*"',
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
    """실제 Claude API를 호출하여 코스 리뷰를 생성하는 워커 함수"""
    safe_name = data['safe_name']
    lang = data['lang']
    filepath = os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md")
    has_sibling = any(
        os.path.isfile(os.path.join(CONTENT_DIR, f"{safe_name}_{sib}.md"))
        for sib in ("en", "ko", "ja")
        if sib != lang
    )
    if not has_sibling and is_non_golf_course_slug(
        safe_name,
        data.get("name", ""),
        features=data.get("features", ""),
        address=data.get("address", ""),
    ):
        return False, f"⏭️  Skip off-theme slug: {safe_name}_{lang}"

    prompt = build_prompt(data)
    min_chars = min_body_chars(lang)

    try:
        content = None
        body_len = 0
        quality_errors: list[str] = []
        for attempt in range(3):
            if attempt == 0:
                call_prompt = prompt
            elif content:
                call_prompt = (
                    f"{prompt}\n\nIMPORTANT: Expand the DRAFT below to at least "
                    f"{min_chars} characters in the Markdown body (exclude YAML). "
                    "Keep every ## section; add concrete access times, fee ranges, "
                    "dress tips, and booking steps. Do not shorten. Output the full "
                    "document starting with ---.\n\nDRAFT:\n"
                    f"{content}"
                )
                if quality_errors:
                    call_prompt += (
                        "\n\nAlso fix: " + "; ".join(quality_errors)
                        + ". For Japanese use `## クイックファクト`, `## コース概要`, "
                        "`## グリーンフィー・予約`, `## アクセス・交通`."
                    )
            else:
                call_prompt = (
                    prompt
                    + f"\n\nIMPORTANT: Write at least {min_chars} characters. "
                    "For Japanese start with `## クイックファクト`."
                )
            response_text = _claude_md(call_prompt)
            content = clean_generated_markdown(response_text.strip())
            post = frontmatter.loads(content)
            body = post.content.strip()
            body_len = len(body)
            quality_errors = validate_course_body(body)
            if body_len >= min_chars and not quality_errors:
                break
            print(
                f"↻ retry {attempt + 1}/3 {safe_name}_{lang}: "
                f"body={body_len} errs={quality_errors or '-'}",
                flush=True,
            )

        if quality_errors:
            return (
                False,
                f"❌ Quality fail: {safe_name}_{lang} -> {'; '.join(quality_errors)}",
            )
        if body_len < min_chars:
            return (
                False,
                f"❌ Quality fail: {safe_name}_{lang} -> too_short:{body_len}<{min_chars}",
            )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return True, f"✅ Success: {safe_name}_{lang} (body {body_len:,} chars)"

    except Exception as e:
        return False, f"❌ Error: {safe_name}_{lang} -> {e}"


def _want_fill_lang() -> str:
    v = (os.environ.get("FILL_LANG") or "").strip().lower()
    if v and v not in ("en", "ko", "ja"):
        raise ValueError(f"FILL_LANG invalid: {v} (use en|ko|ja)")
    return v


def _course_task_from_sibling(safe_name: str, target_lang: str) -> dict | None:
    """Build a generation task from an existing EN/KO sibling markdown."""
    sibling_path = None
    for sib in ("en", "ko", "ja"):
        if sib == target_lang:
            continue
        path = os.path.join(CONTENT_DIR, f"{safe_name}_{sib}.md")
        if os.path.isfile(path):
            sibling_path = path
            break
    if not sibling_path:
        return None
    try:
        post = frontmatter.load(sibling_path)
    except Exception:
        return None
    meta = post.metadata if isinstance(post.metadata, dict) else {}
    cats = meta.get("categories") or ""
    if isinstance(cats, list):
        cats = ", ".join(str(c) for c in cats)
    title = str(meta.get("title") or safe_name).strip()
    # Drop language suffix noise from titles when present
    name = re.sub(r"\s*[|/].*$", "", title).strip() or safe_name.replace("_", " ").title()
    return {
        "safe_name": safe_name,
        "name": name,
        "lat": str(meta.get("lat") or ""),
        "lng": str(meta.get("lng") or ""),
        "address": str(meta.get("address") or ""),
        "features": str(cats),
        "booking": str(meta.get("booking") or ""),
        "Holes": "",
        "Yardage": "",
        "Par": "",
        "Designer": "",
        "OpenedYear": "",
        "GreenFee": "",
        "Phone": "",
        "Website": "",
        "lang": target_lang,
    }


def _fill_lang_course_tasks(limit: int, fill_lang: str) -> list[dict]:
    """Queue missing target-lang files from existing sibling MD (not only CSV queue)."""
    stems: set[str] = set()
    for name in os.listdir(CONTENT_DIR):
        if name.endswith("_en.md"):
            stems.add(name[: -len("_en.md")])
        elif name.endswith("_ko.md"):
            stems.add(name[: -len("_ko.md")])
        elif name.endswith("_ja.md"):
            stems.add(name[: -len("_ja.md")])
    tasks: list[dict] = []
    for safe_name in sorted(stems):
        if len(tasks) >= limit:
            break
        target = os.path.join(CONTENT_DIR, f"{safe_name}_{fill_lang}.md")
        if os.path.isfile(target):
            continue
        task = _course_task_from_sibling(safe_name, fill_lang)
        if task:
            tasks.append(task)
    return tasks


def process_courses(limit):
    """CSV를 읽어 생성 대상을 수집하고 병렬 처리를 실행"""
    try:
        fill_lang = _want_fill_lang()
    except ValueError as exc:
        print(f"❌ {exc}", flush=True)
        return 1

    fill_half = os.environ.get("FILL_HALF", "").strip().lower() in ("1", "true", "yes")
    if fill_lang and fill_half:
        print("⚠️  FILL_LANG set — ignoring FILL_HALF", flush=True)
        fill_half = False

    tasks: list[dict] = []
    half_skipped = 0
    new_topic_count = 0

    if fill_lang:
        tasks = _fill_lang_course_tasks(limit, fill_lang)
        new_topic_count = len(tasks)
    else:
        csv_path = _courses_csv_path()
        if not os.path.exists(csv_path):
            print(f"❌ CSV 없음: {csv_path}", flush=True)
            return 1

        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row in reader:
                name = row['Name'].strip()
                safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "").replace("&", "and").replace(".", "")

                if is_non_golf_course_slug(
                    safe_name,
                    name,
                    features=_safe(row, "Features"),
                    address=_safe(row, "Address"),
                ):
                    print(f"⏭️  Skip off-theme CSV row: {name} ({safe_name})", flush=True)
                    continue

                locales = ("en", "ko", "ja")
                exists = {
                    lang: os.path.exists(os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md"))
                    for lang in locales
                }
                if all(exists.values()):
                    continue

                if fill_half:
                    if not any(exists.values()):
                        continue
                elif any(exists.values()):
                    half_skipped += 1
                    continue
                if new_topic_count >= limit:
                    break

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
                langs = list(locales)
                if fill_half:
                    langs = [lang for lang in locales if not exists[lang]]
                for lang in langs:
                    tasks.append({**base, 'lang': lang})
                new_topic_count += 1

    if half_skipped:
        print(f"⏭️  반쪽(en/ko/ja 일부만) {half_skipped}건 — 신규 트리플 우선으로 스킵", flush=True)

    if not tasks:
        if fill_lang:
            msg = f"🙌 채울 {fill_lang} 코스가 없습니다."
        elif fill_half:
            msg = "🙌 채울 반쪽 코스가 없습니다."
        else:
            msg = "🙌 모든 코스 콘텐츠가 이미 최신 상태입니다."
        print(msg, flush=True)
        _emit_pipeline_result(step="items", topics=0, generated=0, skipped=half_skipped)
        return 0

    if fill_lang:
        print(f"ℹ️  FILL_LANG={fill_lang}: {new_topic_count}주제 · {len(tasks)}파일", flush=True)
    elif fill_half:
        print(f"ℹ️  반쪽 채우기: {new_topic_count}주제 · {len(tasks)}파일", flush=True)
    print(f"🔥 코스 리뷰 생성 시작 (신규 트리플: {new_topic_count}개, 파일: {len(tasks)}개, min body {MIN_BODY_CHARS} chars)", flush=True)
    print("🚀 동시 실행 쓰레드: 10", flush=True)

    success_count = 0
    failure_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(generate_course_task, t) for t in tasks]
        for future in concurrent.futures.as_completed(futures):
            ok, message = future.result()
            if message:
                print(message, flush=True)
            if ok:
                success_count += 1
            else:
                failure_count += 1

    if failure_count:
        print(f"⚠️  생성 실패: {failure_count}개 파일", flush=True)
        _emit_pipeline_result(
            step="items",
            topics=new_topic_count,
            generated=success_count,
            failed=failure_count,
            skipped=half_skipped,
            ok=False,
        )
        return 1
    print(f"✅ 생성 완료: {success_count}개 파일", flush=True)
    _emit_pipeline_result(
        step="items",
        topics=new_topic_count,
        generated=success_count,
        skipped=half_skipped,
    )
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
    print(f"\n✨ 모든 작업 완료! (소요 시간: {time.time() - start_time:.1f}초)", flush=True)
    raise SystemExit(exit_code)
