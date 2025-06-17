# microservices/appointment_service/app/models/schedule.py
import uuid
from datetime import datetime
from .. import db


class VeterinarianSchedule(db.Model):
    __tablename__ = 'veterinarian_schedules'

    id = db.Column(db.Integer, primary_key=True)
    veterinarian_id = db.Column(db.String(36), nullable=False, index=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Sunday, 1=Monday, etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    break_start = db.Column(db.Time, nullable=True)
    break_end = db.Column(db.Time, nullable=True)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'veterinarian_id': self.veterinarian_id,
            'day_of_week': self.day_of_week,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'break_start': self.break_start.strftime('%H:%M') if self.break_start else None,
            'break_end': self.break_end.strftime('%H:%M') if self.break_end else None,
            'is_available': self.is_available,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def get_by_veterinarian(veterinarian_id):
        """Obtener horarios de un veterinario"""
        return VeterinarianSchedule.query.filter_by(
            veterinarian_id=str(veterinarian_id),
            is_available=True
        ).order_by(VeterinarianSchedule.day_of_week).all()

    @staticmethod
    def get_by_day(veterinarian_id, day_of_week):
        """Obtener horario de un día específico"""
        return VeterinarianSchedule.query.filter_by(
            veterinarian_id=str(veterinarian_id),
            day_of_week=day_of_week,
            is_available=True
        ).first()