from app.extensions import db
from datetime import datetime

class AuditLog(db.Model):
    __tablename__ = "AuditLogs"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user = db.Column(db.String(100), nullable=False, index=True)
    action = db.Column(db.String(250), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
