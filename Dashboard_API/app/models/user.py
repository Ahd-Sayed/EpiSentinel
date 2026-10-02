from app.extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model, UserMixin):
    __tablename__ = "Users"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(250), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="Viewer")  # Admin, Researcher, Viewer

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        if self.role == "Admin":
            return True
        if role_name == "Admin":
            return self.role == "Admin"
        if role_name == "Researcher":
            return self.role in ("Admin", "Researcher")
        return True
