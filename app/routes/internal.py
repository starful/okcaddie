"""Internal status endpoints (not linked from any page, not in sitemaps)."""

from __future__ import annotations

import json
import os

from flask import Blueprint, abort, jsonify, request

try:
    from ..paths import BASE_DIR
except ImportError:
    from paths import BASE_DIR

internal_bp = Blueprint("internal", __name__)

REPORT_FILE = os.path.join(BASE_DIR, "..", "script", "reports", "gsc_index_status.json")


@internal_bp.route("/internal/index-status")
def index_status():
    token = os.environ.get("INTERNAL_DASHBOARD_TOKEN", "").strip()
    if not token or request.args.get("token") != token:
        abort(404)

    if not os.path.exists(REPORT_FILE):
        return jsonify({"error": "no report yet, run script/gsc_reindex_pipeline.py"}), 404

    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        report = json.load(f)

    total = report.get("total_checked", 0)
    indexed = report.get("indexed_count", 0)
    unindexed_urls = report.get("unindexed_urls", [])
    return jsonify(
        {
            "checked_at": report.get("checked_at"),
            "total_checked": total,
            "indexed_count": indexed,
            "unindexed_count": len(unindexed_urls),
            "index_rate": round(indexed / total * 100, 1) if total else 0.0,
            "last_resubmitted": report.get("last_resubmitted", False),
            "last_reindexed_count": report.get("last_reindexed_count", 0),
            "unindexed_urls": unindexed_urls,
        }
    )
