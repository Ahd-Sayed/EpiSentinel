from flask import Blueprint, render_template, request, current_app
from flask_login import login_required
from app.services.model_service import ModelService
from app.utils.helpers import parse_prediction_id, api_response

models_bp = Blueprint("models", __name__)

@models_bp.route("/models")
@login_required
def models_page():
    return render_template("models.html", active="models")

@models_bp.route("/api/models/summary")
@login_required
def api_models_summary():
    try:
        summary_path = current_app.config["FILES"]["summary"]
        data = ModelService.get_model_summary(summary_path)
        return api_response(success=True, message="Model summary metrics loaded", data=data)
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

@models_bp.route("/api/models/filters")
@login_required
def api_model_filters():
    try:
        prediction_id = parse_prediction_id(request.args.get('prediction_id'))
        data = ModelService.get_lstm_filters(prediction_id=prediction_id)
        return api_response(success=True, message="LSTM prediction filters loaded", data=data)
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

@models_bp.route("/api/models/lstm-timeline")
@login_required
def api_lstm_timeline():
    try:
        city = request.args.get("city")
        disease = request.args.get("disease")
        prediction_id = parse_prediction_id(request.args.get('prediction_id'))
        
        if not city or not disease:
            return api_response(success=False, message="Parameters city and disease are required", status_code=400)
            
        data = ModelService.get_lstm_timeline(city=city, disease=disease, prediction_id=prediction_id)
        return api_response(success=True, message="LSTM timeline data loaded", data=data)
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)
