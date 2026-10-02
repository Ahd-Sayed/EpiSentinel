from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
cache = Cache()
csrf = CSRFProtect()

# Configure login options
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"

