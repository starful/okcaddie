#!/usr/bin/env python3
"""Re-expand compact course pages to practical visitor depth (3k+)."""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import sys
import time

import frontmatter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
APP_DIR = os.path.join(BASE_DIR, "app")
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, APP_DIR)

from course_generator import (  # noqa: E402
    client,
    CONTENT_DIR,
    clean_generated_markdown,
)
from content_quality import is_non_golf_course_slug, validate_course_body  # noqa: E402
from course_prompts import MIN_BODY_CHARS, build_course_prompt  # noqa: E402
from text_utils import humanize_title  # noqa: E402

SEO_KEYS = ("seo_title", "seo_description")


def body_length(path: str) -> int:
    with open(path, "r", encoding="utf-8") as f:
        post = frontmatter.load(f)
    return len(post.content.strip())


def find_short_targets(
    content_dir: str | None = None,
    min_chars: int = MIN_BODY_CHARS,
    langs: tuple[str, ...] = ("en", "ko"),
) -> list[tuple[str, str, int]]:
    """Return (base_id, lang, body_chars) for files under min_chars."""
    root = content_dir or CONTENT_DIR
    out: list[tuple[str, str, int]] = []
    for lang in langs:
        for name in sorted(os.listdir(root)):
            if not name.endswith(f"_{lang}.md") or name.startswith("_"):
                continue
            base_id = name[: -len(f"_{lang}.md")]
            if is_non_golf_course_slug(base_id):
                continue
            path = os.path.join(root, name)
            n = body_length(path)
            if n < min_chars:
                out.append((base_id, lang, n))
    return sorted(out, key=lambda x: (x[0], x[1]))


def load_course_data(base_id: str, lang: str) -> dict | None:
    path = os.path.join(CONTENT_DIR, f"{base_id}_{lang}.md")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        post = frontmatter.load(f)
    meta = dict(post.metadata)
    cats = meta.get("categories", "")
    if isinstance(cats, list):
        features = ", ".join(cats)
    else:
        features = str(cats)
    return {
        "safe_name": base_id,
        "name": humanize_title(str(meta.get("title", base_id.replace("_", " ").title()))),
        "lat": str(meta.get("lat", "")),
        "lng": str(meta.get("lng", "")),
        "address": str(meta.get("address", "Japan")),
        "features": features,
        "date": str(meta.get("date", ""))[:10] or time.strftime("%Y-%m-%d"),
        "lang": lang,
        "seo": {k: meta[k] for k in SEO_KEYS if meta.get(k)},
    }


def generate_medium(data: dict, *, min_chars: int = MIN_BODY_CHARS) -> int:
    safe_name = data["safe_name"]
    lang = data["lang"]
    filepath = os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md")
    if is_non_golf_course_slug(safe_name, data.get("name", "")):
        return body_length(filepath) if os.path.exists(filepath) else 0

    prior_len = body_length(filepath) if os.path.exists(filepath) else 0
    prompt = build_course_prompt(data)

    content = None
    best_len = prior_len
    best_content = None
    for attempt in range(3):
        extra = ""
        if attempt > 0:
            extra = (
                f"\n\nIMPORTANT: Previous draft body was only {best_len} chars. "
                f"Write at least {min_chars} characters of useful trip-planning detail "
                f"(Quick Facts → Fees/Booking → Access). No masterclass filler."
            )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt + extra,
        )
        candidate = clean_generated_markdown(response.text.strip())

        if data.get("seo"):
            post = frontmatter.loads(candidate)
            for k, v in data["seo"].items():
                post[k] = v
            candidate = frontmatter.dumps(post)

        body = frontmatter.loads(candidate).content.strip()
        body_len = len(body)
        if validate_course_body(body):
            continue
        if body_len > best_len:
            best_len = body_len
            best_content = candidate
        if body_len >= min_chars:
            best_content = candidate
            best_len = body_len
            break

    if best_content is None or best_len <= prior_len:
        return prior_len

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(best_content)

    return best_len


DEFAULT_WORKERS = 10


def expand_one_task(base_id: str, lang: str, *, min_chars: int) -> tuple[str, str, bool, int, str | None]:
    """Worker: expand a single (base_id, lang). Returns (base_id, lang, ok, body_len, error)."""
    data = load_course_data(base_id, lang)
    if not data:
        return base_id, lang, False, 0, "missing file"
    try:
        n = generate_medium(data, min_chars=min_chars)
        ok = n >= min_chars
        return base_id, lang, ok, n, None
    except Exception as e:
        return base_id, lang, False, 0, str(e)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Expand course pages under a body-length threshold.")
    p.add_argument(
        "base_ids",
        nargs="*",
        help="Optional base_id list (default: auto-scan all files under --min-chars)",
    )
    p.add_argument("--min-chars", type=int, default=MIN_BODY_CHARS, help=f"Body length threshold (default {MIN_BODY_CHARS})")
    p.add_argument("--lang", default="en,ko", help="Comma-separated langs to scan/expand (default en,ko)")
    p.add_argument("--dry-run", action="store_true", help="List targets only; do not call Gemini")
    p.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help=f"Parallel API workers (default {DEFAULT_WORKERS})")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    langs = tuple(x.strip() for x in args.lang.split(",") if x.strip())

    if args.base_ids:
        targets = []
        for base_id in args.base_ids:
            for lang in langs:
                path = os.path.join(CONTENT_DIR, f"{base_id}_{lang}.md")
                if not os.path.exists(path):
                    continue
                n = body_length(path)
                if n < args.min_chars:
                    targets.append((base_id, lang, n))
    else:
        targets = find_short_targets(min_chars=args.min_chars, langs=langs)

    if not targets:
        print(f"✅ No files under {args.min_chars} chars for langs={','.join(langs)}")
        return 0

    en_n = sum(1 for _, lang, _ in targets if lang == "en")
    ko_n = sum(1 for _, lang, _ in targets if lang == "ko")
    print(f"📝 Expand targets: {len(targets)} files (EN {en_n}, KO {ko_n}), min={args.min_chars} chars\n")
    for base_id, lang, n in targets:
        print(f"  {base_id}_{lang}  ({n:,} chars)")

    if args.dry_run:
        print("\n(dry-run — no API calls)")
        return 0

    workers = max(1, args.workers)
    print(f"\n🚀 Parallel expand: {workers} workers\n")

    ok, warn, err = 0, 0, 0
    jobs = [(base_id, lang) for base_id, lang, _ in targets]

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(expand_one_task, base_id, lang, min_chars=args.min_chars): (base_id, lang)
            for base_id, lang in jobs
        }
        for future in concurrent.futures.as_completed(futures):
            base_id, lang, success, n, error = future.result()
            if error == "missing file":
                print(f"  ⏭️  skip missing: {base_id}_{lang}")
                err += 1
            elif error:
                print(f"  ❌ {base_id}_{lang}: {error}")
                err += 1
            elif success:
                ok += 1
                print(f"  ✅ {base_id}_{lang} → {n:,} chars body")
            elif n > 0 and n < args.min_chars:
                warn += 1
                print(f"  ⏭️  {base_id}_{lang} → kept prior ({n:,} chars, no improvement)")
            else:
                warn += 1
                print(f"  ✅ {base_id}_{lang} → {n:,} chars body ⚠️ still short")

    print(f"\n✨ Done ({ok} ok, {warn} still short, {err} errors). Run: python script/build_data.py")
    return 0 if warn == 0 and err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
