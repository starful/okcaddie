import os, csv, time, sys
import concurrent.futures
from datetime import datetime

import frontmatter
from dotenv import load_dotenv

from content_quality import (
    is_blocked_guide_id,
    strip_code_fences,
    validate_guide_body,
)
from guide_prompts import MIN_BODY_CHARS, build_guide_prompt, min_body_chars
from topic_queue_csv import resolve as resolve_queue_csv


def _emit_pipeline_result(**kwargs):
    try:
        from generation_result import emit_generation_result

        emit_generation_result(**kwargs)
    except ImportError:
        pass

# 설정 로드
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
    """실제 Claude API를 호출하여 파일을 생성하는 워커 함수"""
    filepath = os.path.join(CONTENT_DIR, f"{topic_id}_{lang}.md")

    if is_blocked_guide_id(topic_id):
        return f"⏭️  Blocked topic id: {topic_id}_{lang}"

    if os.path.exists(filepath):
        return None  # 이미 있으면 스킵

    today = datetime.now().strftime("%Y-%m-%d")
    min_chars = min_body_chars(lang)
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
            if attempt >= 1:
                parts: list[str] = []
                if body_len and body_len < min_chars:
                    parts.append(
                        f"Previous draft body was only {body_len} chars. "
                        f"Write at least {min_chars} characters of useful steps (not filler)."
                    )
                if quality_errors:
                    parts.append(
                        "Previous draft failed quality checks: "
                        + "; ".join(quality_errors)
                        + ". Fix those issues. For Japanese use H2 titles "
                        "`## 対象者`, `## 手順`, `## まとめ`. "
                        "Keep Quick Facts → Steps → Bottom Line."
                    )
                if parts:
                    extra = "\n\nIMPORTANT: " + " ".join(parts)
            response_text = _claude_md(prompt + extra)
            content = clean_guide_markdown(response_text)
            if content == "SKIP_NOT_GOLF":
                return f"⏭️  Skip not-golf topic: {topic_id}_{lang} ({topic_name})"

            post = frontmatter.loads(content)
            # Force today + lang even if model drifts
            post.metadata["date"] = today
            post.metadata["lang"] = lang
            body = post.content.strip()
            body_len = len(body)
            quality_errors = validate_guide_body(body, topic_name=topic_name)
            if body_len >= min_chars and not quality_errors:
                content = frontmatter.dumps(post)
                if not content.endswith("\n"):
                    content += "\n"
                break
            print(
                f"↻ retry {attempt + 1}/3 {topic_id}_{lang}: "
                f"body={body_len} errs={quality_errors or '-'}",
                flush=True,
            )

        if content == "SKIP_NOT_GOLF":
            return f"⏭️  Skip not-golf topic: {topic_id}_{lang} ({topic_name})"
        if quality_errors:
            return f"❌ Quality fail: {topic_id}_{lang} -> {'; '.join(quality_errors)}"
        if body_len < min_chars:
            return f"❌ Quality fail: {topic_id}_{lang} -> too_short:{body_len}<{min_chars}"

        with open(filepath, "w", encoding="utf-8") as mf:
            mf.write(content)
        return f"✅ Success: {topic_id}_{lang} (body {body_len:,} chars)"
    except Exception as e:
        return f"❌ Error: {topic_id}_{lang} -> {e}"


def _want_fill_lang() -> str:
    v = (os.environ.get("FILL_LANG") or "").strip().lower()
    if v and v not in ("en", "ko", "ja"):
        raise ValueError(f"FILL_LANG invalid: {v} (use en|ko|ja)")
    return v


