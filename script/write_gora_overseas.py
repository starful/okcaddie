"""Write EN/KO/JA markdown for GORA overseas catalog courses."""

from __future__ import annotations

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
APP_DIR = os.path.join(BASE_DIR, "app")
CONTENT_DIR = os.path.join(APP_DIR, "content")
sys.path.insert(0, APP_DIR)

from gora_overseas import OVERSEAS_COURSES, THUMBNAILS  # noqa: E402

DATE = "2026-09-15"
DEFAULT_LANGS = ("en", "ko", "ja")


def _yaml_str(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def _body(*, lang: str, row: dict) -> str:
    title = row["title"]
    address = row["address"]
    if lang == "ja":
        airport = row.get("airport_ja") or row["airport"]
        note = row.get("note_ja") or row["note_en"]
        season = row.get("season_ja") or row["season_en"]
        return f"""{title}は{address}にあるゴルフ場です。{note}

## ひと目で

| | |
|---|---|
| **場所** | {address} |
| **空港** | {airport} |
| **予約** | 楽天GORA 海外 |

このページは日本国内コースではありません。下のボタンはGORA海外予約（当該コース）へ進みます。

## グリーンフィー・予約

料金とティータイムは季節・曜日・パッケージで変わります。ページ下の **楽天GORAで予約** から当該コースのリアルタイムプランを確認してください。決済画面は楽天GORA（日本アカウント）基準です。

レンタルクラブ・キャディ・カート込みかはGORAプラン説明で再確認してください。

## アクセス

- **空港から**: {airport}
- ティータイム基準で移動バッファを入れてください。リゾートシャトルがある場合はホテルに先に確認した方が安心です。

## 服装・Tips

- 襟付きシャツ、ソフトスパイク
- 熱帯コースでは紫外線・水分補給が日本本土より重要です

## シーズン

{season}

数字は計画用です。出発前にGORAでライブ見積もりを確認してください。
"""
    if lang == "ko":
        note = row["note_ko"]
        season = row["season_ko"]
        airport = row["airport"]
        return f"""{title}는 {address}에 있는 골프장입니다. {note}

## 한눈에

| | |
|---|---|
| **위치** | {address} |
| **공항** | {airport} |
| **예약** | 라쿠텐 GORA 해외 |

이 페이지는 일본 코스가 아닙니다. 아래 버튼은 GORA 해외 예약(해당 코스)으로 갑니다.

## 그린피·예약

그린피와 티타임은 시즌·요일·패키지에 따라 바뀝니다. 페이지 하단 **라쿠텐에서 골프 예약하기**로 해당 코스의 실시간 플랜을 확인하세요. 결제 화면은 라쿠텐 일본 계정 기준입니다.

렌탈 클럽·캐디·카트 포함 여부는 GORA 플랜 설명에서 다시 보세요.

## 가는 법

- **공항에서**: {airport}
- 티타임 기준으로 이동 버퍼를 넣으세요. 리조트 셔틀이 있으면 호텔에 먼저 확인하는 편이 낫습니다.

## 복장·팁

- 칼라 셔츠, 골프화(소프트 스파이크)
- 열대 코스는 자외선·수분 보충이 일본 본토보다 중요합니다

## 시즌

{season}

숫자는 계획용입니다. 출발 전 GORA에서 라이브 견적을 확인하세요.
"""
    note = row["note_en"]
    season = row["season_en"]
    airport = row["airport"]
    return f"""{title} is in {address}. {note}

## Quick facts

| | |
|---|---|
| **Location** | {address} |
| **Airport** | {airport} |
| **Booking** | Rakuten GORA overseas |

This is not a Japan course. The booking button below opens this club on GORA overseas — not the Japan prefecture search.

## Green fees & booking

Fees move with season, day of week, and package. Use **Check on Rakuten GORA** on this page for the live plan. Checkout is the Japanese Rakuten GORA flow.

Re-check rental clubs, caddie, and cart inclusion on the GORA plan before you pay.

## Access

- **From the airport**: {airport}
- Build buffer before the tee time. If a resort shuttle exists, confirm it with the hotel first.

## Dress & tips

- Collared shirt, soft spikes
- On tropical courses, sun and water matter more than they do on Honshu

## Season

{season}

Treat any number here as planning only. Verify the live quote on GORA before you travel.
"""


def write_course(row: dict, lang: str, thumb: str) -> str:
    slug = row["slug"]
    course_id = f"{slug}_{lang}"
    title = row["title"]
    if lang == "ko":
        summary = f"{row['address']} {title}. 라쿠텐 GORA 해외에서 티타임 확인."
        seo_title = f"{title} 그린피·예약"
        seo_desc = f"{row['address']} {title} 그린피, 공항 접근, 라쿠텐 GORA 해외 예약."
    elif lang == "ja":
        summary = f"{address_ja(row)}の{title}。楽天GORA海外でティータイム確認。"
        seo_title = f"{title} グリーンフィー・予約"
        seo_desc = f"{row['address']} {title}のグリーンフィー、空港アクセス、楽天GORA海外予約。"
    else:
        summary = f"{title} in {row['address']}. Check live tee times on Rakuten GORA overseas."
        seo_title = f"{title}: Fees & Booking"
        seo_desc = f"Green fees, access, and Rakuten GORA overseas booking for {title} in {row['address']}."

    fm = "\n".join(
        [
            "---",
            f"lang: {lang}",
            f"title: {_yaml_str(title)}",
            f"lat: {_yaml_str(row['lat'])}",
            f"lng: {_yaml_str(row['lng'])}",
            f"categories: {_yaml_str(row['categories'])}",
            f"thumbnail: {_yaml_str(thumb)}",
            f"address: {_yaml_str(row['address'])}",
            f"date: '{DATE}'",
            f"booking: /booking/{course_id}",
            f"country: {row['country']}",
            f"gora_cid: {_yaml_str(row['gora_cid'])}",
            f"summary: {_yaml_str(summary)}",
            f"seo_title: {_yaml_str(seo_title)}",
            f"seo_description: {_yaml_str(seo_desc)}",
            "---",
            "",
        ]
    )
    path = os.path.join(CONTENT_DIR, f"{course_id}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(fm + _body(lang=lang, row=row).strip() + "\n")
    return path


def address_ja(row: dict) -> str:
    return row["address"]


def main() -> None:
    langs = DEFAULT_LANGS
    if len(sys.argv) > 1:
        langs = tuple(a.strip() for a in sys.argv[1].split(",") if a.strip())
    os.makedirs(CONTENT_DIR, exist_ok=True)
    written = []
    for i, row in enumerate(OVERSEAS_COURSES):
        thumb = THUMBNAILS[i % len(THUMBNAILS)]
        for lang in langs:
            written.append(write_course(row, lang, thumb))
    print(f"wrote {len(written)} files ({','.join(langs)})")


if __name__ == "__main__":
    main()
