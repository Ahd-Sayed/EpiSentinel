from app.extensions import db
from datetime import datetime

class Upload(db.Model):
    __tablename__ = "Uploads"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    original_filename = db.Column(db.String(250), nullable=False)
    stored_filename = db.Column(db.String(250), nullable=False)
    uploaded_by = db.Column(db.String(100), nullable=False, index=True)
    upload_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    rows = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(50), nullable=False, default="Queued") # Queued, Running, Completed, Failed
    processing_time = db.Column(db.Float, nullable=True) # in seconds
    warnings_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Progress Columns
    progress_percent = db.Column(db.Integer, nullable=False, default=0)
    progress_stage = db.Column(db.String(100), nullable=False, default="Queued")
    elapsed_seconds = db.Column(db.Float, nullable=False, default=0.0)
    estimated_remaining = db.Column(db.Float, nullable=False, default=0.0)
    processed_rows = db.Column(db.Integer, nullable=False, default=0)
    total_rows = db.Column(db.Integer, nullable=False, default=0)
    current_speed = db.Column(db.Float, nullable=False, default=0.0)
    pipeline_message = db.Column(db.String(250), nullable=False, default="")

    # Validation & Quality Columns
    quality_score = db.Column(db.Float, nullable=False, default=100.0)
    completeness_score = db.Column(db.Float, nullable=False, default=100.0)
    consistency_score = db.Column(db.Float, nullable=False, default=100.0)
    coverage_score = db.Column(db.Float, nullable=False, default=100.0)
    duplicate_rows = db.Column(db.Integer, nullable=False, default=0)
    invalid_dates = db.Column(db.Integer, nullable=False, default=0)
    null_values = db.Column(db.Integer, nullable=False, default=0)
    date_range = db.Column(db.String(100), nullable=False, default="")
    unique_cities = db.Column(db.Integer, nullable=False, default=0)
    unique_diseases = db.Column(db.Integer, nullable=False, default=0)
    memory_usage = db.Column(db.Float, nullable=False, default=0.0)

    # Relationships
    predictions = db.relationship("Prediction", backref="upload", cascade="all, delete-orphan", lazy=True)

