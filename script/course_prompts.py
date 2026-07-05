"""Shared Gemini prompts and body-length thresholds for course markdown."""

from __future__ import annotations

from datetime import datetime

MIN_BODY_CHARS = 6000

LANG_FULL = {"en": "English", "ko": "Korean"}

CSV_FACT_FIELDS = [
    ("Holes", "Holes"),
    ("Total Yardage", "Yardage"),
    ("Par", "Par"),
    ("Designer", "Designer"),
    ("Opened Year", "OpenedYear"),
    ("Green Fee Range (JPY)", "GreenFee"),
    ("Phone", "Phone"),
    ("Website", "Website"),
]


def length_target(lang: str) -> str:
    return "5,500 to 8,500 characters" if lang == "ko" else "6,000 to 9,000 characters"


def summary_hint(lang: str) -> str:
    if lang == "ko":
        return "Provide a concrete 1-sentence summary in Korean (<=140 chars) with a numeric or location detail."
    return "Provide a concrete 1-sentence summary in English (<=155 chars) with a numeric or location detail."


def known_facts_block(data: dict) -> str:
    lines = []
    for label, key in CSV_FACT_FIELDS:
        v = data.get(key) or ""
        if v:
            lines.append(f"- {label}: {v}")
    if not lines:
        return ""
    return "\n[KNOWN FACTS — TREAT AS GROUND TRUTH]\n" + "\n".join(lines)


def build_course_prompt(data: dict, *, today: str | None = None) -> str:
    """Medium-depth course profile prompt (6k+ EN / 5.5k+ KO)."""
    lang = data["lang"]
    lang_full = LANG_FULL.get(lang, "English")
    safe_name = data["safe_name"]
    name = data["name"]
    today = today or data.get("date") or datetime.now().strftime("%Y-%m-%d")
    facts = known_facts_block(data)

    return f"""You are a senior Japan golf travel writer for OKCaddie.
Write in {lang_full}. Be specific and useful for trip planning. Avoid generic praise and filler.

Course: {name}
Address: {data['address']}
Coordinates: {data['lat']}, {data['lng']}
Tags: {data['features']}{facts}

[GOAL]
- Total length: {length_target(lang)} (substantive paragraphs, not bullet-only lists).
- Minimum body length after frontmatter: {MIN_BODY_CHARS} characters.
- 3-4 sentences per major section where appropriate.
- Use H2 (##) only. Use 7 to 8 H2 sections in the order below.
- Do NOT use: "world-class", "unforgettable", "must-visit", "Definitive Guide", "Expert Review", "masterpiece".
- Use realistic ranges for yardage/green fees when exact data is uncertain.
- Do NOT invent phone numbers or URLs beyond what is provided.

[SECTIONS — IN THIS ORDER]
1. ## Course Overview — history snippet, holes/par/yardage, designer/year if known, turf types, overall character.
2. ## Layout & Strategy — describe 4 distinct holes (number, par, yardage range): tee shot, hazards, club choice, green read.
3. ## Conditions & Seasonality — best months, wind/rain, pace of play, weekday vs weekend crowd.
4. ## Green Fees & Booking — JPY ranges weekday/weekend, member vs visitor policy, caddie/cart, how to book (Rakuten GORA style).
5. ## Dress Code & On-Course Rules — specific attire, mobile policy, pace expectations.
6. ## Access — nearest station, drive times from Osaka/Kobe/Hiroshima/Tokyo as relevant, parking.
7. ## Clubhouse & Dining — locker room, bath/onsen, restaurant highlights.
8. ## Caddie Tips — common mistakes, local knowledge, who this course suits (handicap/style).

[FORMATTING]
- Raw Markdown only. NO code fences. NO character-count self-check at the end.
- Start with YAML frontmatter (all values in double quotes):

---
lang: "{lang}"
title: "{name}"
lat: "{data['lat']}"
lng: "{data['lng']}"
categories: "{data['features']}"
thumbnail: "/static/images/{safe_name}.jpg"
address: "{data['address']}"
date: "{today}"
booking: "/booking/{safe_name}_{lang}"
summary: "{summary_hint(lang)}"
---
"""
