# app.py
from flask import Flask, jsonify, send_from_directory
from google.cloud import storage
import json
import os
import time

# [중요] Flask 앱 객체 생성은 반드시 라우트(@app.route)보다 위에 있어야 합니다.
app = Flask(__name__, static_url_path='/assets', static_folder='assets', template_folder='.')

# 설정 변수
BUCKET_NAME = "jinjamap-data" 
FILE_NAME = "shrines_data.json"

# 캐싱을 위한 전역 변수
cache_data = None
last_fetch_time = 0
CACHE_DURATION = 3600  # 1시간 (초 단위)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/shrines')
def api_shrines():
    global cache_data, last_fetch_time
    
    current_time = time.time()

    # 1. 캐시가 있고, 아직 유효 시간(1시간)이 안 지났으면 캐시 데이터 반환
    if cache_data and (current_time - last_fetch_time < CACHE_DURATION):
        print("✅ 캐시된 데이터를 반환합니다.")
        return jsonify(cache_data)

    # 2. 캐시가 없거나 만료되었으면 GCS에서 새로 가져옴
    try:
        print("📥 GCS에서 데이터를 다운로드합니다...")
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(FILE_NAME)
        
        data_str = blob.download_as_text()
        json_data = json.loads(data_str)
        
        # 데이터 캐싱 업데이트
        cache_data = json_data
        last_fetch_time = current_time
        
        return jsonify(json_data)
        
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        # 실패 시 기존 캐시가 있다면 반환, 아니면 빈 리스트 반환
        return jsonify(cache_data if cache_data else []), 200

# 로컬 테스트용 실행 코드
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)