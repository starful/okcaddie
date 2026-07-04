"""Filesystem paths relative to the Flask app package."""

from __future__ import annotations

import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = APP_DIR
STATIC_DIR = os.path.join(BASE_DIR, "static")
CONTENT_DIR = os.path.join(BASE_DIR, "content")
GUIDE_DIR = os.path.join(CONTENT_DIR, "guides")
DATA_FILE = os.path.join(STATIC_DIR, "json", "courses_data.json")
