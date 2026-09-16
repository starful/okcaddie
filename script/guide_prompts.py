"""Shared Gemini prompts for guide markdown."""

from __future__ import annotations

from datetime import datetime

MIN_BODY_CHARS = 2800
MIN_BODY_CHARS_BY_LANG = {"en": 2800, "ko": 2500, "ja": 1600}


def min_body_chars(lang: str) -> int:
    return MIN_BODY_CHARS_BY_LANG.get(str(lang).lower(), MIN_BODY_CHARS)

LANG_FULL = {"en": "English", "ko": "Korean", "ja": "Japanese"}


def length_target(lang: str) -> str:
    if lang == "ko":
        return "2,500 to 5,500 characters"
    if lang == "ja":
        return "at least 2,200 characters (prefer 2,800+)"
    return "3,000 to 6,000 characters"


def summary_hint(lang: str) -> str:
    if lang == "ko":
        return "골프 여행자에게 바로 도움이 되는 구체적 한 문장 요약(<=140자)."
    if lang == "ja":
        return "ゴルフ旅行者にすぐ役立つ具体的な一文要約(<=140字)。"
    return "One concrete sentence for golf travelers (<=155 chars) with a usable tip."


def _sections_block(lang: str) -> str:
    if lang == "ja":
        return """[SECTIONS — USE THESE H2 TITLES (exact Japanese preferred)]
1. ## クイックファクト — who this is for, time needed, cost band if relevant, season.
2. ## 対象者 — and who should skip it (must include 対象者 or こんな人 in the H2).
3. ## 手順 — concrete numbered steps a traveler can follow (must include 手順 or ステップ).
4. ## 費用と予約 — ranges, common pitfalls, what to confirm live.
5. ## 地域・コースのポイント — only if relevant; real patterns, not fake reviews.
6. ## よくある失敗 — 4 to 6 bullets.
7. ## まとめ — 2 to 3 sentences with the decision rule (must include まとめ or 結論)."""
    return """[SECTIONS — COVER THESE THEMES]
1. ## Quick Facts — who this is for, time needed, cost band if relevant, season.
2. ## Who This Guide Is For — and who should skip it.
3. ## How It Works / Steps — concrete numbered steps a traveler can follow.
4. ## Costs & Booking Reality — ranges, common pitfalls, what to confirm live.
5. ## Regional / Course Notes — only if relevant; name real patterns, not fake reviews.
6. ## Common Mistakes — 4 to 6 bullets.
7. ## Bottom Line — 2 to 3 sentences with the decision rule."""


def build_guide_prompt(
    *,
    topic_id: str,
    topic_name: str,
    lang: str,
    keywords: str,
    today: str | None = None,
) -> str:
    lang_full = LANG_FULL.get(lang, "English")
    today = today or datetime.now().strftime("%Y-%m-%d")
    kw = keywords or topic_name
    sections = _sections_block(lang)

    return f"""You are a practical Japan golf travel editor for OKCaddie.
Write in {lang_full}. Help a visitor make a decision or complete a trip task.
No fluff, no personal-brand caddy monologue, no cafe/dessert digressions unless the topic is explicitly about golf logistics.

Topic ID: {topic_id}
Topic: {topic_name}
Keywords: {kw}

[HARD RULES]
- The guide MUST be useful for golf travel in Japan (booking, courses, regions, etiquette, gear logistics, seasons).
- If the topic is not golf-travel relevant, refuse by writing only: SKIP_NOT_GOLF
- Do NOT use: "world-class", "unforgettable", "must-visit", "Definitive Guide", "Expert Review",
  "masterpiece", "as an elite", "two decades", "Historical Prestige", "Hole-by-Hole Masterclass",
  "20년 경력", "마스터피스".
- Do NOT invent exact yen prices, phone numbers, or URLs. Use ranges and "verify live" wording.
- Prefer checklists and steps over ornate prose.
- Total length: {length_target(lang)}. Minimum body after frontmatter: {min_body_chars(lang)} characters.
- Use H2 (##) only. 6 to 8 H2 sections covering the themes below.

{sections}

[FORMATTING]
- Raw Markdown only. NO code fences. NO character-count self-check.
- Start with YAML frontmatter (values in double quotes):

---
lang: "{lang}"
title: "{topic_name}"
summary: "{summary_hint(lang)}"
date: "{today}"
---
"""
