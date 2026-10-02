from app.extensions import db
from datetime import datetime

class Prediction(db.Model):
    __tablename__ = "Predictions"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    upload_id = db.Column(db.Integer, db.ForeignKey("Uploads.id"), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.Float, nullable=True) # in seconds
    total_groups = db.Column(db.Integer, nullable=False, default=0)
    total_alerts = db.Column(db.Integer, nullable=False, default=0)
    normal_count = db.Column(db.Integer, nullable=False, default=0)
    watch_count = db.Column(db.Integer, nullable=False, default=0)
    warning_count = db.Column(db.Integer, nullable=False, default=0)
    emergency_count = db.Column(db.Integer, nullable=False, default=0)

    # Relationships
    details = db.relationship("PredictionDetail", backref="prediction", cascade="all, delete-orphan", lazy=True)
    warning_logs = db.relationship("WarningLog", backref="prediction", cascade="all, delete-orphan", lazy=True)
