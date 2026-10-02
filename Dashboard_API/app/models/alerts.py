from app.extensions import db

class WeeklyAlertFact(db.Model):
    __tablename__ = "Fact_WeeklyAlerts"
    
    alert_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prediction_id = db.Column(db.Integer, nullable=True, index=True)
    city = db.Column(db.String(100), nullable=False, index=True)
    disease = db.Column(db.String(100), nullable=False, index=True)
    target_date = db.Column(db.Date, nullable=False, index=True)
    lstm_target_next_week = db.Column(db.Integer, nullable=True)
    lstm_prob = db.Column(db.Float, nullable=True)
    lstm_pred = db.Column(db.Integer, nullable=True)
    week_start = db.Column(db.Date, nullable=True, index=True)
    if_flag = db.Column(db.Integer, default=0)
    dbscan_flag = db.Column(db.Integer, default=0)
    true_outbreak = db.Column(db.Integer, default=0, index=True)
    total_visits = db.Column(db.Float, nullable=True)
    fusion_score = db.Column(db.Integer, default=0)
    alert_level = db.Column(db.String(50), nullable=False, index=True)
