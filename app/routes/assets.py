"""Static assets, favicons, social OG images."""

from __future__ import annotations

import io
import os
import re
import urllib.request

from flask import Blueprint, Response, abort, redirect, request, send_from_directory

try:
    from ..paths import STATIC_DIR
    from ..view_helpers import gcs_image_url, jpeg_bytes
except ImportError:
    from paths import STATIC_DIR
    from view_helpers import gcs_image_url, jpeg_bytes

assets_bp = Blueprint("assets", __name__)


@assets_bp.route("/favicon.ico")
@assets_bp.route("/favicon-32x32.png")
@assets_bp.route("/favicon-48x48.png")
@assets_bp.route("/apple-touch-icon.png")
@assets_bp.route("/android-chrome-192x192.png")
@assets_bp.route("/android-chrome-512x512.png")
def serve_favicons():
    from flask import current_app

    image_dir = os.path.join(current_app.root_path, "static", "images")
    filename = request.path[1:]
    if filename == "favicon.ico" and not os.path.exists(os.path.join(image_dir, filename)):
        filename = "favicons.ico"
    return send_from_directory(
        image_dir,
        filename,
        mimetype="image/png" if filename.endswith(".png") else "image/vnd.microsoft.icon",
    )


@assets_bp.route("/site.webmanifest")
def webmanifest():
    return send_from_directory(STATIC_DIR, "site.webmanifest", mimetype="application/manifest+json")


@assets_bp.route("/social/<slug>.jpg")
def social_image(slug):
    safe = re.sub(r"[^a-z0-9_-]", "", slug.lower())
    if not safe:
        abort(404)
    gcs_url = gcs_image_url(f"{safe}.jpg")
    try:
        with urllib.request.urlopen(gcs_url, timeout=15) as resp:
            raw = resp.read()
            if not raw:
                abort(404)
    except Exception:
        abort(404)

    try:
        from PIL import Image, ImageOps

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        data = jpeg_bytes(ImageOps.fit(img, (1200, 630), Image.Resampling.LANCZOS))
    except Exception:
        data = raw

    return Response(
        data,
        mimetype="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@assets_bp.route("/static/images/<path:filename>")
def serve_images(filename):
    from flask import current_app

    images_root = os.path.join(current_app.root_path, "static", "images")
    if any(x in filename for x in ["favicon", "apple-touch"]):
        local_path = os.path.join(images_root, filename)
        if os.path.isfile(local_path):
            return send_from_directory(images_root, filename)
    url = f"https://storage.googleapis.com/ok-project-assets/okcaddie/{filename}"
    if request.query_string:
        url = f"{url}?{request.query_string.decode()}"
    return redirect(url, code=302)


@assets_bp.route("/robots.txt")
def robots_txt():
    return send_from_directory(STATIC_DIR, "robots.txt")
