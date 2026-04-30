import os
import csv
import time
import requests
from dotenv import load_dotenv

# ==========================================
# ⚙️ 설정 — Google Places API (New) 전용
#   - 엔드포인트: https://places.googleapis.com/v1/...
#   - 키 우선순위:
#       1) Secret Manager — GOOGLE_CLOUD_PROJECT(또는 GCP_PROJECT_ID) +
#          GOOGLE_PLACES_API_KEY_SECRET_ID (시크릿 *이름*만, 예: OKCADDIE_GOOGLE_PLACES_API_KEY)
#          ADC: gcloud auth application-default login (로컬) / CI SA에 secretAccessor
#       2) 평문 폴백 — GOOGLE_PLACES_API_KEY (.env, 로컬 편의용)
# ==========================================
load_dotenv()

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.dirname(SCRIPT_DIR)
IMAGES_DIR  = os.path.join(BASE_DIR, 'app', 'static', 'images')
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')
CSV_PATH    = os.path.join(SCRIPT_DIR, 'csv', 'courses.csv')

MAX_WIDTH = 1200  # 골프장은 넓은 사진이 잘 나오므로 더 크게
PROTECTED = {'logo.png', 'logo.svg', 'favicon.ico', 'default.png', 'og_image.png'}


def _gcp_project_id() -> str:
    return (
        os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
        or os.environ.get("GCP_PROJECT_ID", "").strip()
    )


def _access_secret_latest(project_id: str, secret_id: str) -> str:
    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()


def resolve_places_api_key() -> str:
    """Places API (New) 키: Secret Manager 우선, 없으면 환경변수 평문."""
    project_id = _gcp_project_id()
    secret_id = os.environ.get("GOOGLE_PLACES_API_KEY_SECRET_ID", "").strip()

    if project_id and secret_id:
        try:
            return _access_secret_latest(project_id, secret_id)
        except Exception as e:
            print(f"❌ Secret Manager 접근 실패 ({secret_id}): {e}")
            print(
                "   프로젝트/시크릿 이름, ADC(gcloud auth application-default login), "
                "IAM secretAccessor 를 확인하세요."
            )

    direct = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    if direct:
        return direct

    return ""


def _places_error_message(res: requests.Response) -> str:
    try:
        err = res.json().get("error", {})
        return err.get("message", res.text[:200])
    except Exception:
        return res.text[:200] if res.text else str(res.status_code)


# ==========================================
# 🔍 Places API (New) — 골프장 검색
# ==========================================
def search_place(name, lat, lng, api_key: str):
    """1차: searchNearby / 2차: searchText 폴백"""

    headers_base = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.photos",
    }
    name_lower = name.lower().replace(" ", "")

    # ── 1차: Nearby Search ──
    try:
        body = {
            "includedTypes": ["golf_course", "tourist_attraction", "establishment"],
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": float(lat), "longitude": float(lng)},
                    "radius": 3000.0,
                }
            },
            "maxResultCount": 10,
            "languageCode": "ja",
        }
        res = requests.post(
            "https://places.googleapis.com/v1/places:searchNearby",
            headers=headers_base,
            json=body,
            timeout=10,
        )
        if res.status_code != 200:
            print(f"  ⚠️ searchNearby HTTP {res.status_code}: {_places_error_message(res)}")
        places = res.json().get("places", [])

        for place in places:
            display = place.get("displayName", {}).get("text", "").lower().replace(" ", "")
            if name_lower in display or display in name_lower:
                return place
        if places:
            return places[0]
    except Exception as e:
        print(f"  ⚠️ Nearby 검색 오류: {e}")

    # ── 2차: Text Search ──
    try:
        body = {
            "textQuery": f"{name} golf course Japan",
            "locationBias": {
                "circle": {
                    "center": {"latitude": float(lat), "longitude": float(lng)},
                    "radius": 5000.0,
                }
            },
            "maxResultCount": 5,
            "languageCode": "ja",
        }
        res = requests.post(
            "https://places.googleapis.com/v1/places:searchText",
            headers={
                **headers_base,
                "X-Goog-FieldMask": "places.id,places.displayName,places.photos",
            },
            json=body,
            timeout=10,
        )
        if res.status_code != 200:
            print(f"  ⚠️ searchText HTTP {res.status_code}: {_places_error_message(res)}")
        places = res.json().get("places", [])
        if places:
            print("  🔄 Text Search 폴백 성공")
            return places[0]
    except Exception as e:
        print(f"  ⚠️ Text Search 오류: {e}")

    return None


# ==========================================
# 📸 Place Photo (New)
# ==========================================
def download_photo(photo_name, save_path, api_key: str):
    url = f"https://places.googleapis.com/v1/{photo_name}/media"
    params = {
        "maxWidthPx": MAX_WIDTH,
        "key": api_key,
        "skipHttpRedirect": "false",
    }

    try:
        res = requests.get(url, params=params, timeout=15, allow_redirects=True)
        if res.status_code == 200 and res.headers.get("Content-Type", "").startswith("image"):
            with open(save_path, "wb") as f:
                f.write(res.content)
            print(f"  📥 다운로드 완료 ({len(res.content)/1024:.0f}KB)")
            return True
        print(f"  ⚠️ 응답 오류: HTTP {res.status_code} {_places_error_message(res)}")
        return False
    except Exception as e:
        print(f"  ⚠️ 다운로드 오류: {e}")
        return False


# ==========================================
# 🚀 메인 실행 (MD 파일 기준)
# ==========================================
def fetch_all_images():
    api_key = resolve_places_api_key()
    if not api_key:
        print("❌ Places API (New) 키가 없습니다.")
        print(
            "   Secret Manager: GOOGLE_CLOUD_PROJECT + GOOGLE_PLACES_API_KEY_SECRET_ID"
        )
        print("   또는 폴백: GOOGLE_PLACES_API_KEY")
        return

    os.makedirs(IMAGES_DIR, exist_ok=True)

    md_safe_names = set()
    if os.path.exists(CONTENT_DIR):
        for fname in os.listdir(CONTENT_DIR):
            if fname.endswith(".md"):
                base = fname.replace(".md", "")
                for lang in ["_ko", "_en"]:
                    if base.endswith(lang):
                        md_safe_names.add(base[: -len(lang)])
                        break

    with open(CSV_PATH, mode="r", encoding="utf-8-sig") as f:
        all_rows = list(csv.DictReader(f))

    rows = []
    for row in all_rows:
        name = (row.get("Name") or "").strip()
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
        name = (row.get("Name") or "").strip()
        lat = (row.get("Lat") or "").strip()
        lng = (row.get("Lng") or "").strip()
        if not name or not lat or not lng:
            continue

        safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "").replace("&", "and")
        save_path = os.path.join(IMAGES_DIR, f"{safe_name}.jpg")

        print(f"[{i:03d}/{total}] {name}")

        if os.path.exists(save_path) and os.path.basename(save_path) not in PROTECTED:
            print("  ⏭️  이미 존재 → 스킵")
            skipped += 1
            continue

        place = search_place(name, lat, lng, api_key)
        if not place:
            print("  ❌ 장소를 찾을 수 없음")
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
        ok = download_photo(photos[0].get("name", ""), save_path, api_key)
        if ok:
            success += 1
        else:
            failed += 1

        time.sleep(0.3)

    print("\n" + "─" * 50)
    print("🎉 이미지 수집 완료!")
    print(f"   ✅ 성공: {success}개  ⏭️  스킵: {skipped}개  ❌ 실패: {failed}개")
    print("─" * 50)


if __name__ == "__main__":
    fetch_all_images()
