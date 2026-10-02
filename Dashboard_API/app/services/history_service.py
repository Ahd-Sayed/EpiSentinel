from app.extensions import db
from app.models.upload import Upload
from app.models.prediction import Prediction
from app.models.prediction_detail import PredictionDetail
from app.models.warning import WarningLog
from app.models.audit_log import AuditLog

class HistoryService:
    @staticmethod
    def get_runs():
        """Retrieve list of all uploads/prediction runs."""
        results = db.session.query(
            Upload.id.label("upload_id"),
            Upload.original_filename,
            Upload.uploaded_by,
            Upload.upload_time,
            Upload.rows,
            Upload.status,
            Upload.processing_time,
            Upload.warnings_count,
            Prediction.id.label("prediction_id"),
            Prediction.total_alerts,
            Prediction.normal_count,
            Prediction.watch_count,
            Prediction.warning_count,
            Prediction.emergency_count
        ).outerjoin(Prediction, Prediction.upload_id == Upload.id)\
         .order_by(Upload.upload_time.desc()).all()
         
        runs = []
        for r in results:
            runs.append({
                "upload_id": r.upload_id,
                "original_filename": r.original_filename,
                "uploaded_by": r.uploaded_by,
                "upload_time": r.upload_time.strftime("%Y-%m-%d %H:%M:%S") if r.upload_time else None,
                "rows": r.rows,
                "status": r.status,
                "processing_time": round(r.processing_time, 2) if r.processing_time else None,
                "warnings_count": r.warnings_count,
                "prediction_id": r.prediction_id,
                "total_alerts": r.total_alerts or 0,
                "normal_count": r.normal_count or 0,
                "watch_count": r.watch_count or 0,
                "warning_count": r.warning_count or 0,
                "emergency_count": r.emergency_count or 0
            })
        return runs

    @staticmethod
    def get_run_by_prediction(prediction_id):
        """Get prediction details by ID."""
        pred = Prediction.query.get(prediction_id)
        if not pred:
            return None
        upload = Upload.query.get(pred.upload_id)
        return {
            "prediction_id": pred.id,
            "upload_id": pred.upload_id,
            "original_filename": upload.original_filename if upload else "Unknown",
            "uploaded_by": upload.uploaded_by if upload else "Unknown",
            "started_at": pred.started_at.strftime("%Y-%m-%d %H:%M:%S") if pred.started_at else None,
            "finished_at": pred.finished_at.strftime("%Y-%m-%d %H:%M:%S") if pred.finished_at else None,
            "duration": round(pred.duration, 2) if pred.duration else None,
            "total_groups": pred.total_groups,
            "total_alerts": pred.total_alerts,
            "normal_count": pred.normal_count,
            "watch_count": pred.watch_count,
            "warning_count": pred.warning_count,
            "emergency_count": pred.emergency_count
        }

    @staticmethod
    def get_run_details(prediction_id):
        """Retrieve all details for a prediction."""
        details = PredictionDetail.query.filter_by(prediction_id=prediction_id).all()
        return [{
            "id": d.id,
            "city": d.city,
            "country": d.country,
            "disease": d.disease,
            "week": d.week,
            "if_flag": d.if_flag,
            "dbscan_flag": d.dbscan_flag,
            "lstm_flag": d.lstm_flag,
            "lstm_probability": d.lstm_probability,
            "points": d.points,
            "alert_level": d.alert_level
        } for d in details]

    @staticmethod
    def get_run_warnings(prediction_id):
        """Retrieve all warnings for a prediction."""
        warnings = WarningLog.query.filter_by(prediction_id=prediction_id).all()
        return [{
            "type": w.warning_type,
            "value": w.warning_value
        } for w in warnings]

    @staticmethod
    def delete_run(upload_id, username=None):
        """Delete an upload run and all associated data."""
        upload = Upload.query.get(upload_id)
        if not upload:
            return False
            
        # Log audit trail before deleting
        audit = AuditLog(
            user=username or "System", 
            action=f"Deleted upload run: {upload.original_filename} (id={upload_id})"
        )
        db.session.add(audit)
        
        db.session.delete(upload) # Cascade delete handles Predictions, Details, Warnings
        db.session.commit()
        return True
