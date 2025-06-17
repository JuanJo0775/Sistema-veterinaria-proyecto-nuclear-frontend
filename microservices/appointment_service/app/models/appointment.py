# microservices/appointment_service/app/models/appointment.py
import uuid
from datetime import datetime
from .. import db


class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pet_id = db.Column(db.String(36), nullable=False, index=True)
    veterinarian_id = db.Column(db.String(36), nullable=False, index=True)
    client_id = db.Column(db.String(36), nullable=False, index=True)
    appointment_date = db.Column(db.Date, nullable=False, index=True)
    appointment_time = db.Column(db.Time, nullable=False)
    appointment_type = db.Column(db.String(50), default='consultation')
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='scheduled')
    notes = db.Column(db.Text)

    # Información adicional para mostrar en vistas
    pet_name = db.Column(db.String(100))
    pet_species = db.Column(db.String(50))
    owner_name = db.Column(db.String(200))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'pet_id': self.pet_id,
            'veterinarian_id': self.veterinarian_id,
            'client_id': self.client_id,
            'appointment_date': self.appointment_date.isoformat() if self.appointment_date else None,
            'appointment_time': self.appointment_time.strftime('%H:%M') if self.appointment_time else None,
            'appointment_type': self.appointment_type,
            'reason': self.reason,
            'status': self.status,
            'notes': self.notes,
            'pet_name': self.pet_name,
            'pet_species': self.pet_species,
            'owner_name': self.owner_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def check_availability(veterinarian_id, appointment_date, appointment_time):
        """Verificar si un horario está disponible"""
        existing = Appointment.query.filter_by(
            veterinarian_id=str(veterinarian_id),
            appointment_date=appointment_date,
            appointment_time=appointment_time
        ).filter(Appointment.status.in_(['scheduled', 'confirmed', 'in_progress'])).first()

        return existing is None

    @staticmethod
    def get_by_veterinarian(veterinarian_id, start_date=None, end_date=None):
        """Obtener citas de un veterinario"""
        query = Appointment.query.filter_by(veterinarian_id=str(veterinarian_id))

        if start_date:
            query = query.filter(Appointment.appointment_date >= start_date)
        if end_date:
            query = query.filter(Appointment.appointment_date <= end_date)

        return query.order_by(Appointment.appointment_date, Appointment.appointment_time).all()

    @staticmethod
    def get_by_client(client_id, status=None):
        """Obtener citas de un cliente"""
        query = Appointment.query.filter_by(client_id=str(client_id))

        if status:
            query = query.filter_by(status=status)

        return query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()
