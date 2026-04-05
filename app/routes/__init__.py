def register_routes(app):
    """Register all route blueprints with the Flask app."""
    from app.routes.users import users_bp
    from app.routes.urls import urls_bp
    from app.routes.url_actions import url_creation_bp, url_updated_bp, url_delete_bp
    from app.routes.seed import seed_bp
    from app.routes.stats import stats_bp
    from app.routes.events import events_bp
    from app.routes.url_redirect import url_redirect_bp

    app.register_blueprint(users_bp)
    app.register_blueprint(urls_bp)
    app.register_blueprint(url_creation_bp)
    app.register_blueprint(url_updated_bp)
    app.register_blueprint(url_delete_bp)
    app.register_blueprint(seed_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(url_redirect_bp)
