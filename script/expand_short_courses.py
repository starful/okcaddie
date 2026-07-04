#!/usr/bin/env python3
"""Re-expand compact course pages (~3–5k chars) to medium depth (~6–9k EN / ~5–8k KO)."""
import os
import re
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
    LANG_FULL,
    _strip_selfcheck,
    _dedupe_h2,
)
from text_utils import humanize_title  # noqa: E402

# GSC / recent compact batch (EN body < 6,000 chars)
SHORT_BASE_IDS = [
    "seto_inland_sea_golf",
    "okayama_country_club",
    "hanshin_public_golf",
    "takarazuka_golf_club",
    "hiroshima_kokusai_golf",
    "takamatsu_country_club",
    "hiroshima_country_club",
    "okayama_royal_golf",
    "kobe_grand_hill",
    "sanda_golf_club",
]

SEO_KEYS = ("seo_title", "seo_description")


def build_prompt_medium(data):
    lang = data["lang"]
    lang_full = LANG_FULL.get(lang, "English")
    name = data["name"]
    today = data.get("date") or time.strftime("%Y-%m-%d")

    summary_hint = (
        "Provide a concrete 1-sentence summary in Korean (<=140 chars) with a numeric or location detail."
        if lang == "ko"
        else "Provide a concrete 1-sentence summary in English (<=155 chars) with a numeric or location detail."
    )

    length_target = (
        "5,500 to 8,500 characters" if lang == "ko" else "6,000 to 9,000 characters"
    )

    return f"""You are a senior Japan golf travel writer for OKCaddie.
Write in {lang_full}. Be specific and useful for trip planning. Avoid generic praise and filler.

Course: {name}
Address: {data['address']}
Coordinates: {data['lat']}, {data['lng']}
Tags: {data['features']}

[GOAL]
- Total length: {length_target} (substantive paragraphs, not bullet-only lists).
- 3-4 sentences per major section where appropriate.
- Use H2 (##) only. Use 7 to 8 H2 sections in the order below.
- Do NOT use: "world-class", "unforgettable", "must-visit", "Definitive Guide", "Expert Review", "masterpiece".
- Use realistic ranges for yardage/green fees when exact data is uncertain.
- Do NOT invent phone numbers or URLs.

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
thumbnail: "/static/images/{data['safe_name']}.jpg"
address: "{data['address']}"
date: "{today}"
booking: "/booking/{data['safe_name']}_{lang}"
summary: "{summary_hint}"
---
"""


def load_course_data(base_id, lang):
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


def generate_medium(data):
    safe_name = data["safe_name"]
    lang = data["lang"]
    filepath = os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md")
    prompt = build_prompt_medium(data)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    content = response.text.strip()
    content = re.sub(r"^```markdown\s*", "", content)
    content = re.sub(r"^```yaml\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    content = content.replace("## yaml", "").strip()
    content = re.sub(
        r'^(title:\s*"[^"]*?)\s*\(\s*(?:en|ko|EN|KO)\s*\)\s*"',
        r"\1\"",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    content = _strip_selfcheck(content)
    content = _dedupe_h2(content)

    # Re-inject SEO overrides after regeneration
    if data.get("seo"):
        post = frontmatter.loads(content)
        for k, v in data["seo"].items():
            post[k] = v
        content = frontmatter.dumps(post)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    body_len = len(frontmatter.loads(content).content)
    return body_len


def main():
    bases = SHORT_BASE_IDS
    if len(sys.argv) > 1:
        bases = [b.strip() for b in sys.argv[1].split(",") if b.strip()]

    print(f"📝 Medium expand: {len(bases)} courses × 2 languages\n")
    for base_id in bases:
        for lang in ("en", "ko"):
            data = load_course_data(base_id, lang)
            if not data:
                print(f"  ⏭️  skip missing: {base_id}_{lang}")
                continue
            try:
                n = generate_medium(data)
                print(f"  ✅ {base_id}_{lang} → {n:,} chars body")
            except Exception as e:
                print(f"  ❌ {base_id}_{lang}: {e}")
            time.sleep(0.5)
    print("\n✨ Done. Run: python script/build_data.py")


if __name__ == "__main__":
    main()
