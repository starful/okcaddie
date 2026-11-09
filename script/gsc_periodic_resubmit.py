"""Periodic resubmission of unindexed URLs via the Indexing API.

Run via cron more often than the full pipeline (e.g. daily):
    python script/gsc_periodic_resubmit.py

Unlike gsc_reindex_pipeline.py, this does not re-run the URL Inspection
check (which has a tight daily quota). It just reads the unindexed_urls
list from the report file that app/routes/internal.py's /internal/index-status
endpoint serves, and re-asks the Indexing API to crawl them.
"""

import json
import os
from datetime import datetime, timezone

try:
    from request_indexing import request_indexing
except ImportError:
    from script.request_indexing import request_indexing

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_FILE = os.path.join(SCRIPT_DIR, "reports", "gsc_index_status.json")

# Keep well under the Indexing API's daily quota, spread across multiple runs.
REINDEX_LIMIT = int(os.environ.get("GSC_PERIODIC_REINDEX_LIMIT", "100"))


def load_report():
    if not os.path.exists(REPORT_FILE):
        return None
    try:
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_report(report):
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def run():
    report = load_report()
    if report is None:
        print("보고서가 없습니다. 먼저 'python script/gsc_reindex_pipeline.py'를 실행하세요.")
        return

    unindexed_urls = report.get("unindexed_urls", [])
    if not unindexed_urls:
        print("미색인 URL이 없습니다. 재제출을 건너뜁니다.")
        return

    resubmit_count = min(len(unindexed_urls), REINDEX_LIMIT)
    print(f"🔁 미색인 URL {len(unindexed_urls)}개 중 최대 {resubmit_count}개 재제출")
    request_indexing(priority_urls=unindexed_urls, daily_limit=REINDEX_LIMIT)

    report["last_periodic_resubmit_at"] = datetime.now(timezone.utc).isoformat()
    report["last_periodic_resubmit_count"] = resubmit_count
    save_report(report)


if __name__ == "__main__":
    run()
