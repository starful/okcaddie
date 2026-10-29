"""Weekly GSC index-coverage check + sitemap resubmission pipeline.

Run via cron (weekly): python script/gsc_reindex_pipeline.py
Requires the same service account key as request_indexing.py, added as a
"Full" user on the Search Console property (needed for sitemaps.submit).

Flow: inspect every sitemap URL through the URL Inspection API, record
indexed/unindexed status, and if the sitemap files changed since the last
run (or new unindexed URLs showed up) resubmit the sitemap to Search Console
and ask the Indexing API to recrawl the unindexed URLs.
"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

try:
    from request_indexing import (
        KEY_FILE,
        SITEMAP_INDEX,
        SITEMAP_PARTS,
        STATIC_DIR,
        get_urls_from_sitemaps,
        request_indexing,
    )
except ImportError:
    from script.request_indexing import (
        KEY_FILE,
        SITEMAP_INDEX,
        SITEMAP_PARTS,
        STATIC_DIR,
        get_urls_from_sitemaps,
        request_indexing,
    )

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(SCRIPT_DIR, "reports")
REPORT_FILE = os.path.join(REPORT_DIR, "gsc_index_status.json")

SITE_URL = os.environ.get("SITE_URL", "https://okcaddie.net").rstrip("/")
# Search Console property identifier (url-prefix, e.g. "https://okcaddie.net/",
# or a domain property "sc-domain:okcaddie.net"). Override if the verified
# property differs from the url-prefix default.
GSC_SITE_URL = os.environ.get("GSC_SITE_URL", f"{SITE_URL}/")
WEBMASTERS_SCOPE = "https://www.googleapis.com/auth/webmasters"

# URL Inspection quota is 2000/day, 600/min — stay well under both.
INSPECT_LIMIT = int(os.environ.get("GSC_INSPECT_LIMIT", "600"))
INSPECT_SLEEP_SECONDS = 0.3
# Keep reindex requests small; the Indexing API quota is separate from GSC.
REINDEX_LIMIT = int(os.environ.get("GSC_REINDEX_LIMIT", "100"))


def sitemap_fingerprint():
    paths = [SITEMAP_INDEX] + [os.path.join(STATIC_DIR, name) for name in SITEMAP_PARTS]
    digest = hashlib.md5()
    for path in paths:
        if os.path.exists(path):
            with open(path, "rb") as f:
                digest.update(f.read())
    return digest.hexdigest()


def load_previous_report():
    if not os.path.exists(REPORT_FILE):
        return {}
    try:
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_report(report):
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def build_search_console_service():
    if not os.path.exists(KEY_FILE):
        print(f"❌ 인증 키 파일이 없습니다: {KEY_FILE}")
        return None
    credentials = service_account.Credentials.from_service_account_file(
        KEY_FILE, scopes=[WEBMASTERS_SCOPE]
    )
    return build("searchconsole", "v1", credentials=credentials)


def inspect_urls(service, urls):
    """Returns {url: {"verdict": str, "coverageState": str}}."""
    results = {}
    for i, url in enumerate(urls[:INSPECT_LIMIT], start=1):
        try:
            resp = (
                service.urlInspection()
                .index()
                .inspect(body={"inspectionUrl": url, "siteUrl": GSC_SITE_URL})
                .execute()
            )
            status = resp.get("inspectionResult", {}).get("indexStatusResult", {})
            results[url] = {
                "verdict": status.get("verdict", "UNKNOWN"),
                "coverageState": status.get("coverageState", ""),
            }
            print(f"🔎 [{i}/{min(len(urls), INSPECT_LIMIT)}] {results[url]['verdict']} {url}")
        except HttpError as e:
            print(f"❌ 검사 실패 {url}: {e.resp.status}")
            results[url] = {"verdict": "ERROR", "coverageState": ""}
        time.sleep(INSPECT_SLEEP_SECONDS)
    return results


def resubmit_sitemap(service):
    try:
        service.sitemaps().submit(
            siteUrl=GSC_SITE_URL, feedpath=f"{SITE_URL}/sitemap.xml"
        ).execute()
        print(f"📤 사이트맵 재제출 완료: {SITE_URL}/sitemap.xml")
        return True
    except HttpError as e:
        print(f"❌ 사이트맵 재제출 실패: {e.resp.status} {e.content.decode('utf-8')}")
        return False


def print_dashboard(status, sitemap_changed, resubmitted, reindexed_count):
    total = len(status)
    indexed = [u for u, info in status.items() if info["verdict"] == "PASS"]
    unindexed = [u for u, info in status.items() if info["verdict"] != "PASS"]
    rate = (len(indexed) / total * 100) if total else 0.0

    print("\n========== 색인 상태 대시보드 ==========")
    print(f"검사 URL: {total}개 | 색인됨: {len(indexed)}개 ({rate:.1f}%) | 미색인: {len(unindexed)}개")
    print(f"사이트맵 변경 감지: {'예' if sitemap_changed else '아니오'} | 재제출: {'완료' if resubmitted else '없음'}")
    print(f"재색인 요청: {reindexed_count}개")
    if unindexed:
        print("\n미색인 URL (상위 20개):")
        for u in unindexed[:20]:
            print(f"  - [{status[u]['coverageState'] or status[u]['verdict']}] {u}")
    print("=========================================\n")


def run():
    urls = get_urls_from_sitemaps()
    if not urls:
        print("검사할 URL이 없습니다. 먼저 'python script/build_data.py'를 실행하세요.")
        return

    previous = load_previous_report()
    current_fingerprint = sitemap_fingerprint()
    sitemap_changed = current_fingerprint != previous.get("sitemap_fingerprint")

    service = build_search_console_service()
    if service is None:
        return

    status = inspect_urls(service, urls)
    unindexed_urls = [u for u, info in status.items() if info["verdict"] != "PASS"]

    resubmitted = False
    reindexed_count = 0
    if sitemap_changed or unindexed_urls:
        resubmitted = resubmit_sitemap(service)
        if unindexed_urls:
            request_indexing(priority_urls=unindexed_urls, daily_limit=REINDEX_LIMIT)
            reindexed_count = min(len(unindexed_urls), REINDEX_LIMIT)

    print_dashboard(status, sitemap_changed, resubmitted, reindexed_count)

    save_report(
        {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "sitemap_fingerprint": current_fingerprint,
            "total_checked": len(status),
            "indexed_count": sum(1 for info in status.values() if info["verdict"] == "PASS"),
            "unindexed_urls": unindexed_urls,
            "status": status,
            "last_resubmitted": resubmitted,
            "last_reindexed_count": reindexed_count,
        }
    )


if __name__ == "__main__":
    run()
