"""Register HTTP route blueprints."""

from __future__ import annotations

from flask import Flask

try:
    from .routes.assets import assets_bp
    from .routes.courses import courses_bp
    from .routes.guides import guides_bp
    from .routes.pages import pages_bp
except ImportError:
    from routes.assets import assets_bp
    from routes.courses import courses_bp
    from routes.guides import guides_bp
    from routes.pages import pages_bp


def register_routes(app: Flask) -> None:
    app.register_blueprint(pages_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(guides_bp)
    app.register_blueprint(assets_bp)
