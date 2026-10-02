from app.extensions import db

class CalendarDim(db.Model):
    __tablename__ = "Dim_Calendar"
    
    date_id = db.Column(db.String(10), primary_key=True)  # YYYY-MM-DD
    date_val = db.Column(db.Date, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    week = db.Column(db.Integer, nullable=False)
    day = db.Column(db.Integer, nullable=False)
    season = db.Column(db.String(50), nullable=True)
