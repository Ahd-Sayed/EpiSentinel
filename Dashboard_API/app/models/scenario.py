from app.extensions import db

class ScenarioDim(db.Model):
    __tablename__ = "Dim_Scenarios"
    
    scenario_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    city = db.Column(db.String(100), nullable=False, index=True)
    disease = db.Column(db.String(100), nullable=False, index=True)
    exact_start = db.Column(db.Date, nullable=True)
    exact_end = db.Column(db.Date, nullable=True)
    n_records = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(50), nullable=True)
    lstm_available = db.Column(db.Boolean, default=True)
    first_alert_date = db.Column(db.Date, nullable=True)
    lead_time_weeks = db.Column(db.Float, default=0.0)
    max_alert_level = db.Column(db.String(50), nullable=True)
    detection_rate = db.Column(db.Float, default=0.0)
    detected = db.Column(db.Boolean, default=False)
    before_detected = db.Column(db.Boolean, default=False)
    in_test_period = db.Column(db.Boolean, default=True)
