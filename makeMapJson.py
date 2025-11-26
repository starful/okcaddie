# makeMapJson.py
import os
import json
import googlemaps
from google.cloud import storage
from hatena_client import get_all_posts
from datetime import datetime # [추가됨] 날짜 기능

# 환경 변수
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY') 
BUCKET_NAME = "jinjamap-data"
FILE_NAME = "shrines_data.json"

def load_existing_data(bucket):
    try:
        blob = bucket.blob(FILE_NAME)
        if not blob.exists():
            return {}
        
        data_str = blob.download_as_text()
        json_data = json.loads(data_str)
        
        # [수정됨] 기존 데이터가 리스트인지 딕셔너리인지 확인하여 호환성 유지
        existing_list = json_data.get('shrines', []) if isinstance(json_data, dict) else json_data
        
        coord_cache = {}
        for item in existing_list:
            if 'address' in item and 'lat' in item and 'lng' in item:
                coord_cache[item['address']] = {'lat': item['lat'], 'lng': item['lng']}
        
        print(f"📦 기존 데이터 {len(coord_cache)}개를 캐시로 로드했습니다.")
        return coord_cache

    except Exception as e:
        print(f"⚠️ 기존 데이터 로드 중 오류 발생 (무시하고 진행): {e}")
        return {}

def main():
    print("🔥 데이터 갱신 스크립트 시작...")

    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    coord_cache = load_existing_data(bucket)

    posts = get_all_posts()
    if not posts:
        print("❌ 글을 가져오지 못했습니다.")
        return

    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    processed_posts = []
    
    for post in posts:
        address = post.get('address')
        if not address: continue
        
        if address in coord_cache:
            post['lat'] = coord_cache[address]['lat']
            post['lng'] = coord_cache[address]['lng']
            processed_posts.append(post)
        else:
            try:
                geocode_result = gmaps.geocode(address)
                if geocode_result:
                    location = geocode_result[0]['geometry']['location']
                    post['lat'] = location['lat']
                    post['lng'] = location['lng']
                    processed_posts.append(post)
                    print(f"  📍 좌표 변환: {post['title']}")
            except Exception as e:
                print(f"  ❌ API 에러: {e}")

    # [수정됨] 날짜와 데이터를 함께 저장하는 구조로 변경
    final_data = {
        "last_updated": datetime.now().strftime("%Y.%m.%d"),
        "shrines": processed_posts
    }

    try:
        blob = bucket.blob(FILE_NAME)
        blob.upload_from_string(
            json.dumps(final_data, ensure_ascii=False),
            content_type='application/json'
        )
        print(f"💾 저장 완료 (총 {len(processed_posts)}개) - 날짜 포함")

    except Exception as e:
        print(f"❌ GCS 업로드 실패: {e}")
        exit(1)

if __name__ == "__main__":
    main()