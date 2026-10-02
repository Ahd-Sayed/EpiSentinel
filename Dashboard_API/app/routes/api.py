from flask import Blueprint, request, jsonify, g, current_app, send_file
from flask_login import current_user
from app.extensions import db
from app.models.upload import Upload
from app.models.prediction import Prediction
from app.models.prediction_detail import PredictionDetail
from app.models.warning import WarningLog
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.services.upload_service import UploadService
from app.services.prediction_service import PredictionService
from app.services.history_service import HistoryService
from app.services.validation_service import ValidationService
from app.services.notification_service import NotificationService
from app.services.monitor_service import MonitorService
from app.services.pipeline_service import PipelineService
from app.utils.csv_validator import CSVValidationError
from app.utils.helpers import api_response
from functools import wraps
from sqlalchemy import func
import os

api_bp = Blueprint("api", __name__, url_prefix="/api")

def api_login_required(role_needed=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = current_user
            if not user.is_authenticated:
                auth = request.authorization
                if auth:
                    from app.models.user import User
                    db_user = User.query.filter_by(username=auth.username).first()
                    if db_user and db_user.check_password(auth.password):
                        user = db_user
            
            if not user or not user.is_authenticated:
                return jsonify({"success": False, "message": "Authentication required"}), 401
                
            if role_needed and not user.has_role(role_needed):
                return jsonify({"success": False, "message": f"Unauthorized: requires {role_needed} role"}), 403
                
            g.api_user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@api_bp.route("/validate", methods=["POST"])
@api_login_required("Researcher")
def validate_dataset():
    """
    Validate a CSV/XLSX dataset and generate a quality report
    ---
    tags:
      - Dataset Operations
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: The dataset CSV/XLSX file to validate
    responses:
      200:
        description: Validation report generated successfully
      400:
        description: File upload or column validation error
    """
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file part in the request"}), 400
        
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No selected file"}), 400
        
    username = g.api_user.username
    ip_addr = request.remote_addr
    
    try:
        # Convert Excel to CSV temporarily if XLSX uploaded
        # For Excel support, we can read with pandas and export to CSV
        orig_filename = file.filename
        is_xlsx = orig_filename.lower().endswith(('.xlsx', '.xls'))
        
        # Save file
        filepath, safe_filename = UploadService.save_and_validate(file, username)
        
        # Generate Validation Report
        report = ValidationService.generate_validation_report(filepath)
        
        if not report["valid"]:
            # Clean up
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({
                "success": False, 
                "message": "Required column validation failed", 
                "missing_columns": report["missing_required"]
            }), 400
            
        # Create Upload record in database as Queued/Validated
        q_scores = report["quality_scores"]
        upload = Upload(
            original_filename=orig_filename,
            stored_filename=safe_filename,
            uploaded_by=username,
            status="Queued",
            rows=report["total_rows"],
            warnings_count=0,
            quality_score=q_scores["overall"],
            completeness_score=q_scores["completeness"],
            consistency_score=q_scores["consistency"],
            coverage_score=q_scores["coverage"],
            duplicate_rows=report["duplicate_rows"],
            invalid_dates=report["invalid_dates"],
            null_values=report["null_values"],
            date_range=report["date_range"],
            unique_cities=report["unique_cities"],
            unique_diseases=report["unique_diseases"],
            memory_usage=report["memory_usage_mb"]
        )
        db.session.add(upload)
        db.session.commit()
        
        # Log Audit Trail
        audit = AuditLog(user=username, action=f"Validated dataset: {orig_filename}", ip_address=ip_addr)
        db.session.add(audit)
        db.session.commit()
        
        # Add notifications for validation success or warning
        if q_scores["overall"] < 80.0:
            NotificationService.add_notification(
                title="Dataset Validation Warning",
                message=f"Dataset {orig_filename} passed validation with low quality score ({q_scores['overall']}%). Review recommendations before executing.",
                category="Warning"
            )
        else:
            NotificationService.add_notification(
                title="New Dataset Validated",
                message=f"Dataset {orig_filename} successfully validated with quality score {q_scores['overall']}%. Ready to run.",
                category="Success"
            )
            
        return jsonify({
            "success": True,
            "upload_id": upload.id,
            "report": report
        })
        
    except CSVValidationError as e:
        return jsonify({
            "success": False,
            "message": "Missing required columns",
            "missing_columns": e.missing_columns
        }), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400

@api_bp.route("/predict", methods=["POST"])
@api_login_required("Researcher")
def run_prediction():
    """
    Start pipeline execution on an uploaded or pre-validated dataset
    ---
    tags:
      - Predictions
    parameters:
      - name: upload_id
        in: formData
        type: integer
        required: false
        description: ID of a pre-validated upload record to execute
      - name: file
        in: formData
        type: file
        required: false
        description: Patient CSV file (if not pre-validated)
    responses:
      202:
        description: Prediction run scheduled successfully
    """
    username = g.api_user.username
    ip_addr = request.remote_addr
    
    upload_id = request.form.get("upload_id")
    
    if upload_id:
        upload = Upload.query.get(upload_id)
        if not upload:
            return jsonify({"success": False, "message": f"Upload ID {upload_id} not found"}), 404
            
        uploads_dir = current_app.config.get("UPLOAD_FOLDER", "uploads")
        filepath = os.path.join(uploads_dir, upload.stored_filename)
        
        # Change status and reset progress
        upload.status = "Running"
        upload.progress_percent = 5
        upload.progress_stage = "Uploading Dataset"
        upload.pipeline_message = "Scheduling pipeline runner thread..."
        db.session.commit()
        
        # Trigger background processing
        PredictionService.start_prediction_async(
            upload_id=upload.id,
            filepath=filepath,
            username=username,
            ip_address=ip_addr
        )
        
        # Notify Pipeline Started
        NotificationService.add_notification(
            title="Pipeline Execution Started",
            message=f"Surveillance pipeline run initiated for dataset: {upload.original_filename}",
            category="Information"
        )
        
        return jsonify({
            "success": True,
            "message": "Prediction started",
            "upload_id": upload.id,
            "status_url": f"/api/progress/{upload.id}"
        }), 202
        
    else:
        # Fallback support for direct uploads
        if "file" not in request.files:
            return jsonify({"success": False, "message": "No file part in request"}), 400
        file = request.files["file"]
        
        try:
            filepath, safe_filename = UploadService.save_and_validate(file, username)
            upload = Upload(
                original_filename=file.filename,
                stored_filename=safe_filename,
                uploaded_by=username,
                status="Running"
            )
            db.session.add(upload)
            db.session.commit()
            
            PredictionService.start_prediction_async(
                upload_id=upload.id,
                filepath=filepath,
                username=username,
                ip_address=ip_addr
            )
            
            return jsonify({
                "success": True,
                "message": "File uploaded and prediction started",
                "upload_id": upload.id,
                "status_url": f"/api/progress/{upload.id}"
            }), 202
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 400

@api_bp.route("/progress/<int:upload_id>", methods=["GET"])
@api_login_required("Viewer")
def get_progress(upload_id):
    """
    Retrieve execution progress and statistics of a prediction run
    ---
    tags:
      - Predictions
    parameters:
      - name: upload_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Progress statistics
    """
    upload = Upload.query.get(upload_id)
    if not upload:
        return jsonify({"success": False, "message": f"Upload ID {upload_id} not found"}), 404
        
    return jsonify({
        "success": True,
        "upload_id": upload.id,
        "status": upload.status,
        "progress_percent": upload.progress_percent,
        "progress_stage": upload.progress_stage,
        "elapsed_seconds": upload.elapsed_seconds,
        "estimated_remaining": upload.estimated_remaining,
        "processed_rows": upload.processed_rows,
        "total_rows": upload.total_rows,
        "current_speed": upload.current_speed,
        "pipeline_message": upload.pipeline_message
    })

@api_bp.route("/history", methods=["GET"])
@api_login_required("Viewer")
def get_history():
    """Retrieve prediction runs list"""
    runs = HistoryService.get_runs()
    return jsonify({"success": True, "data": runs})

@api_bp.route("/run/<int:upload_id>", methods=["GET"])
@api_login_required("Viewer")
def get_run(upload_id):
    """Retrieve single run metadata"""
    upload = Upload.query.get(upload_id)
    if not upload:
        return jsonify({"success": False, "message": f"Run ID {upload_id} not found"}), 404
        
    prediction = Prediction.query.filter_by(upload_id=upload_id).first()
    prediction_data = None
    if prediction:
        prediction_data = HistoryService.get_run_by_prediction(prediction.id)
        
    return jsonify({
        "success": True,
        "upload": {
            "id": upload.id,
            "original_filename": upload.original_filename,
            "uploaded_by": upload.uploaded_by,
            "upload_time": upload.upload_time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": upload.status,
            "processing_time": round(upload.processing_time, 2) if upload.processing_time else None,
            "warnings_count": upload.warnings_count,
            "quality_score": upload.quality_score,
            "completeness_score": upload.completeness_score,
            "consistency_score": upload.consistency_score,
            "coverage_score": upload.coverage_score,
            "duplicate_rows": upload.duplicate_rows,
            "invalid_dates": upload.invalid_dates,
            "null_values": upload.null_values,
            "date_range": upload.date_range,
            "unique_cities": upload.unique_cities,
            "unique_diseases": upload.unique_diseases,
            "memory_usage": upload.memory_usage
        },
        "prediction": prediction_data
    })

@api_bp.route("/run/<int:prediction_id>/details", methods=["GET"])
@api_login_required("Viewer")
def get_run_details(prediction_id):
    """Retrieve all alert records for a prediction"""
    details = HistoryService.get_run_details(prediction_id)
    return jsonify({"success": True, "data": details})

@api_bp.route("/run/<int:prediction_id>/warnings", methods=["GET"])
@api_login_required("Viewer")
def get_run_warnings(prediction_id):
    """Retrieve warnings list for a prediction session"""
    warnings = HistoryService.get_run_warnings(prediction_id)
    return jsonify({"success": True, "data": warnings})

@api_bp.route("/run/<int:prediction_id>/analytics", methods=["GET"])
@api_login_required("Viewer")
def get_run_analytics(prediction_id):
    """
    Retrieve aggregated analytics metrics for chart visualisations
    ---
    tags:
      - Runs Analytics
    """
    # KPI metrics and Plotly charts datasets
    prediction = Prediction.query.get(prediction_id)
    if not prediction:
        return jsonify({"success": False, "message": "Prediction not found"}), 404
        
    details = PredictionDetail.query.filter_by(prediction_id=prediction_id).all()
    
    # 1. Alert distribution
    dist = {"Normal": 0, "Watch": 0, "Warning": 0, "Emergency": 0}
    for d in details:
        dist[d.alert_level] += 1
        
    # 2. Disease breakdown
    diseases = {}
    for d in details:
        diseases[d.disease] = diseases.get(d.disease, 0) + 1
    disease_list = [{"name": k, "count": v} for k, v in diseases.items()]
    
    # 3. Cities breakdown
    cities = {}
    for d in details:
        cities[d.city] = cities.get(d.city, 0) + 1
    city_list = [{"city": k, "count": v} for k, v in cities.items()]
    
    # 4. Weekly timelines
    weekly_counts = {}
    for d in details:
        weekly_counts[d.week] = weekly_counts.get(d.week, 0) + 1
    weeks_list = [{"week": k, "count": v} for k, v in sorted(weekly_counts.items())]
    
    return jsonify({
        "success": True,
        "distribution": dist,
        "diseases": disease_list,
        "cities": city_list,
        "timeline": weeks_list
    })

@api_bp.route("/runs/compare", methods=["GET"])
@api_login_required("Viewer")
def compare_runs():
    """
    Compare two execution runs side-by-side
    ---
    tags:
      - Runs Comparison
    parameters:
      - name: run_a
        in: query
        type: integer
        required: true
      - name: run_b
        in: query
        type: integer
        required: true
    """
    run_a_id = request.args.get("run_a")
    run_b_id = request.args.get("run_b")
    
    pred_a = Prediction.query.get(run_a_id)
    pred_b = Prediction.query.get(run_b_id)
    
    if not pred_a or not pred_b:
        return jsonify({"success": False, "message": "One or both run IDs not found"}), 404
        
    upload_a = Upload.query.get(pred_a.upload_id)
    upload_b = Upload.query.get(pred_b.upload_id)
    
    details_a = PredictionDetail.query.filter_by(prediction_id=pred_a.id).all()
    details_b = PredictionDetail.query.filter_by(prediction_id=pred_b.id).all()
    
    # Calculate averages
    probs_a = [d.lstm_probability for d in details_a if d.lstm_probability is not None]
    probs_b = [d.lstm_probability for d in details_b if d.lstm_probability is not None]
    
    avg_prob_a = sum(probs_a) / len(probs_a) if probs_a else 0.0
    avg_prob_b = sum(probs_b) / len(probs_b) if probs_b else 0.0
    
    comparison = {
        "run_a": {
            "prediction_id": pred_a.id,
            "filename": upload_a.original_filename if upload_a else "Run A",
            "rows": upload_a.rows if upload_a else 0,
            "duration": round(pred_a.duration, 2) if pred_a.duration else 0.0,
            "warnings": upload_a.warnings_count if upload_a else 0,
            "alerts": pred_a.total_alerts,
            "avg_prob": round(avg_prob_a, 4),
            "quality_score": upload_a.quality_score if upload_a else 100.0,
            "emergency_pct": round((pred_a.emergency_count / max(1, pred_a.total_alerts)) * 100, 1),
            "warning_pct": round((pred_a.warning_count / max(1, pred_a.total_alerts)) * 100, 1),
            "watch_pct": round((pred_a.watch_count / max(1, pred_a.total_alerts)) * 100, 1),
            "levels": {
                "Emergency": pred_a.emergency_count,
                "Warning": pred_a.warning_count,
                "Watch": pred_a.watch_count,
                "Normal": pred_a.normal_count
            }
        },
        "run_b": {
            "prediction_id": pred_b.id,
            "filename": upload_b.original_filename if upload_b else "Run B",
            "rows": upload_b.rows if upload_b else 0,
            "duration": round(pred_b.duration, 2) if pred_b.duration else 0.0,
            "warnings": upload_b.warnings_count if upload_b else 0,
            "alerts": pred_b.total_alerts,
            "avg_prob": round(avg_prob_b, 4),
            "quality_score": upload_b.quality_score if upload_b else 100.0,
            "emergency_pct": round((pred_b.emergency_count / max(1, pred_b.total_alerts)) * 100, 1),
            "warning_pct": round((pred_b.warning_count / max(1, pred_b.total_alerts)) * 100, 1),
            "watch_pct": round((pred_b.watch_count / max(1, pred_b.total_alerts)) * 100, 1),
            "levels": {
                "Emergency": pred_b.emergency_count,
                "Warning": pred_b.warning_count,
                "Watch": pred_b.watch_count,
                "Normal": pred_b.normal_count
            }
        }
    }
    return jsonify({"success": True, "data": comparison})

@api_bp.route("/models/status", methods=["GET"])
@api_login_required("Viewer")
def get_models_status():
    """Retrieve model monitoring details"""
    # Fetch parameters from singleton
    pipeline = None
    try:
        pipeline = PipelineService.get_pipeline()
    except Exception:
        pass
        
    dbscan_thr = pipeline.dbscan_threshold if pipeline else 5.0
    lstm_thr = pipeline.lstm_threshold if pipeline else 0.28
    
    models = [
        {
            "name": "Isolation Forest",
            "type": "Outlier Detection",
            "version": "1.2.0 (scikit-learn)",
            "file": "task3_iso_forest.pkl",
            "threshold": "Decision score < 0.0",
            "status": "Loaded Successfully" if pipeline else "Unavailable",
            "description": "Evaluates patient visit symptoms vectors and checks for individual clinical anomalies."
        },
        {
            "name": "DBSCAN Clustering",
            "type": "Density Clustering",
            "version": "1.2.0 (scikit-learn)",
            "file": "task3_dbscan_params.pkl",
            "threshold": f"Burst count >= {dbscan_thr}",
            "status": "Loaded Successfully" if pipeline else "Unavailable",
            "description": "Groups concurrent anomalous patient encounters spatially per city chunk to highlight active outbreaks."
        },
        {
            "name": "LSTM Ensemble",
            "type": "Neural Networks Forecast",
            "version": "Keras 3.15 / TensorFlow 2.21",
            "file": "best_model_seed42.keras, seed123.keras, seed2024.keras (3-Model Ensemble)",
            "threshold": f"Probability >= {lstm_thr}",
            "status": "Loaded Successfully" if pipeline else "Unavailable",
            "description": "Forecasts case counts growth and outbreak probability based on the preceding 8-week timeline window."
        }
    ]
    return jsonify({"success": True, "data": models})

@api_bp.route("/system/status", methods=["GET"])
@api_login_required("Viewer")
def get_system_status():
    """Retrieve CPU, RAM, SQLite status"""
    status = MonitorService.get_system_status()
    return jsonify({"success": True, "data": status})

@api_bp.route("/notifications", methods=["GET"])
@api_login_required("Viewer")
def get_notifications():
    """Retrieve active notifications and unread counts"""
    unread = NotificationService.get_unread_count()
    all_notifs = NotificationService.get_notifications(limit=30)
    
    notifs_data = [{
        "id": n.id,
        "title": n.title,
        "message": n.message,
        "category": n.category,
        "is_read": n.is_read,
        "time": n.created_at.strftime("%H:%M:%S")
    } for n in all_notifs]
    
    return jsonify({
        "success": True,
        "unread_count": unread,
        "notifications": notifs_data
    })

@api_bp.route("/notifications/read", methods=["POST"])
@api_login_required("Viewer")
def mark_notifications_read():
    """Mark notification or all notifications as read"""
    notif_id = request.form.get("id")
    if notif_id:
        NotificationService.mark_as_read(notif_id)
    else:
        NotificationService.mark_all_as_read()
    return jsonify({"success": True})

@api_bp.route("/notifications/<int:notif_id>", methods=["DELETE"])
@api_login_required("Viewer")
def delete_notification(notif_id):
    """Delete a notification entry"""
    success = NotificationService.delete_notification(notif_id)
    return jsonify({"success": success})

# Exporters
@api_bp.route("/download/<int:prediction_id>/json", methods=["GET"])
@api_login_required("Viewer")
def download_json(prediction_id):
    """Download prediction details as JSON"""
    prediction = Prediction.query.get(prediction_id)
    if not prediction:
        return jsonify({"success": False, "message": "Prediction session not found"}), 404
        
    details = HistoryService.get_run_details(prediction_id)
    return jsonify({"success": True, "prediction_id": prediction_id, "data": details})

@api_bp.route("/system/audit-logs", methods=["GET"])
@api_login_required("Admin")
def get_audit_logs():
    """Retrieve audit logs list"""
    from sqlalchemy import or_
    search = request.args.get("search", "")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    
    query = AuditLog.query
    if search:
        query = query.filter(
            or_(
                AuditLog.user.like(f"%{search}%"),
                AuditLog.action.like(f"%{search}%"),
                AuditLog.ip_address.like(f"%{search}%")
            )
        )
    query = query.order_by(AuditLog.datetime.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    logs = [{
        "id": l.id,
        "user": l.user,
        "action": l.action,
        "ip_address": l.ip_address or "—",
        "created_at": l.datetime.strftime("%Y-%m-%d %H:%M:%S")
    } for l in pagination.items]
    
    return jsonify({
        "success": True,
        "data": logs,
        "total": pagination.total,
        "page": page,
        "pages": pagination.pages
    })

@api_bp.route("/warnings/aggregate", methods=["GET"])
@api_login_required("Viewer")
def get_aggregate_warnings():
    """Retrieve aggregated warnings list"""
    search = request.args.get("search", "")
    run_id = request.args.get("run_id")
    category = request.args.get("category")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    
    query = WarningLog.query.join(Prediction)
    
    if run_id:
        query = query.filter(Prediction.upload_id == run_id)
    if category:
        query = query.filter(WarningLog.warning_type == category)
    if search:
        query = query.filter(WarningLog.warning_value.like(f"%{search}%"))
        
    query = query.order_by(WarningLog.id.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    warnings = []
    for w in pagination.items:
        upload = Upload.query.get(w.prediction.upload_id)
        warnings.append({
            "id": w.id,
            "prediction_id": w.prediction_id,
            "run_name": upload.original_filename if upload else f"Run {w.prediction_id}",
            "type": w.warning_type,
            "value": w.warning_value,
            "severity": "Warning" if "fallback" in w.warning_type.lower() or "missing" in w.warning_type.lower() else "Info"
        })
        
    return jsonify({
        "success": True,
        "data": warnings,
        "total": pagination.total,
        "page": page,
        "pages": pagination.pages
    })

@api_bp.route("/download/<int:prediction_id>/csv", methods=["GET"])
@api_login_required("Viewer")
def download_csv(prediction_id):
    """Download prediction details as CSV"""
    import csv, io
    prediction = Prediction.query.get(prediction_id)
    if not prediction:
        return jsonify({"success": False, "message": "Not found"}), 404
    details = HistoryService.get_run_details(prediction_id)
    output = io.StringIO()
    cols = ["city","country","disease","week","if_flag","dbscan_flag","lstm_flag","lstm_probability","points","alert_level"]
    writer = csv.DictWriter(output, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(details)
    from flask import make_response
    resp = make_response(output.getvalue())
    resp.headers["Content-Disposition"] = f"attachment; filename=run_{prediction_id}_results.csv"
    resp.headers["Content-Type"] = "text/csv"
    return resp

@api_bp.route("/download/<int:prediction_id>/xlsx", methods=["GET"])
@api_login_required("Viewer")
def download_xlsx(prediction_id):
    """Download prediction details as Excel"""
    prediction = Prediction.query.get(prediction_id)
    if not prediction:
        return jsonify({"success": False, "message": "Not found"}), 404
    details = HistoryService.get_run_details(prediction_id)
    from app.services.explorer_service import ExplorerService
    from flask import make_response
    cols = ["city","country","disease","week","if_flag","dbscan_flag","lstm_flag","lstm_probability","points","alert_level"]
    xlsx = ExplorerService.generate_excel_bytes(cols, details)
    resp = make_response(xlsx)
    resp.headers["Content-Disposition"] = f"attachment; filename=run_{prediction_id}_results.xlsx"
    resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return resp

@api_bp.route("/download/<int:prediction_id>/pdf", methods=["GET"])
@api_login_required("Viewer")
def download_pdf(prediction_id):
    """Download prediction details as PDF"""
    prediction = Prediction.query.get(prediction_id)
    if not prediction:
        return jsonify({"success": False, "message": "Not found"}), 404
    details = HistoryService.get_run_details(prediction_id)
    from app.utils.pdf_generator import generate_pdf_bytes
    from flask import make_response
    cols = ["city","country","disease","week","if_flag","dbscan_flag","lstm_probability","points","alert_level"]
    pdf = generate_pdf_bytes(cols, details, f"Prediction Run #{prediction_id}")
    resp = make_response(pdf)
    resp.headers["Content-Disposition"] = f"attachment; filename=run_{prediction_id}_report.pdf"
    resp.headers["Content-Type"] = "application/pdf"
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4 — ENTERPRISE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/search", methods=["GET"])
@api_login_required("Viewer")
def global_search():
    """
    Omnisearch across all entities in the system.
    ---
    tags:
      - Search
    parameters:
      - name: q
        in: query
        type: string
        required: true
        description: Search query string (min 2 chars)
    """
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify({"success": True, "results": [], "total": 0})

    results = []
    pattern = f"%{q}%"

    # Search in prediction details (cities, diseases)
    try:
        from sqlalchemy import or_
        details = PredictionDetail.query.filter(
            or_(
                PredictionDetail.city.ilike(pattern),
                PredictionDetail.disease.ilike(pattern),
                PredictionDetail.country.ilike(pattern)
            )
        ).limit(8).all()
        for d in details:
            results.append({
                "type": "location",
                "icon": "🌆",
                "label": f"{d.city} — {d.disease}",
                "meta": f"{d.alert_level} | Week {d.week} | Score {d.points}",
                "url": f"/runs/{d.prediction_id}",
                "alert": d.alert_level
            })
    except Exception:
        pass

    # Search in uploads/runs
    try:
        uploads = Upload.query.filter(
            Upload.original_filename.ilike(pattern)
        ).limit(5).all()
        for u in uploads:
            pred = Prediction.query.filter_by(upload_id=u.id).first()
            results.append({
                "type": "run",
                "icon": "📋",
                "label": u.original_filename,
                "meta": f"Run #{pred.id if pred else '—'} | {u.status} | {u.upload_time.strftime('%Y-%m-%d') if u.upload_time else ''}",
                "url": f"/runs/{pred.id}" if pred else "/upload"
            })
    except Exception:
        pass

    # Search in warnings
    try:
        warnings = WarningLog.query.filter(
            WarningLog.warning_value.ilike(pattern)
        ).limit(5).all()
        for w in warnings:
            results.append({
                "type": "warning",
                "icon": "⚠️",
                "label": w.warning_type.replace("_", " ").title(),
                "meta": w.warning_value[:80],
                "url": "/warning-center"
            })
    except Exception:
        pass

    # Search in notifications
    try:
        notifs = Notification.query.filter(
            or_(
                Notification.title.ilike(pattern),
                Notification.message.ilike(pattern)
            )
        ).limit(5).all()
        for n in notifs:
            results.append({
                "type": "notification",
                "icon": "🔔",
                "label": n.title,
                "meta": n.message[:80],
                "url": "#"
            })
    except Exception:
        pass

    return jsonify({"success": True, "results": results[:20], "total": len(results)})


@api_bp.route("/analytics", methods=["GET"])
@api_login_required("Viewer")
def get_analytics_data():
    """
    Retrieve aggregated analytics data for the Advanced Analytics Dashboard.
    ---
    tags:
      - Analytics
    parameters:
      - name: prediction_id
        in: query
        type: integer
        required: false
        description: Filter to a specific prediction run (optional)
    """
    from sqlalchemy import func, extract
    from datetime import datetime, timedelta

    empty_fallback = {
        "monthly_trends": [], "weekly_trends": [],
        "disease_dist": [], "country_dist": [], "city_ranking": [],
        "alert_dist": {"Emergency": 0, "Warning": 0, "Watch": 0, "Normal": 0},
        "fusion_histogram": [], "lstm_conf_dist": [],
        "outbreak_growth": [], "total_groups": 0
    }

    try:
        pred_id = request.args.get("prediction_id")
        query = db.session.query(PredictionDetail)
        if pred_id:
            query = query.filter(PredictionDetail.prediction_id == pred_id)

        all_details = query.all()

        if not all_details:
            return jsonify({"success": True, "data": empty_fallback})
    except Exception as e:
        import logging
        logging.error(f"Analytics query failed: {e}")
        return jsonify({"success": True, "data": empty_fallback})

    # Alert distribution
    alert_dist = {"Emergency": 0, "Warning": 0, "Watch": 0, "Normal": 0}
    disease_counts = {}
    country_counts = {}
    city_counts = {}
    fusion_bins = [0] * 6  # 0,1,2,3,4,5
    lstm_conf_bins = [0] * 10  # 0-10%, 10-20%, ..., 90-100%
    weekly_counts = {}
    monthly_counts = {}

    for d in all_details:
        # Alert distribution
        lvl = d.alert_level or "Normal"
        alert_dist[lvl] = alert_dist.get(lvl, 0) + 1

        # Disease breakdown
        disease_counts[d.disease] = disease_counts.get(d.disease, 0) + 1

        # Country breakdown
        if d.country:
            country_counts[d.country] = country_counts.get(d.country, 0) + 1

        # City ranking
        city_counts[d.city] = city_counts.get(d.city, 0) + 1

        # Fusion histogram (0-5 points)
        pts = int(d.points or 0)
        if 0 <= pts <= 5:
            fusion_bins[pts] += 1

        # LSTM confidence bins
        if d.lstm_probability is not None:
            bin_idx = min(9, int(d.lstm_probability * 10))
            lstm_conf_bins[bin_idx] += 1

        # Weekly trends
        if d.week:
            weekly_counts[str(d.week)] = weekly_counts.get(str(d.week), 0) + 1

    # Weekly sorted
    weekly_sorted = [{"week": k, "count": v} for k, v in sorted(weekly_counts.items())]

    # Monthly (group weeks into months - approximate)
    monthly_dict = {}
    for w, cnt in weekly_counts.items():
        try:
            wnum = int(str(w).split("-W")[-1]) if "-W" in str(w) else int(str(w)[-2:])
            month = f"Month {((wnum - 1) // 4) + 1}"
        except Exception:
            month = "Other"
        monthly_dict[month] = monthly_dict.get(month, 0) + cnt
    monthly_sorted = [{"month": k, "count": v} for k, v in sorted(monthly_dict.items())]

    # Outbreak growth rate (emergency count per week)
    emergency_by_week = {}
    for d in all_details:
        if d.alert_level == "Emergency":
            key = str(d.week)
            emergency_by_week[key] = emergency_by_week.get(key, 0) + 1
    growth_sorted = [{"week": k, "count": v} for k, v in sorted(emergency_by_week.items())]

    # Top cities/diseases/countries
    top_diseases = sorted([{"name": k, "count": v} for k, v in disease_counts.items()], key=lambda x: -x["count"])[:12]
    top_countries = sorted([{"name": k, "count": v} for k, v in country_counts.items()], key=lambda x: -x["count"])[:12]
    top_cities = sorted([{"city": k, "count": v} for k, v in city_counts.items()], key=lambda x: -x["count"])[:12]

    return jsonify({
        "success": True,
        "data": {
            "monthly_trends": monthly_sorted,
            "weekly_trends": weekly_sorted[-24:],  # last 24 weeks
            "disease_dist": top_diseases,
            "country_dist": top_countries,
            "city_ranking": top_cities,
            "alert_dist": alert_dist,
            "fusion_histogram": [{"score": i, "count": fusion_bins[i]} for i in range(6)],
            "lstm_conf_dist": [{"range": f"{i*10}-{(i+1)*10}%", "count": lstm_conf_bins[i]} for i in range(10)],
            "outbreak_growth": growth_sorted,
            "total_groups": len(all_details)
        }
    })


@api_bp.route("/settings", methods=["GET", "POST"])
@api_login_required("Viewer")
def user_settings():
    """
    Get or save user dashboard settings (stored client-side in localStorage,
    this endpoint provides defaults and validation).
    """
    if request.method == "GET":
        return jsonify({
            "success": True,
            "defaults": {
                "default_page": "/",
                "refresh_interval": 30,
                "chart_theme": "dark",
                "sidebar_collapsed": False,
                "visible_kpis": ["patients", "visits", "alerts", "emergencies", "warnings", "watches"],
                "map_style": "dark",
                "saved_filters": {}
            }
        })
    data = request.get_json() or {}
    # Settings are persisted client-side; this endpoint just validates
    return jsonify({"success": True, "saved": True, "message": "Settings saved to browser."})


@api_bp.route("/detail/<int:detail_id>/summary", methods=["GET"])
@api_login_required("Viewer")
def get_detail_summary(detail_id):
    """
    Retrieve clinical patient visit summary for a specific prediction detail.
    """
    detail = PredictionDetail.query.get(detail_id)
    if not detail:
        return jsonify({"success": False, "message": "Prediction detail not found"}), 404
        
    from app.models.patients import PatientVisitFact
    from datetime import datetime, timedelta
    
    # Parse week start date
    try:
        # Check if week has year-week format like '2024-W12'
        if "-W" in detail.week:
            # We can parse the Monday of that week
            import time
            week_str = detail.week + "-1" # add weekday Monday
            t = time.strptime(week_str, "%Y-W%W-%w")
            week_start = datetime(t.tm_year, t.tm_mon, t.tm_mday)
        else:
            # ISO date format like YYYY-MM-DD
            week_start = datetime.strptime(detail.week.split()[0], "%Y-%m-%d")
    except Exception:
        try:
            week_start = datetime.strptime(detail.week, "%Y-%m-%d %H:%M:%S")
        except Exception:
            # Fallback
            week_start = None
            
    if not week_start:
        return jsonify({
            "success": True,
            "total_visits": 0,
            "patient_summary": "Invalid week format.",
            "genders": {"Male": 0, "Female": 0},
            "age_groups": {"Children (<18)": 0, "Adults (18-64)": 0, "Seniors (65+)": 0},
            "top_symptoms": [],
            "avg_age": 0.0
        })
        
    week_end = week_start + timedelta(days=7)
    
    # Query visits
    visits = PatientVisitFact.query.filter(
        PatientVisitFact.city == detail.city,
        PatientVisitFact.disease == detail.disease,
        PatientVisitFact.visit_date >= week_start,
        PatientVisitFact.visit_date < week_end
    ).all()
    
    total_visits = len(visits)
    if total_visits == 0:
        return jsonify({
            "success": True,
            "total_visits": 0,
            "patient_summary": "No raw visit records found for this week group in database.",
            "genders": {"Male": 0, "Female": 0},
            "age_groups": {"Children (<18)": 0, "Adults (18-64)": 0, "Seniors (65+)": 0},
            "top_symptoms": [],
            "avg_age": 0.0
        })
        
    ages = [v.age_at_visit for v in visits if v.age_at_visit is not None]
    avg_age = sum(ages) / len(ages) if ages else 0.0
    
    genders = {"Male": 0, "Female": 0, "Other": 0}
    for v in visits:
        g = v.gender or "Other"
        if g in genders:
            genders[g] += 1
        else:
            genders["Other"] += 1
            
    age_groups = {"Children (<18)": 0, "Adults (18-64)": 0, "Seniors (65+)": 0}
    for age in ages:
        if age < 18:
            age_groups["Children (<18)"] += 1
        elif age < 65:
            age_groups["Adults (18-64)"] += 1
        else:
            age_groups["Seniors (65+)"] += 1
            
    symptom_cols = [
        ("fever", "sym_fever"), ("chills", "sym_chills"), ("headache", "sym_headache"),
        ("fatigue", "sym_fatigue"), ("vomiting", "sym_vomiting"), ("diarrhea", "sym_diarrhea"),
        ("cough", "sym_cough"), ("shortness of breath", "sym_shortness_of_breath"),
        ("chest pain", "sym_chest_pain"), ("rash", "sym_rash"), ("muscle pain", "sym_muscle_pain"),
        ("abdominal pain", "sym_abdominal_pain"), ("night sweats", "sym_night_sweats"),
        ("weight loss", "sym_weight_loss"), ("jaundice", "sym_jaundice"), ("stiff neck", "sym_stiff_neck"),
        ("sensitivity to light", "sym_sensitivity_to_light"), ("red eyes", "sym_red_eyes"),
        ("runny nose", "sym_runny_nose"), ("sore throat", "sym_sore_throat"), ("hemorrhage", "sym_hemorrhage"),
        ("sweating", "sym_sweating"), ("dehydration", "sym_dehydration"), ("muscle cramps", "sym_muscle_cramps"),
        ("loss of smell", "sym_loss_of_smell"), ("swollen lymph nodes", "sym_swollen_lymph_nodes"),
        ("pain behind eyes", "sym_pain_behind_eyes"), ("general weakness", "sym_general_weakness")
    ]
    
    symptom_counts = {label: 0 for label, col in symptom_cols}
    for v in visits:
        for label, col in symptom_cols:
            val = getattr(v, col, 0) or 0
            if val > 0:
                symptom_counts[label] += 1
                
    sorted_symptoms = sorted(
        [{"symptom": k, "percentage": round((v / total_visits) * 100, 1)} for k, v in symptom_counts.items() if v > 0],
        key=lambda x: -x["percentage"]
    )
    
    return jsonify({
        "success": True,
        "total_visits": total_visits,
        "avg_age": round(avg_age, 1),
        "genders": genders,
        "age_groups": age_groups,
        "top_symptoms": sorted_symptoms[:5]
    })


@api_bp.route("/upload/<int:upload_id>/pdf-report", methods=["GET"])
@api_login_required("Viewer")
def download_upload_pdf_report(upload_id):
    """
    Generate a professional PDF profile report of an uploaded dataset.
    """
    upload = Upload.query.get(upload_id)
    if not upload:
        return jsonify({"success": False, "message": "Upload not found"}), 404
        
    from app.utils.pdf_generator import generate_pdf_bytes
    # Let's format statistics from the upload record
    details = [
        {"metric": "Quality Score", "value": f"{upload.quality_score or 0.0:.1f}%"},
        {"metric": "Completeness", "value": f"{upload.completeness_score or 0.0:.1f}%"},
        {"metric": "Consistency", "value": f"{upload.consistency_score or 0.0:.1f}%"},
        {"metric": "Coverage", "value": f"{upload.coverage_score or 0.0:.1f}%"},
        {"metric": "Total Rows", "value": f"{upload.rows or 0:,}"},
        {"metric": "Date Range", "value": upload.date_range or "N/A"},
        {"metric": "Cities Tracked", "value": str(upload.unique_cities or 0)},
        {"metric": "Diseases Tracked", "value": str(upload.unique_diseases or 0)},
        {"metric": "Duplicate Rows", "value": f"{upload.duplicate_rows or 0:,}"},
        {"metric": "Null Values", "value": f"{upload.null_values or 0:,}"},
        {"metric": "Invalid Dates", "value": f"{upload.invalid_dates or 0:,}"},
        {"metric": "Memory Usage", "value": f"{upload.memory_usage or 0.0:.2f} MB"}
    ]
    
    cols = ["metric", "value"]
    pdf = generate_pdf_bytes(cols, details, f"Dataset Profile: {upload.original_filename}")
    
    from flask import make_response
    resp = make_response(pdf)
    resp.headers["Content-Disposition"] = f"attachment; filename=dataset_{upload_id}_profile.pdf"
    resp.headers["Content-Type"] = "application/pdf"
    return resp


