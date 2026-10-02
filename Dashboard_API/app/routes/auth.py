from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import current_user
from app.services.auth_service import AuthService
from app.utils.helpers import api_response

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("overview.index"))
        
    if request.method == "POST":
        # Check if JSON or Form request
        if request.is_json:
            data = request.get_json()
            username = data.get("username")
            password = data.get("password")
        else:
            username = request.form.get("username")
            password = request.form.get("password")
            
        user = AuthService.authenticate(username, password)
        
        if user:
            if request.is_json:
                return api_response(success=True, message="Login successful", data={"role": user.role})
            flash("Welcome to EpiGuard Africa Dashboard!", "success")
            return redirect(url_for("overview.index"))
        else:
            if request.is_json:
                return api_response(success=False, message="Invalid username or password", status_code=401)
            flash("Invalid username or password", "danger")
            
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    AuthService.logout()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
