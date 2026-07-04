#!/usr/bin/env python3
"""CLI: validate course/guide frontmatter lang vs title/seo fields."""

from __future__ import annotations

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "app"))

from frontmatter_validate import collect_violations  # noqa: E402


def main() -> int:
    violations = collect_violations()
    if not violations:
        print("OK: no frontmatter violations")
        return 0
    for path, errs in violations:
        for err in errs:
            print(f"{path}: {err}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
