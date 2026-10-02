from app.extensions import db

class PredictionDetail(db.Model):
    __tablename__ = "PredictionDetails"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey("Predictions.id"), nullable=False)
    city = db.Column(db.String(100), nullable=False, index=True)
    country = db.Column(db.String(100), nullable=False)
    disease = db.Column(db.String(100), nullable=False, index=True)
    week = db.Column(db.String(50), nullable=False, index=True) # formatted as YYYY-MM-DD
    if_flag = db.Column(db.Integer, nullable=False, default=0)
    dbscan_flag = db.Column(db.Integer, nullable=False, default=0)
    lstm_flag = db.Column(db.Integer, nullable=False, default=0)
    lstm_probability = db.Column(db.Float, nullable=True)
    points = db.Column(db.Integer, nullable=False, default=0)
    alert_level = db.Column(db.String(50), nullable=False) # Normal, Watch, Warning, Emergency
