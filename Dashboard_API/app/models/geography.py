from app.extensions import db

class GeographyDim(db.Model):
    __tablename__ = "Dim_Geography"
    
    geo_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    city = db.Column(db.String(100), unique=True, nullable=False, index=True)
    state = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
