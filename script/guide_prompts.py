"""Shared Gemini prompts for guide markdown."""

from __future__ import annotations

from datetime import datetime

MIN_BODY_CHARS = 2800

LANG_FULL = {"en": "English", "ko": "Korean"}


def length_target(lang: str) -> str:
    return "2,800 to 5,500 characters" if lang == "ko" else "3,000 to 6,000 characters"


def summary_hint(lang: str) -> str:
    if lang == "ko":
        return "골프 여행자에게 바로 도움이 되는 구체적 한 문장 요약(<=140자)."
    return "One concrete sentence for golf travelers (<=155 chars) with a usable tip."


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
- Total length: {length_target(lang)}. Minimum body after frontmatter: {MIN_BODY_CHARS} characters.
- Use H2 (##) only. 6 to 8 H2 sections in the order below.

[SECTIONS — IN THIS ORDER]
1. ## Quick Facts — who this is for, time needed, cost band if relevant, season.
2. ## Who This Guide Is For — and who should skip it.
3. ## How It Works / Steps — concrete numbered steps a traveler can follow.
4. ## Costs & Booking Reality — ranges, common pitfalls, what to confirm live.
5. ## Regional / Course Notes — only if relevant; name real patterns, not fake reviews.
6. ## Common Mistakes — 4 to 6 bullets.
7. ## Bottom Line — 2 to 3 sentences with the decision rule.

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
