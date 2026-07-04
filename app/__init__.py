from flask import Flask, redirect, request
from flask_compress import Compress
import os

try:
    from .config import FAMILY_SITE_ID, SITE_URL, SUPPORTED_LANGS
    from .data_loader import CACHED_DATA, load_all_data
    from .family_sites import inject_family_context
    from .ids import split_localized_id
    from .reactions import reactions_bp
    from .routes import register_routes
except ImportError:
    from config import FAMILY_SITE_ID, SITE_URL, SUPPORTED_LANGS
    from data_loader import CACHED_DATA, load_all_data
    from family_sites import inject_family_context
    from ids import split_localized_id
    from reactions import reactions_bp
    from routes import register_routes

app = Flask(__name__)
Compress(app)
app.register_blueprint(reactions_bp)
register_routes(app)
load_all_data()


@app.context_processor
def inject_site_url():
    n_courses = len(
        {c.get("base_id") or split_localized_id(c.get("id", ""))[0] for c in CACHED_DATA.get("courses", [])}
    )
    lang = request.args.get("lang", "en") if request else "en"
    return {
        "site_url": SITE_URL,
        "total_course_count": n_courses or len(CACHED_DATA.get("courses", [])),
        **inject_family_context(FAMILY_SITE_ID, lang),
    }


@app.before_request
def seo_url_normalization():
    if request.method != "GET":
        return None
    p = request.path
    if (
        p.startswith("/static/")
        or p.startswith("/api/")
        or p.startswith("/booking/")
        or p.startswith("/travel/")
    ):
        return None

    if request.headers.get("X-Forwarded-Proto", "").lower() == "http":
        return redirect(request.url.replace("http://", "https://", 1), code=301)

    args = request.args
    keys = set(args.keys())

    if p == "/" and keys == {"lang"} and args.get("lang") == "en":
        return redirect("/", code=301)
    if p == "/guide" and keys == {"lang"} and args.get("lang") == "en":
        return redirect("/guide", code=301)
    if p == "/about" and keys == {"lang"} and args.get("lang") == "en":
        return redirect("/about", code=301)
    if p == "/privacy" and keys == {"lang"} and args.get("lang") == "en":
        return redirect("/privacy", code=301)

    if p == "/courses":
        if keys == {"lang"} and args.get("lang") == "en":
            return redirect("/courses", code=301)
        if keys == {"lang", "page"} and args.get("lang") == "en":
            pg = args.get("page") or "1"
            if pg == "1":
                return redirect("/courses", code=301)
            return redirect(f"/courses?page={pg}", code=301)

    if p.startswith("/course/") and len(p) > len("/course/"):
        if keys == {"lang"} and args.get("lang") == "en":
            return redirect(p, code=301)
    if p.startswith("/guide/") and p != "/guide" and len(p) > len("/guide/"):
        if keys == {"lang"} and args.get("lang") == "en":
            return redirect(p, code=301)

    return None


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
