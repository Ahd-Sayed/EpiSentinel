"""app.py — Flask application entry point"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config

app = create_app(Config)

if __name__ == "__main__":
    print("\n  EpiGuard Africa Dashboard")
    print(f"   http://localhost:{Config.PORT}\n")
    app.run(debug=Config.DEBUG, port=Config.PORT, use_reloader=Config.DEBUG)
