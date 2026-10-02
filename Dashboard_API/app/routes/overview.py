from flask import Blueprint, render_template, request
from flask_login import login_required
from app.services.dashboard_service import DashboardService
from app.utils.helpers import parse_prediction_id, api_response
from app.extensions import cache

overview_bp = Blueprint("overview", __name__)

@overview_bp.route("/")
@login_required
def index():
    return render_template("index.html", active="overview")

@overview_bp.route("/spa")
@login_required
def spa_dashboard():
    return render_template("spa.html", active="spa")

@overview_bp.route("/api/overview")
@login_required
def api_overview():
    try:
        data = DashboardService.get_overview_data()
        return api_response(success=True, message="Overview data retrieved successfully", data=data)
    except Exception as e:
        return api_response(success=False, message=f"Failed to retrieve overview data: {str(e)}", status_code=500)

@overview_bp.route("/api/search")
@login_required
def api_search():
    try:
        q = request.args.get("q", "")
        results = DashboardService.global_search(q)
        return api_response(success=True, message="Search results retrieved", data=results)
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

@overview_bp.route("/api/executive-summary")
@login_required
def api_executive_summary():
    try:
        prediction_id = parse_prediction_id(request.args.get('prediction_id'))
        if prediction_id == "":
            prediction_id = None
        data = DashboardService.get_executive_summary(prediction_id=prediction_id)
        return api_response(success=True, message="Executive summary loaded", data=data)
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

