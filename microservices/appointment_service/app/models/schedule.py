# microservices/appointment_service/app/models/schedule.py
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import time

db = SQLAlchemy()


class VeterinarianSchedule(db.Model):
    __tablename__ = 'veterinarian_schedules'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    veterinarian_id = db.Column(db.String(36), nullable=False)  # FK a users
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Lunes, 6=Domingo
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_available = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'veterinarian_id': self.veterinarian_id,
            'day_of_week': self.day_of_week,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'is_available': self.is_available
        }

    @classmethod
    def get_by_veterinarian(cls, vet_id):
        return cls.query.filter_by(veterinarian_id=vet_id, is_available=True).all()

    @classmethod
    def get_by_day(cls, vet_id, day_of_week):
        return cls.query.filter_by(
            veterinarian_id=vet_id,
            day_of_week=day_of_week,
            is_available=True
        ).first()