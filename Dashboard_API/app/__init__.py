import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, render_template, redirect, url_for
from app.config import Config
from app.extensions import db, login_manager, cache
from app.services.auth_service import AuthService
from app.utils.helpers import api_response
from flasgger import Swagger
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if type(dbapi_connection).__name__ == "Connection":  # matches sqlite3.Connection
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()
        except Exception:
            pass

def setup_logging():
    # Ensure logs directory exists
    if not os.path.exists("logs"):
        os.makedirs("logs")
        
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]: %(message)s"
    )
    
    # General log file handler
    app_handler = RotatingFileHandler("logs/app.log", maxBytes=10000000, backupCount=5)
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)
    
    # Error log file handler
    error_handler = RotatingFileHandler("logs/errors.log", maxBytes=10000000, backupCount=5)
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)
    
    # Config root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)

def update_db_schema(app):
    import sqlite3
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI")
    if db_uri.startswith("sqlite:///"):
        db_path = db_uri.replace("sqlite:///", "")
        if not os.path.isabs(db_path):
            db_path = os.path.join(app.root_path, "..", db_path)
        db_path = os.path.abspath(db_path)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(Uploads)")
        columns = [col[1] for col in cursor.fetchall()]
        
        new_cols = {
            "progress_percent": "INTEGER NOT NULL DEFAULT 0",
            "progress_stage": "TEXT NOT NULL DEFAULT 'Queued'",
            "elapsed_seconds": "REAL NOT NULL DEFAULT 0.0",
            "estimated_remaining": "REAL NOT NULL DEFAULT 0.0",
            "processed_rows": "INTEGER NOT NULL DEFAULT 0",
            "total_rows": "INTEGER NOT NULL DEFAULT 0",
            "current_speed": "REAL NOT NULL DEFAULT 0.0",
            "pipeline_message": "TEXT NOT NULL DEFAULT ''",
            "quality_score": "REAL NOT NULL DEFAULT 100.0",
            "completeness_score": "REAL NOT NULL DEFAULT 100.0",
            "consistency_score": "REAL NOT NULL DEFAULT 100.0",
            "coverage_score": "REAL NOT NULL DEFAULT 100.0",
            "duplicate_rows": "INTEGER NOT NULL DEFAULT 0",
            "invalid_dates": "INTEGER NOT NULL DEFAULT 0",
            "null_values": "INTEGER NOT NULL DEFAULT 0",
            "date_range": "TEXT NOT NULL DEFAULT ''",
            "unique_cities": "INTEGER NOT NULL DEFAULT 0",
            "unique_diseases": "INTEGER NOT NULL DEFAULT 0",
            "memory_usage": "REAL NOT NULL DEFAULT 0.0"
        }
        
        for col_name, col_type in new_cols.items():
            if col_name not in columns:
                try:
                    cursor.execute(f"ALTER TABLE Uploads ADD COLUMN {col_name} {col_type}")
                    app.logger.info(f"Added column {col_name} to Uploads table.")
                except Exception as e:
                    app.logger.error(f"Failed to add column {col_name}: {e}")
                    
        conn.commit()
        conn.close()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Security session settings
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    
    setup_logging()
    app.logger.info("EpiGuard Africa Dashboard Starting Up...")
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    cache.init_app(app)
    from app.extensions import csrf
    csrf.init_app(app)
    
    # Swagger docs config
    app.config['SWAGGER'] = {
        'title': 'EpiSentinel Africa API Spec',
        'uiversion': 3,
        'description': 'API documentation for the EpiSentinel Africa epidemiological monitoring system'
    }
    swagger = Swagger(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.overview import overview_bp
    from app.routes.alerts import alerts_bp
    from app.routes.scenarios import scenarios_bp
    from app.routes.models import models_bp
    from app.routes.explorer import explorer_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(overview_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(scenarios_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(explorer_bp)
    app.register_blueprint(api_bp)
    
    # Exempt API blueprint from CSRF
    csrf.exempt(api_bp)
    
    # Initialize PipelineService singleton eager-loading
    from app.services.pipeline_service import PipelineService
    PipelineService.initialize(app)
    
    # Create DB and seed users
    with app.app_context():
        db.create_all()
        update_db_schema(app)
        from app.models.user import User
        if not User.query.filter_by(username="admin").first():
            u = User(username="admin", role="Admin")
            u.set_password("admin123")
            db.session.add(u)
        if not User.query.filter_by(username="researcher").first():
            u = User(username="researcher", role="Researcher")
            u.set_password("researcher123")
            db.session.add(u)
        if not User.query.filter_by(username="viewer").first():
            u = User(username="viewer", role="Viewer")
            u.set_password("viewer123")
            db.session.add(u)
        db.session.commit()

    
    # Flask-Login user loader
    @login_manager.user_loader
    def load_user(user_id):
        return AuthService.get_user(user_id)
        
    @login_manager.unauthorized_handler
    def unauthorized_callback():
        if request.path.startswith("/api/"):
            return api_response(success=False, message="Authentication required", status_code=401)
        return redirect(url_for("auth.login"))
        
    # Global error handlers
    @app.errorhandler(401)
    def unauthorized(e):
        if request.path.startswith("/api/"):
            return api_response(success=False, message="Authentication required", status_code=401)
        return redirect(url_for("auth.login"))
        
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return api_response(success=False, message="API endpoint not found", status_code=404)
        return render_template("404.html"), 404
        
    @app.errorhandler(500)
    def internal_error(e):
        if request.path.startswith("/api/"):
            return api_response(success=False, message="Internal server error", status_code=500)
        return render_template("500.html"), 500
        
    return app

app = create_app(Config)

