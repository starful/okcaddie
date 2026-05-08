"""
AI가 본문 끝에 자기점검 메타텍스트 + 본문을 한 번 더 출력해버린 케이스를 정리한다.
- 영문 self-check 마커가 보이면 그 줄부터 잘라낸다.
- 마커가 없어도 첫 번째 ## H2 헤더가 두 번 이상 나오면 두 번째 등장 직전에서 잘라낸다.
- 파일 끝의 ``` 잔재 제거.
- frontmatter는 그대로 보존한다.
"""
import os
import re
import sys

CONTENT_DIRS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "content"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "content", "guides"),
]

# 영문 self-check / LLM commentary 마커 (어느 한 줄에서라도 매치되면 그 위까지만 보존)
# LLM "self-reflection" 푸터의 시작점만 정확히 매치한다.
# 모두 줄 시작(^) 앵커. 본문 안의 일반 문장은 절대 건드리지 않는다.
SELFCHECK_PATTERNS = [
    re.compile(r"^\s*\*{0,2}\s*\(?\s*Total\s+character(?:\s+count)?\b", re.IGNORECASE),
    re.compile(r"^\s*\*{0,2}\s*\(?\s*Character\s+count\s+check\b", re.IGNORECASE),
    re.compile(r"^\s*Total\s+(?:characters?|length)\s*[:=(]", re.IGNORECASE),
    re.compile(r"^\s*Each\s+section\s+length", re.IGNORECASE),
    re.compile(r"^\s*Markdown\s+formatting\s+with", re.IGNORECASE),
    re.compile(r"^\s*The\s+tone\s+is\s+professional,?\s+technical", re.IGNORECASE),
    re.compile(r"^\s*YAML\s+frontmatter\s+is\s+correctly", re.IGNORECASE),
    re.compile(r"^\s*The\s+generated\s+(?:Korean|English)\s+content\s+is\s+~?\s*\d", re.IGNORECASE),
    re.compile(r"^\s*Korean\s+language\s+is\s+used\s+throughout", re.IGNORECASE),
    re.compile(r"^\s*This\s+falls\s+within\s+the\s+target\s+range", re.IGNORECASE),
    re.compile(r"^\s*\*?\s*\(?\s*aiming\s+for\s+\d{3,}", re.IGNORECASE),
    re.compile(r"^\s*\*?\s*\(?\s*approximately\s+\d{3,}\s+characters?", re.IGNORECASE),
    re.compile(r"^\s*```markdown\s*$", re.IGNORECASE),
    re.compile(r"^\s*```yaml\s*$", re.IGNORECASE),
    # 추가 변형들 (실제 문서에서 발견)
    re.compile(r"^\s*Total\s+characters?\s+will\s+be\s+within", re.IGNORECASE),
    re.compile(r"^\s*\*?\s*\*?\*?Total\s+(?:length|characters?)\s*[:\*]", re.IGNORECASE),
    re.compile(r"^\s*Total\s+estimated\s+characters?", re.IGNORECASE),
    re.compile(r"^\s*Let\s+me\s+(?:quickly\s+)?estimate\s+the\s+character\s+count", re.IGNORECASE),
    re.compile(r"falls\s+(?:perfectly\s+)?within\s+the\s+(?:8\s*,?\s*000|target)", re.IGNORECASE),
    re.compile(r"^\s*\*\s+\*\*(?:Tone|Formatting|SEO\s+Optimization|Total)\*\*\s*:", re.IGNORECASE),
    # 번호 매겨진 LLM 자기점검 리스트 (e.g. "1.  **Character Count:**")
    re.compile(
        r"^\s*\d+\.\s+\*\*(?:Character\s+Count|Tone|Language|YAML\s+Frontmatter|Markdown\s+Formatting|SEO|Formatting)\b",
        re.IGNORECASE,
    ),
]

CODEFENCE_TAIL_RE = re.compile(r"\n*`{3,}\s*\w*\s*$")


def split_frontmatter(text):
    """파일을 (frontmatter_block_with_delims, body) 로 분리. frontmatter 없으면 ('', text)."""
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return "", text
    # 첫 '---' 이후 다음 '---' 까지가 frontmatter
    m = re.search(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return "", text
    fm = text[: m.end()]
    body = text[m.end():]
    return fm, body


def cut_at_selfcheck(body):
    lines = body.splitlines()
    for i, line in enumerate(lines):
        for pat in SELFCHECK_PATTERNS:
            if pat.search(line):
                return "\n".join(lines[:i]).rstrip() + "\n"
    return body


def cut_at_duplicate_h2(body):
    """첫 번째 H2 헤더가 본문 내에 두 번 이상 등장하면 두 번째 직전까지만 보존."""
    lines = body.splitlines()
    first_h2 = None
    first_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("## "):
            first_h2 = line.strip()
            first_idx = i
            break
    if first_h2 is None:
        return body
    # 두 번째 occurrence 찾기
    for j in range(first_idx + 1, len(lines)):
        if lines[j].strip() == first_h2:
            return "\n".join(lines[:j]).rstrip() + "\n"
    return body


def clean_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    fm, body = split_frontmatter(text)
    if not body.strip():
        return False, 0, 0

    original_len = len(body)
    cleaned = cut_at_selfcheck(body)
    cleaned = cut_at_duplicate_h2(cleaned)
    cleaned = CODEFENCE_TAIL_RE.sub("", cleaned).rstrip() + "\n"

    if cleaned == body:
        return False, original_len, original_len

    new_text = fm + cleaned
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)
    return True, original_len, len(cleaned)


def main():
    files = []
    for d in CONTENT_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if fn.endswith(".md"):
                files.append(os.path.join(d, fn))

    files.sort()
    changed = 0
    saved_chars = 0
    for path in files:
        changed_flag, before, after = clean_file(path)
        if changed_flag:
            changed += 1
            saved_chars += (before - after)
            rel = os.path.relpath(path)
            print(f"  ✂️  {rel}: {before} → {after} chars (-{before - after})")

    print()
    print(f"Done. {changed} file(s) cleaned, {saved_chars:,} chars removed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
