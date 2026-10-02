from flask import Blueprint, render_template, request
from flask_login import login_required
from app.services.scenario_service import ScenarioService
from app.utils.helpers import parse_prediction_id, api_response

scenarios_bp = Blueprint("scenarios", __name__)

@scenarios_bp.route("/scenarios")
@login_required
def scenarios_page():
    return render_template("scenarios.html", active="scenarios")

@scenarios_bp.route("/api/scenarios")
@login_required
def api_scenarios():
    try:
        data = ScenarioService.get_scenarios_validation()
        return api_response(success=True, message="Outbreak validation scenarios loaded", data={"scenarios": data})
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

@scenarios_bp.route("/api/scenarios/timeline")
@login_required
def api_scenario_timeline():
    try:
        city = request.args.get("city")
        disease = request.args.get("disease")
        prediction_id = parse_prediction_id(request.args.get('prediction_id'))
        
        if not city or not disease:
            return api_response(success=False, message="Parameters city and disease are required", status_code=400)
            
        data = ScenarioService.get_scenario_timeline(city=city, disease=disease, prediction_id=prediction_id)
        return api_response(success=True, message="Scenario timeline data loaded", data=data)
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)
