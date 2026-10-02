from app.extensions import db

class LSTMPredictionFact(db.Model):
    __tablename__ = "Fact_LSTMPredictions"
    
    lstm_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_name = db.Column(db.String(250), nullable=True)  # maps to 'group' in CSV
    target_date = db.Column(db.Date, nullable=False, index=True)
    y_true = db.Column(db.Integer, nullable=False)
    lstm_prob = db.Column(db.Float, nullable=False)
    lstm_pred = db.Column(db.Integer, nullable=False)
    country = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False, index=True)
    disease = db.Column(db.String(100), nullable=False, index=True)
