import os
import time
import xml.etree.ElementTree as ET
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================
KEY_FILE = "starful-258005-577d4eb60864.json"      # 아까 다운로드한 키 파일
SITEMAP_PATH = "app/static/sitemap.xml"    # build_data.py로 생성된 사이트맵 경로
ENDPOINT = "https://www.googleapis.com/auth/indexing"

def get_urls_from_sitemap():
    """사이트맵 파일에서 모든 URL 리스트를 추출합니다."""
    urls = []
    if not os.path.exists(SITEMAP_PATH):
        print(f"❌ 사이트맵이 없습니다: {SITEMAP_PATH}")
        print("먼저 'python script/build_data.py'를 실행하여 사이트맵을 생성하세요.")
        return urls

    try:
        tree = ET.parse(SITEMAP_PATH)
        root = tree.getroot()
        # 사이트맵 네임스페이스 처리 (표준 sitemap.org 형식)
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        for url_tag in root.findall('ns:url', ns):
            loc = url_tag.find('ns:loc', ns).text
            if loc:
                urls.append(loc)
    except Exception as e:
        print(f"❌ 사이트맵 분석 중 오류 발생: {e}")
    
    return urls

def request_indexing():
    # 1. URL 수집
    urls = get_urls_from_sitemap()
    if not urls:
        print("요청할 URL이 없습니다.")
        return

    print(f"🚀 총 {len(urls)}개의 URL에 대해 색인 요청을 시작합니다.")

    # 2. 구글 인증 정보 로드
    if not os.path.exists(KEY_FILE):
        print(f"❌ 인증 키 파일이 없습니다: {KEY_FILE}")
        return

    credentials = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=[ENDPOINT])
    service = build("indexing", "v3", credentials=credentials)

    # 3. 루프를 돌며 API 호출
    count = 0
    for url in urls:
        body = {
            "url": url,
            "type": "URL_UPDATED"  # 새 주소 추가 및 기존 주소 갱신 모두 이 타입 사용
        }
        
        try:
            # 구글 서버에 알림 전송
            service.urlNotifications().publish(body=body).execute()
            print(f"✅ [{count+1}/{len(urls)}] 요청 성공: {url}")
            count += 1
            # 할당량 초과 방지 및 서버 부하를 위한 아주 짧은 대기
            time.sleep(0.5) 
        except HttpError as e:
            error_data = e.content.decode('utf-8')
            if e.resp.status == 429:
                print(f"\n⚠️ 일일 할당량(보통 200개)을 초과했습니다.")
                print("나머지 URL은 24시간 후에 다시 실행하세요.")
                break
            else:
                print(f"❌ [{count+1}] 요청 실패: {url} -> {e.resp.status} : {error_data}")

    print(f"\n✨ 작업 완료! 총 {count}개의 URL을 구글 봇에게 전달했습니다.")

if __name__ == "__main__":
    request_indexing()