from app.models.user import User
from flask_login import login_user, logout_user

class AuthService:
    @staticmethod
    def authenticate(username, password):
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return user
        return None

    @staticmethod
    def logout():
        logout_user()

    @staticmethod
    def get_user(user_id):
        return User.query.get(int(user_id))