def _fill_lang_guide_tasks(limit: int, fill_lang: str) -> list[dict]:
    """Queue missing target-lang guides from existing sibling MD files."""
    stems: set[str] = set()
    for name in os.listdir(CONTENT_DIR):
        if name.endswith("_en.md"):
            stems.add(name[: -len("_en.md")])
        elif name.endswith("_ko.md"):
            stems.add(name[: -len("_ko.md")])
        elif name.endswith("_ja.md"):
            stems.add(name[: -len("_ja.md")])
    tasks: list[dict] = []
    for topic_id in sorted(stems):
        if len(tasks) >= limit:
            break
        if is_blocked_guide_id(topic_id):
            continue
        target = os.path.join(CONTENT_DIR, f"{topic_id}_{fill_lang}.md")
        if os.path.isfile(target):
            continue
        sibling = None
        for sib in ("en", "ko", "ja"):
            if sib == fill_lang:
                continue
            path = os.path.join(CONTENT_DIR, f"{topic_id}_{sib}.md")
            if os.path.isfile(path):
                sibling = path
                break
        if not sibling:
            continue
        topic_name = topic_id.replace("-", " ")
        keywords = ""
        try:
            post = frontmatter.load(sibling)
            meta = post.metadata if isinstance(post.metadata, dict) else {}
            topic_name = str(meta.get("title") or topic_name).strip()
            keywords = str(meta.get("keywords") or meta.get("summary") or "")[:200]
        except Exception:
            pass
        tasks.append(
            {
                "topic_id": topic_id,
                "topic_name": topic_name,
                "lang": fill_lang,
                "keywords": keywords,
            }
        )
    return tasks


def generate_guides_parallel(limit=5):
    tasks = []
    new_topics_count = 0
    skipped_blocked = 0
    half_skipped = 0
    try:
        fill_lang = _want_fill_lang()
    except ValueError as exc:
        print(f"❌ {exc}")
        _emit_pipeline_result(step="guides", topics=0, generated=0, failed=1, ok=False)
        return
    fill_half = os.environ.get("FILL_HALF", "").strip().lower() in ("1", "true", "yes")
    if fill_lang and fill_half:
        print("⚠️  FILL_LANG set — ignoring FILL_HALF")
        fill_half = False

    if fill_lang:
        tasks = _fill_lang_guide_tasks(limit, fill_lang)
        new_topics_count = len(tasks)
    else:
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

                locales = ("en", "ko", "ja")
                exists = {
                    lang: os.path.exists(os.path.join(CONTENT_DIR, f"{topic_id}_{lang}.md"))
                    for lang in locales
                }
                if all(exists.values()):
                    continue
                if fill_half:
                    if not any(exists.values()):
                        continue
                    for lang in locales:
                        if exists[lang]:
                            continue
                        tasks.append(
                            {
                                "topic_id": topic_id,
                                "topic_name": row.get(f"topic_{lang}") or row.get("topic_en") or topic_id,
                                "lang": lang,
                                "keywords": row.get("keywords") or "",
                            }
                        )
                    new_topics_count += 1
                    continue
                if any(exists.values()):
                    half_skipped += 1
                    continue

                for lang in locales:
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
    if half_skipped:
        print(f"⏭️  반쪽(en/ko/ja 일부만) 가이드 {half_skipped}건 — 신규 트리플 우선으로 스킵")

    if not tasks:
        if fill_lang:
            msg = f"💡 채울 {fill_lang} 가이드가 없습니다."
        elif fill_half:
            msg = "💡 채울 반쪽 가이드가 없습니다."
        else:
            msg = "💡 생성할 새 가이드 페어가 없습니다."
        print(msg)
        _emit_pipeline_result(step="guides", topics=0, generated=0, skipped=half_skipped)
        return

    if fill_lang:
        print(f"ℹ️  FILL_LANG={fill_lang}: {new_topics_count}주제 · {len(tasks)}파일")
    elif fill_half:
        print(f"ℹ️  반쪽 채우기: {new_topics_count}주제 · {len(tasks)}파일")
    print(f"🔥 병렬 처리 시작: 신규 {new_topics_count}트리플 · {len(tasks)}파일 (동시 작업 쓰레드: 10)")

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
    _emit_pipeline_result(
        step="guides",
        topics=new_topics_count,
        generated=ok,
        failed=failed,
        skipped=half_skipped,
    )


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
