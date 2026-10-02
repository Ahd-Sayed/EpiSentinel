from app.extensions import db

class WarningLog(db.Model):
    __tablename__ = "WarningLogs"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey("Predictions.id"), nullable=False)
    warning_type = db.Column(db.String(100), nullable=False, index=True)
    warning_value = db.Column(db.Text, nullable=False)
