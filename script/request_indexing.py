import os
import time
import xml.etree.ElementTree as ET
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
SITEMAP_INDEX = os.path.join(STATIC_DIR, "sitemap.xml")
SITEMAP_PARTS = (
    "sitemap-hub.xml",
    "sitemap-courses.xml",
    "sitemap-guides.xml",
)
KEY_FILE = os.path.join(BASE_DIR, "starful-258005-577d4eb60864.json")
ENDPOINT = "https://www.googleapis.com/auth/indexing"
SITEMAP_NS = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _urls_from_urlset(path):
    urls = []
    if not os.path.exists(path):
        return urls
    try:
        root = ET.parse(path).getroot()
        for url_tag in root.findall("ns:url", SITEMAP_NS):
            loc = url_tag.find("ns:loc", SITEMAP_NS)
            if loc is not None and loc.text:
                urls.append(loc.text.strip())
    except ET.ParseError as exc:
        print(f"❌ 사이트맵 파싱 오류 ({path}): {exc}")
    return urls


def _urls_from_sitemap_index(path):
    """sitemap index → child sitemap files → all page URLs."""
    if not os.path.exists(path):
        return []
    urls = []
    try:
        root = ET.parse(path).getroot()
        for sm in root.findall("ns:sitemap", SITEMAP_NS):
            loc = sm.find("ns:loc", SITEMAP_NS)
            if loc is None or not loc.text:
                continue
            child_url = loc.text.strip()
            if child_url.startswith("http"):
                print(f"⚠️ 원격 사이트맵은 스킵: {child_url}")
                continue
            child_name = child_url.rsplit("/", 1)[-1]
            child_path = os.path.join(STATIC_DIR, child_name)
            urls.extend(_urls_from_urlset(child_path))
    except ET.ParseError as exc:
        print(f"❌ 사이트맵 인덱스 파싱 오류: {exc}")
    return urls


def get_urls_from_sitemaps():
    """정적 사이트맵(인덱스 + 분할)에서 모든 URL을 수집합니다."""
    all_urls = []
    if os.path.exists(SITEMAP_INDEX):
        all_urls.extend(_urls_from_sitemap_index(SITEMAP_INDEX))
    for name in SITEMAP_PARTS:
        part_path = os.path.join(STATIC_DIR, name)
        all_urls.extend(_urls_from_urlset(part_path))
    # preserve order, dedupe
    seen = set()
    ordered = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


def request_indexing(priority_urls=None, daily_limit=200):
    urls = list(priority_urls or []) + [u for u in get_urls_from_sitemaps() if u not in (priority_urls or [])]
    seen = set()
    deduped = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)
    urls = deduped[:daily_limit]

    if not urls:
        print("요청할 URL이 없습니다. 먼저 'python script/build_data.py'를 실행하세요.")
        return

    print(f"🚀 총 {len(urls)}개 URL 색인 요청 (한도 {daily_limit})")

    if not os.path.exists(KEY_FILE):
        print(f"❌ 인증 키 파일이 없습니다: {KEY_FILE}")
        return

    credentials = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=[ENDPOINT])
    service = build("indexing", "v3", credentials=credentials)

    count = 0
    for url in urls:
        body = {"url": url, "type": "URL_UPDATED"}
        try:
            service.urlNotifications().publish(body=body).execute()
            count += 1
            print(f"✅ [{count}/{len(urls)}] {url}")
            time.sleep(0.5)
        except HttpError as e:
            if e.resp.status == 429:
                print("\n⚠️ 일일 할당량 초과. 24시간 후 나머지 URL을 다시 실행하세요.")
                break
            print(f"❌ [{count + 1}] 실패 {url}: {e.resp.status} {e.content.decode('utf-8')}")

    print(f"\n✨ 완료: {count}개 URL 전달")


if __name__ == "__main__":
    featured = [
        "https://okcaddie.net/course/pgm_golf_resort_okinawa",
        "https://okcaddie.net/course/hirono_golf_club",
        "https://okcaddie.net/course/yokohama_country_club",
        "https://okcaddie.net/course/shimonoseki_golf_club",
        "https://okcaddie.net/course/natsudomari_golf_links",
        "https://okcaddie.net/course/hakone_country_club",
        "https://okcaddie.net/course/abc_golf_club",
        "https://okcaddie.net/course/eniwa_country_club",
        "https://okcaddie.net/course/totsuka_country_club",
        "https://okcaddie.net/course/kotohira_golf_club",
        "https://okcaddie.net/",
        "https://okcaddie.net/courses",
    ]
    request_indexing(priority_urls=featured)
