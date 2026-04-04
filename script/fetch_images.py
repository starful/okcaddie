import os
import csv
import time
import requests
from dotenv import load_dotenv

# ==========================================
# ⚙️ 설정
# ==========================================
load_dotenv()
API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.dirname(SCRIPT_DIR)
IMAGES_DIR  = os.path.join(BASE_DIR, 'app', 'static', 'images')
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')
CSV_PATH    = os.path.join(SCRIPT_DIR, 'csv', 'courses.csv')

MAX_WIDTH = 1200  # 골프장은 넓은 사진이 잘 나오므로 더 크게
PROTECTED = {'logo.png', 'logo.svg', 'favicon.ico', 'default.png', 'og_image.png'}

# ==========================================
# 🔍 Places API — 골프장 검색
# ==========================================
def search_place(name, lat, lng):
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.photos"
    }
    body = {
        "includedTypes": ["golf_course"],
        "locationRestriction": {
            "circle": {
                "center": {"latitude": float(lat), "longitude": float(lng)},
                "radius": 1000.0  # 골프장은 넓으므로 1km 반경
            }
        },
        "maxResultCount": 5,
        "languageCode": "ja"
    }

    try:
        res = requests.post(url, headers=headers, json=body, timeout=10)
        data = res.json()
        places = data.get("places", [])
        if not places:
            return None

        name_lower = name.lower().replace(" ", "")
        for place in places:
            display = place.get("displayName", {}).get("text", "").lower().replace(" ", "")
            if name_lower in display or display in name_lower:
                return place
        return places[0]

    except Exception as e:
        print(f"  ⚠️ 검색 오류 ({name}): {e}")
        return None


# ==========================================
# 📸 사진 다운로드
# ==========================================
def download_photo(photo_name, save_path):
    url = f"https://places.googleapis.com/v1/{photo_name}/media"
    params = {
        "maxWidthPx": MAX_WIDTH,
        "key": API_KEY,
        "skipHttpRedirect": "false"
    }

    try:
        res = requests.get(url, params=params, timeout=15, allow_redirects=True)
        if res.status_code == 200 and res.headers.get("Content-Type", "").startswith("image"):
            with open(save_path, "wb") as f:
                f.write(res.content)
            print(f"  📥 다운로드 완료 ({len(res.content)/1024:.0f}KB)")
            return True
        else:
            print(f"  ⚠️ 응답 오류: HTTP {res.status_code}")
            return False
    except Exception as e:
        print(f"  ⚠️ 다운로드 오류: {e}")
        return False


# ==========================================
# 🚀 메인 실행 (MD 파일 기준)
# ==========================================
def fetch_all_images():
    if not API_KEY:
        print("❌ GOOGLE_PLACES_API_KEY가 없습니다.")
        return

    os.makedirs(IMAGES_DIR, exist_ok=True)

    # MD 파일 기준 safe_name 추출
    md_safe_names = set()
    if os.path.exists(CONTENT_DIR):
        for fname in os.listdir(CONTENT_DIR):
            if fname.endswith('.md'):
                base = fname.replace('.md', '')
                for lang in ['_ko', '_en']:
                    if base.endswith(lang):
                        md_safe_names.add(base[:-len(lang)])
                        break

    # CSV에서 MD가 있는 골프장만 필터링
    with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
        all_rows = list(csv.DictReader(f))

    rows = []
    for row in all_rows:
        name = (row.get('Name') or '').strip()
        if not name:
            continue
        safe = name.lower().replace(" ", "_").replace("'", "").replace(",", "").replace("&", "and")
        if safe in md_safe_names:
            rows.append(row)

    total = len(rows)
    print(f"\n⛳  MD 기준 총 {total}개 골프장 이미지 확인...")
    print(f"   (전체 CSV {len(all_rows)}개 중 컨텐츠 있는 {total}개만 처리)\n")

    success = skipped = failed = 0

    for i, row in enumerate(rows, 1):
        name = (row.get('Name') or '').strip()
        lat  = (row.get('Lat') or '').strip()
        lng  = (row.get('Lng') or '').strip()
        if not name or not lat or not lng:
            continue

        safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "").replace("&", "and")
        save_path = os.path.join(IMAGES_DIR, f"{safe_name}.jpg")

        print(f"[{i:03d}/{total}] {name}")

        if os.path.exists(save_path) and os.path.basename(save_path) not in PROTECTED:
            print(f"  ⏭️  이미 존재 → 스킵")
            skipped += 1
            continue

        place = search_place(name, lat, lng)
        if not place:
            print(f"  ❌ 장소를 찾을 수 없음")
            failed += 1
            time.sleep(0.3)
            continue

        place_name = place.get("displayName", {}).get("text", "?")
        photos = place.get("photos", [])
        if not photos:
            print(f"  ❌ 사진 없음 (장소: {place_name})")
            failed += 1
            time.sleep(0.3)
            continue

        print(f"  🔍 장소: {place_name}")
        ok = download_photo(photos[0].get("name", ""), save_path)
        if ok: success += 1
        else:  failed  += 1

        time.sleep(0.3)

    print("\n" + "─" * 50)
    print(f"🎉 이미지 수집 완료!")
    print(f"   ✅ 성공: {success}개  ⏭️  스킵: {skipped}개  ❌ 실패: {failed}개")
    print("─" * 50)


if __name__ == "__main__":
    fetch_all_images()
