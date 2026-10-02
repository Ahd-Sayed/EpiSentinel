from app.extensions import db

class DiseaseDim(db.Model):
    __tablename__ = "Dim_Diseases"
    
    disease_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    emoji = db.Column(db.String(10), nullable=True)
