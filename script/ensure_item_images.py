"""MD가 있는 항목 중 썸네일이 없으면 default 이미지를 slug.jpg로 복사 (GCS rsync 대상)."""

import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
IMAGES_DIR = os.path.join(BASE_DIR, "app", "static", "images")
CONTENT_DIR = os.path.join(BASE_DIR, "app", "content")

DEFAULT_CANDIDATES = ("default.png", "default.jpg")
LANG_SUFFIXES = ("_ko", "_en")
PROTECTED = {
    "logo.png",
    "logo.svg",
    "favicon.ico",
    "default.png",
    "default.jpg",
    "og_image.png",
}


def _default_source_path() -> str | None:
    for name in DEFAULT_CANDIDATES:
        path = os.path.join(IMAGES_DIR, name)
        if os.path.isfile(path):
            return path
    return None


def collect_content_slugs() -> set[str]:
    slugs: set[str] = set()
    if not os.path.isdir(CONTENT_DIR):
        return slugs
    for fname in os.listdir(CONTENT_DIR):
        if not fname.endswith(".md"):
            continue
        base = fname[:-3]
        for lang in LANG_SUFFIXES:
            if base.endswith(lang):
                slugs.add(base[: -len(lang)])
                break
    return slugs


def ensure_item_images(*, slugs: set[str] | None = None) -> dict[str, int]:
    os.makedirs(IMAGES_DIR, exist_ok=True)
    source = _default_source_path()
    if not source:
        print(f"❌ 기본 이미지 없음: {IMAGES_DIR}/default.png (또는 default.jpg)")
        return {"copied": 0, "skipped": 0, "failed": 0}

    targets = sorted(slugs if slugs is not None else collect_content_slugs())
    copied = skipped = failed = 0

    print(f"\n📋 default placeholder — {len(targets)}개 slug 확인")
    print(f"   source: {os.path.basename(source)}\n")

    for slug in targets:
        if not slug:
            continue
        filename = f"{slug}.jpg"
        if filename in PROTECTED:
            continue
        target = os.path.join(IMAGES_DIR, filename)
        if os.path.isfile(target):
            skipped += 1
            continue
        try:
            shutil.copy2(source, target)
            copied += 1
            print(f"  ✅ {filename}")
        except OSError as exc:
            failed += 1
            print(f"  ❌ {filename}: {exc}")

    print("\n" + "─" * 50)
    print(f"📋 placeholder 완료 — 생성: {copied} / 기존: {skipped} / 실패: {failed}")
    print("─" * 50)
    return {"copied": copied, "skipped": skipped, "failed": failed}


if __name__ == "__main__":
    ensure_item_images()
