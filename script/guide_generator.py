import os, csv, time, sys
import concurrent.futures
from datetime import datetime

import frontmatter
from google import genai
from dotenv import load_dotenv

from content_quality import (
    is_blocked_guide_id,
    strip_code_fences,
    validate_guide_body,
)
from guide_prompts import MIN_BODY_CHARS, build_guide_prompt
from topic_queue_csv import resolve as resolve_queue_csv


def _emit_pipeline_result(**kwargs):
    try:
        from generation_result import emit_generation_result

        emit_generation_result(**kwargs)
    except ImportError:
        pass

# 설정 로드
load_dotenv()
try:
    from google.genai import types as genai_types

    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
        http_options=genai_types.HttpOptions(timeout=180_000),
    )
except Exception:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

GUIDE_CSV = 'script/csv/guides.csv'


def _guides_csv_path() -> str:
    return resolve_queue_csv("guides", GUIDE_CSV)


CONTENT_DIR = "app/content/guides"
os.makedirs(CONTENT_DIR, exist_ok=True)


def clean_guide_markdown(content: str) -> str:
    content = strip_code_fences(content)
    if content.strip().upper().startswith("SKIP_NOT_GOLF"):
        return "SKIP_NOT_GOLF"
    return content.strip() + ("\n" if not content.endswith("\n") else "")


def task_worker(topic_id, topic_name, lang, keywords):
    """실제 Gemini API를 호출하여 파일을 생성하는 워커 함수"""
    filepath = os.path.join(CONTENT_DIR, f"{topic_id}_{lang}.md")

    if is_blocked_guide_id(topic_id):
        return f"⏭️  Blocked topic id: {topic_id}_{lang}"

    if os.path.exists(filepath):
        return None  # 이미 있으면 스킵

    today = datetime.now().strftime("%Y-%m-%d")
    prompt = build_guide_prompt(
        topic_id=topic_id,
        topic_name=topic_name,
        lang=lang,
        keywords=keywords,
        today=today,
    )

    try:
        content = None
        body_len = 0
        quality_errors: list[str] = []
        for attempt in range(3):
            extra = ""
            if attempt == 1 and body_len and body_len < MIN_BODY_CHARS:
                extra = (
                    f"\n\nIMPORTANT: Previous draft body was only {body_len} chars. "
                    f"Write at least {MIN_BODY_CHARS} characters of useful steps (not filler)."
                )
            elif attempt >= 1 and quality_errors:
                extra = (
                    "\n\nIMPORTANT: Previous draft failed quality checks: "
                    + "; ".join(quality_errors)
                    + ". Fix those issues. Keep Quick Facts → Steps → Bottom Line."
                )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt + extra,
            )
            content = clean_guide_markdown(response.text)
            if content == "SKIP_NOT_GOLF":
                return f"⏭️  Skip not-golf topic: {topic_id}_{lang} ({topic_name})"

            post = frontmatter.loads(content)
            # Force today + lang even if model drifts
            post.metadata["date"] = today
            post.metadata["lang"] = lang
            body = post.content.strip()
            body_len = len(body)
            quality_errors = validate_guide_body(body, topic_name=topic_name)
            if body_len >= MIN_BODY_CHARS and not quality_errors:
                content = frontmatter.dumps(post)
                if not content.endswith("\n"):
                    content += "\n"
                break

        if content == "SKIP_NOT_GOLF":
            return f"⏭️  Skip not-golf topic: {topic_id}_{lang} ({topic_name})"
        if quality_errors:
            return f"❌ Quality fail: {topic_id}_{lang} -> {'; '.join(quality_errors)}"

        with open(filepath, "w", encoding="utf-8") as mf:
            mf.write(content)
        return f"✅ Success: {topic_id}_{lang} (body {body_len:,} chars)"
    except Exception as e:
        return f"❌ Error: {topic_id}_{lang} -> {e}"


def generate_guides_parallel(limit=5):
    tasks = []
    new_topics_count = 0
    skipped_blocked = 0

    csv_path = _guides_csv_path()
    if not os.path.exists(csv_path):
        print(f"❌ CSV 없음: {csv_path}")
        _emit_pipeline_result(step="guides", topics=0, generated=0, failed=1, ok=False)
        return

    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if new_topics_count >= limit:
                break

            topic_id = (row.get("id") or "").strip()
            if is_blocked_guide_id(topic_id):
                skipped_blocked += 1
                print(f"⏭️  Skip blocked guide id in queue: {topic_id}")
                continue

            if not (
                os.path.exists(os.path.join(CONTENT_DIR, f"{topic_id}_en.md"))
                and os.path.exists(os.path.join(CONTENT_DIR, f"{topic_id}_ko.md"))
            ):
                for lang in ["en", "ko"]:
                    tasks.append(
                        {
                            "topic_id": topic_id,
                            "topic_name": row.get(f"topic_{lang}") or row.get("topic_en") or topic_id,
                            "lang": lang,
                            "keywords": row.get("keywords") or "",
                        }
                    )
                new_topics_count += 1

    if skipped_blocked:
        print(f"🛡️  Blocked queue rows skipped: {skipped_blocked}")

    if not tasks:
        print("💡 생성할 새 가이드가 없습니다.")
        _emit_pipeline_result(step="guides", topics=0, generated=0)
        return

    print(f"🔥 병렬 처리 시작: 총 {len(tasks)}개 파일 생성 시도 (동시 작업 쓰레드: 10)")

    ok = 0
    failed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(
                task_worker, t["topic_id"], t["topic_name"], t["lang"], t["keywords"]
            )
            for t in tasks
        ]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                print(result)
                if result.startswith("✅"):
                    ok += 1
                elif result.startswith("❌"):
                    failed += 1
    _emit_pipeline_result(step="guides", topics=new_topics_count, generated=ok, failed=failed)


if __name__ == "__main__":
    # 실행 시 개수 지정 가능 (예: python script/guide_generator.py 20)
    if len(sys.argv) > 1:
        run_limit = int(sys.argv[1])
    else:
        run_limit = 5  # 기본값 5개 주제(파일 10개)

    start_time = time.time()
    generate_guides_parallel(limit=run_limit)
    end_time = time.time()

    print(f"\n⏱️ 소요 시간: {end_time - start_time:.2f}초")
