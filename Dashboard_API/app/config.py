import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # f:/New folder (7)/project5/project
DATA_DIR = BASE_DIR # CSV files are placed in the root of the project

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "epiguard-secret-key-1298471239")
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    if db_url:
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'epiguard_local.db')}"
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {
                "timeout": 15,
                "check_same_thread": False
            }
        }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload and exports config
    MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 1 GB limit
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    EXPORTS_FOLDER = os.path.join(BASE_DIR, "exports")
    
    # Model artifacts directories
    TASK1_3_DIR = os.path.join(BASE_DIR, "task1_3_dir")
    TASK2_DIR = os.path.join(BASE_DIR, "task2_dir")
    TASK2_MODELS_DIR = os.path.join(BASE_DIR, "task2_models_dir")
    
    # Caching config
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    PORT = int(os.environ.get("PORT", 5000))
    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1")



    # Data file paths (from original config)
    FILES = {
        "summary":        os.path.join(DATA_DIR, "task4_summary.json"),
        "validation":     os.path.join(DATA_DIR, "task4_validation.csv"),
        "validation_final": os.path.join(DATA_DIR, "task4_validation_FINAL.csv"),
        "scenarios":      os.path.join(DATA_DIR, "scenarios_exact_dates.csv"),
        "alerts":         os.path.join(DATA_DIR, "task4_weekly_alerts.csv"),
        "signals":        os.path.join(DATA_DIR, "merged_weekly_signals.csv"),
        "signals_overlap": os.path.join(DATA_DIR, "merged_weekly_signals_overlap.csv"),
        "lstm":           os.path.join(DATA_DIR, "lstm_test_predictions.csv"),
        "patients":       os.path.join(DATA_DIR, "test_df_with_if_dbscan_predictions.csv"),
    }

    # Alert level colour mapping
    ALERT_COLORS = {
        "Normal":    "#6B7280",
        "Watch":     "#3B82F6",
        "Warning":   "#F59E0B",
        "Emergency": "#EF4444",
    }

    ALERT_ORDER = ["Normal", "Watch", "Warning", "Emergency"]
    ALERT_NUMERIC = {"Normal": 0, "Watch": 1, "Warning": 2, "Emergency": 3}

    # Disease emoji mapping
    DISEASE_EMOJI = {
        "Ebola virus disease": "🦠",
        "Cholera":             "💧",
        "COVID-19":            "😷",
        "Malaria":             "🦟",
        "Mpox":                "🟤",
        "Dengue fever":        "🦟",
        "Lassa fever":         "🔴",
        "Meningitis":          "🧠",
        "Typhoid fever":       "💊",
    }
