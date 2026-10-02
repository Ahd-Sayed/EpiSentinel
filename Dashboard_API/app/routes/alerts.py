from flask import Blueprint, render_template, request, make_response
from flask_login import login_required
from app.services.alerts_service import AlertsService
from app.utils.helpers import parse_prediction_id, api_response

alerts_bp = Blueprint("alerts", __name__)

@alerts_bp.route("/alerts")
@login_required
def alerts_page():
    return render_template("alerts.html", active="alerts")

@alerts_bp.route("/api/alerts/filters")
@login_required
def api_filters():
    try:
        prediction_id = parse_prediction_id(request.args.get('prediction_id'))
        data = AlertsService.get_filters(prediction_id=prediction_id)
        return api_response(success=True, message="Alert filters loaded", data=data)
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

@alerts_bp.route("/api/alerts/summary")
@login_required
def api_summary():
    try:
        args = request.args
        prediction_id = parse_prediction_id(args.get('prediction_id'))
        data = AlertsService.get_summary(
            cities=args.getlist("city") or None,
            diseases=args.getlist("disease") or None,
            levels=args.getlist("level") or None,
            date_from=args.get("from"),
            date_to=args.get("to"),
            prediction_id=prediction_id
        )
        return api_response(success=True, message="Alert summary computed", data=data)
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

@alerts_bp.route("/api/alerts/timeline")
@login_required
def api_timeline():
    try:
        city = request.args.get("city")
        disease = request.args.get("disease")
        prediction_id = parse_prediction_id(request.args.get('prediction_id'))
        data = AlertsService.get_timeline(city=city, disease=disease, prediction_id=prediction_id)
        return api_response(success=True, message="Alert timeline loaded", data=data)
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

@alerts_bp.route("/api/alerts/heatmap")
@login_required
def api_heatmap():
    try:
        disease = request.args.get("disease")
        prediction_id = parse_prediction_id(request.args.get('prediction_id'))
        data = AlertsService.get_heatmap(disease=disease, prediction_id=prediction_id)
        return api_response(success=True, message="Alert heatmap generated", data=data)
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

@alerts_bp.route("/api/alerts/table")
@login_required
def api_table():
    try:
        args = request.args
        page = int(args.get("page", 1))
        prediction_id = parse_prediction_id(args.get('prediction_id'))
        
        result = AlertsService.get_paginated_alerts(
            cities=args.getlist("city") or None,
            diseases=args.getlist("disease") or None,
            levels=args.getlist("level") or None,
            date_from=args.get("from"),
            date_to=args.get("to"),
            page=page,
            per_page=50,
            prediction_id=prediction_id
        )
        
        meta = {
            "page": result["page"],
            "pages": result["pages"],
            "total": result["total"]
        }
        return api_response(success=True, message="Table page loaded", data=result, meta=meta)
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)

@alerts_bp.route("/api/alerts/export")
@login_required
def api_export():
    try:
        args = request.args
        prediction_id = parse_prediction_id(args.get('prediction_id'))
        csv_data = AlertsService.generate_csv_export(
            cities=args.getlist("city") or None,
            diseases=args.getlist("disease") or None,
            levels=args.getlist("level") or None,
            date_from=args.get("from"),
            date_to=args.get("to"),
            prediction_id=prediction_id
        )
        resp = make_response(csv_data)
        resp.headers["Content-Disposition"] = "attachment; filename=alerts_filtered.csv"
        resp.headers["Content-Type"] = "text/csv"
        return resp
    except Exception as e:
        return api_response(success=False, message=str(e), status_code=500)
