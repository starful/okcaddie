"""Shared Gemini prompts and body-length thresholds for course markdown."""

from __future__ import annotations

from datetime import datetime

# Practical pages beat padded masterclass prose (see 2026-07 content cleanup).
MIN_BODY_CHARS = 3000

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
    return "3,000 to 6,500 characters" if lang == "ko" else "3,500 to 7,000 characters"


def summary_hint(lang: str) -> str:
    if lang == "ko":
        return "예약·요금·접근이 드러나는 구체적 한 문장 요약(<=140자)."
    return "One concrete sentence (<=155 chars) mentioning booking, fees, or access."


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
    """Practical visitor course profile (booking / fees / access first)."""
    lang = data["lang"]
    lang_full = LANG_FULL.get(lang, "English")
    safe_name = data["safe_name"]
    name = data["name"]
    today = today or data.get("date") or datetime.now().strftime("%Y-%m-%d")
    facts = known_facts_block(data)

    return f"""You are a practical Japan golf travel editor for OKCaddie.
Write in {lang_full}. Trip-planning first. No ornate caddy monologue.

Course: {name}
Address: {data['address']}
Coordinates: {data['lat']}, {data['lng']}
Tags: {data['features']}{facts}

[HARD RULES]
- Total length: {length_target(lang)}. Minimum body after frontmatter: {MIN_BODY_CHARS} characters.
- Use H2 (##) only. 7 sections in the EXACT order below.
- Do NOT use: "world-class", "unforgettable", "must-visit", "Definitive Guide", "Expert Review",
  "masterpiece", "as an elite", "two decades", "Historical Prestige", "Hole-by-Hole Masterclass",
  "symphony of", "character-by-character", "unforgettable pilgrimage", "20년 경력", "마스터피스".
- Do NOT invent exact hole-by-hole yardages, stimpmeter readings, or phone numbers.
  Only use hole numbers / designer / fees when present in KNOWN FACTS; otherwise speak in ranges and character.
- Be honest about visitor access (public vs private / introduction). Prefer "verify live quote" over fake exact yen.
- Link booking as markdown: [/booking/{safe_name}_{lang}](/booking/{safe_name}_{lang})

[SECTIONS — IN THIS ORDER]
1. ## Quick Facts — compact bullets or a 2-column markdown table: location, holes/style if known, visitor access, best for, best season.
2. ## Who This Course Is For — 3 bullets for fits + 1 to 2 for skips.
3. ## Course Overview — layout character, turf tendencies, wind/elevation; no fake hole novels.
4. ## Green Fees & Booking — weekday/weekend JPY ranges as estimates, what packages usually include, how visitors book (Rakuten GORA / hotel). Always say fees move with season.
5. ## Access — nearest airport/station, typical drive times from relevant hubs, car vs taxi reality.
6. ## Dress Code & Tips — attire, soft spikes, pace, 3 practical tips.
7. ## Bottom Line — 2 to 3 sentences: who should book this and the first next action.

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
seo_title: "Write a practical SEO title with booking or fees angle (<=60 chars)"
seo_description: "Write a practical meta description with location + booking cue (<=155 chars)"
---
"""
