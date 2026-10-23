#!/usr/bin/env python3
"""CLI: check detail-page hreflang alternates match sitemap-courses/guides.xml."""

from __future__ import annotations

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "app"))

from hreflang_validate import collect_hreflang_mismatches  # noqa: E402


def main() -> int:
    errors = collect_hreflang_mismatches()
    if not errors:
        print("OK: hreflang alternates match sitemap-courses.xml / sitemap-guides.xml")
        return 0
    for err in errors:
        print(err)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
