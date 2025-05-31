# microservices/appointment_service/app/models/schedule.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import time

# Importar db del módulo principal
from .. import db


class VeterinarianSchedule(db.Model):
    __tablename__ = 'veterinarian_schedules'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    veterinarian_id = db.Column(UUID(as_uuid=True), nullable=False)  # FK a users
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Lunes, 6=Domingo
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_available = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': str(self.id),
            'veterinarian_id': str(self.veterinarian_id),
            'day_of_week': self.day_of_week,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'is_available': self.is_available
        }

    @classmethod
    def get_by_veterinarian(cls, vet_id):
        # Convertir string a UUID si es necesario
        if isinstance(vet_id, str):
            vet_id = uuid.UUID(vet_id)
        return cls.query.filter_by(veterinarian_id=vet_id, is_available=True).all()

    @classmethod
    def get_by_day(cls, vet_id, day_of_week):
        # Convertir string a UUID si es necesario
        if isinstance(vet_id, str):
            vet_id = uuid.UUID(vet_id)
        return cls.query.filter_by(
            veterinarian_id=vet_id,
            day_of_week=day_of_week,
            is_available=True
        ).first()