"""Text normalization helpers for titles, summaries, and LLM artifacts."""

from __future__ import annotations

import re

_LANG_SUFFIX_RE = re.compile(r"\s*\(\s*(?:en|ko|EN|KO)\s*\)\s*$")
_REVIEW_BOILERPLATE_RE = re.compile(
    r"^\s*The\s+Definitive\s+Guide\s+to\s+(?P<name>.+?)\s*:\s*An\s+Expert\s+Review\b.*$",
    re.IGNORECASE,
)
_BOILERPLATE_PHRASES = (
    "The Definitive Guide to ",
    ": An Expert Review",
    "An Expert Review",
    " Masterpiece Review",
    "마스터피스 리뷰",
    "마스터 리뷰",
    "마스터 가이드",
    "완벽 가이드",
    "전문가 리뷰",
    "심층 분석",
    "20년 경력 베테랑 캐디의",
)
_RUNTIME_SELFCHECK_PATTERNS = [
    re.compile(r"^\s*\*{0,2}\s*\(?\s*Total\s+character", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*\*{0,2}\s*\(?\s*Character\s+count\s+check", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*Markdown\s+formatting\s+with", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*YAML\s+frontmatter\s+is\s+correctly", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*The\s+tone\s+is\s+professional,?\s+technical", re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"^\s*The\s+generated\s+(?:Korean|English)\s+content\s+is\s+~?\s*\d",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^\s*\d+\.\s+\*\*(?:Character\s+Count|Tone|Language|YAML\s+Frontmatter)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(r"^\s*```(?:markdown|yaml)\s*$", re.IGNORECASE | re.MULTILINE),
]
_PROMO_SUMMARY_RE = re.compile(
    r"\d{1,3},?\d{3}\s*(?:자|character|-?\s*character)",
    re.IGNORECASE,
)


def get_meta_fallback(text, key):
    """YAML 파싱 실패 시 정규식으로 데이터를 강제 추출하는 백업 함수"""
    pattern = rf'{key}:\s*["\']?(.*?)["\']?\n'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def humanize_title(title):
    """타이틀에서 라벨·보일러플레이트를 정리해 SERP에 어울리는 형태로 만든다."""
    if not title:
        return ""
    s = _LANG_SUFFIX_RE.sub("", str(title).strip())
    m = _REVIEW_BOILERPLATE_RE.match(s)
    if m:
        return m.group("name").strip()

    cleaned = s
    for phrase in _BOILERPLATE_PHRASES:
        cleaned = cleaned.replace(phrase, "")
    for sep in (":", "：", " - ", " — "):
        if sep in cleaned:
            prefix = cleaned.split(sep, 1)[0].strip()
            if len(prefix) >= 4:
                cleaned = prefix
                break
    cleaned = cleaned.strip(" -—|·•")
    if len(cleaned) > 70 and " | " in cleaned:
        first = cleaned.split(" | ")[0].strip()
        if len(first) >= 5:
            cleaned = first
    return cleaned or s


def short_summary(summary, limit=155):
    """SERP description 길이 제한 (모바일 우선)."""
    if not summary:
        return ""
    s = str(summary).strip()
    if len(s) <= limit:
        return s
    return s[: limit - 1].rstrip() + "…"


def strip_llm_selfcheck(body):
    """본문에서 LLM 자기점검 푸터가 나타나는 첫 위치부터 끝까지 잘라낸다."""
    if not body:
        return body
    earliest = len(body)
    for pat in _RUNTIME_SELFCHECK_PATTERNS:
        m = pat.search(body)
        if m and m.start() < earliest:
            earliest = m.start()
    if earliest < len(body):
        return body[:earliest].rstrip()
    return body


def clean_summary(summary, title="", lang="en"):
    """AI 보일러플레이트 summary 를 SERP-친화적 형태로 대체한다."""
    if not summary:
        return summary
    s = str(summary).strip()
    if not _PROMO_SUMMARY_RE.search(s):
        return s
    name = humanize_title(title) if title else ""
    if lang == "ko":
        return f"{name} 그린피, 예약 정보, 코스 공략, 접근성, 베스트 시즌까지 한 페이지에 정리한 가이드.".strip()
    return f"{name} guide: green fees, booking paths, layout strategy, access tips, and best seasons.".strip()


def truncate_text(value, max_len):
    text = " ".join(str(value or "").split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"
