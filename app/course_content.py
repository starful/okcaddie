"""Course markdown helpers shared by runtime, builds, and generators."""

from __future__ import annotations

import os

import frontmatter

COURSE_FRONTMATTER_KEYS = frozenset(
    {
        "lang",
        "title",
        "lat",
        "lng",
        "categories",
        "thumbnail",
        "address",
        "date",
        "booking",
        "summary",
        "description",
        "seo_title",
        "seo_description",
    }
)

COURSE_METADATA_FALLBACK_KEYS = frozenset(
    {
        "lat",
        "lng",
        "categories",
        "thumbnail",
        "address",
        "booking",
        "description",
        "seo_title",
        "seo_description",
    }
)


def _extract_embedded_metadata_block(text: str) -> tuple[dict, str, bool]:
    original = text
    lines = text.lstrip("\n").splitlines()
    if not lines:
        return {}, original, False

    candidate_lines: list[str] = []
    saw_key = False
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        if stripped == "---":
            if not saw_key:
                return {}, original, False
            candidate = "---\n" + "\n".join(candidate_lines).rstrip() + "\n---\n"
            metadata = dict(frontmatter.loads(candidate).metadata)
            remainder = "\n".join(lines[idx + 1 :]).lstrip("\n")
            return metadata, remainder, True

        if not stripped:
            candidate_lines.append(line)
            idx += 1
            continue

        if line[:1].isspace():
            if not candidate_lines:
                return {}, original, False
            candidate_lines.append(line)
            idx += 1
            continue

        key, sep, _ = line.partition(":")
        key = key.strip()
        if not sep or key not in COURSE_FRONTMATTER_KEYS:
            return {}, original, False

        saw_key = True
        candidate_lines.append(line)
        idx += 1

    return {}, original, False


def loads_course_post(raw: str):
    post = frontmatter.loads(raw)
    metadata = dict(post.metadata)
    body = post.content

    embedded_meta, cleaned_body, normalized = _extract_embedded_metadata_block(body)
    if normalized:
        metadata.update(embedded_meta)
        body = cleaned_body

    return frontmatter.Post(body, **metadata), normalized


def _lang_from_path(path: str) -> str | None:
    stem = os.path.splitext(os.path.basename(path))[0]
    if stem.endswith("_ko"):
        return "ko"
    if stem.endswith("_en"):
        return "en"
    return None


def _title_from_content(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
        if stripped:
            break
    return ""


def _sibling_course_path(path: str) -> str | None:
    stem, ext = os.path.splitext(path)
    if stem.endswith("_ko"):
        return stem[:-3] + "_en" + ext
    if stem.endswith("_en"):
        return stem[:-3] + "_ko" + ext
    return None


def load_course_post_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        post, normalized = loads_course_post(f.read())

    metadata = dict(post.metadata)
    changed = normalized

    inferred_lang = _lang_from_path(path)
    if inferred_lang and not metadata.get("lang"):
        metadata["lang"] = inferred_lang
        changed = True

    inferred_title = _title_from_content(post.content)
    if inferred_title and not metadata.get("title"):
        metadata["title"] = inferred_title
        changed = True

    sibling_path = _sibling_course_path(path)
    if sibling_path and os.path.exists(sibling_path):
        with open(sibling_path, "r", encoding="utf-8") as f:
            sibling_post, _ = loads_course_post(f.read())
        sibling_meta = dict(sibling_post.metadata)
        for key in COURSE_METADATA_FALLBACK_KEYS:
            if not metadata.get(key) and sibling_meta.get(key):
                metadata[key] = sibling_meta[key]
                changed = True

    return frontmatter.Post(post.content, **metadata), changed


def normalize_course_markdown(raw: str) -> tuple[str, bool]:
    post, normalized = loads_course_post(raw)
    if not normalized:
        return raw, False
    return frontmatter.dumps(post), True
