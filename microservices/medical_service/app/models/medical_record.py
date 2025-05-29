# microservices/medical_service/app/models/medical_record.py
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime

db = SQLAlchemy()


class MedicalRecord(db.Model):
    __tablename__ = 'medical_records'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pet_id = db.Column(db.String(36), db.ForeignKey('pets.id'), nullable=False)
    veterinarian_id = db.Column(db.String(36), nullable=False)  # FK a users
    appointment_id = db.Column(db.String(36))  # FK a appointments (opcional)

    # Información de la consulta
    symptoms_description = db.Column(db.Text)
    physical_examination = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    treatment = db.Column(db.Text)
    medications_prescribed = db.Column(db.Text)
    exams_requested = db.Column(db.Text)
    observations = db.Column(db.Text)
    next_appointment_recommendation = db.Column(db.Text)

    # Campos adicionales
    weight_at_visit = db.Column(db.Numeric(5, 2))
    temperature = db.Column(db.Numeric(4, 1))
    pulse = db.Column(db.Integer)
    respiratory_rate = db.Column(db.Integer)

    # Estado del registro
    status = db.Column(db.Enum('draft', 'completed', 'reviewed', name='medical_record_status'), default='draft')
    is_emergency = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    prescriptions = db.relationship('Prescription', backref='medical_record', lazy=True, cascade='all, delete-orphan')
    exam_results = db.relationship('ExamResult', backref='medical_record', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'pet_id': self.pet_id,
            'veterinarian_id': self.veterinarian_id,
            'appointment_id': self.appointment_id,
            'symptoms_description': self.symptoms_description,
            'physical_examination': self.physical_examination,
            'diagnosis': self.diagnosis,
            'treatment': self.treatment,
            'medications_prescribed': self.medications_prescribed,
            'exams_requested': self.exams_requested,
            'observations': self.observations,
            'next_appointment_recommendation': self.next_appointment_recommendation,
            'weight_at_visit': float(self.weight_at_visit) if self.weight_at_visit else None,
            'temperature': float(self.temperature) if self.temperature else None,
            'pulse': self.pulse,
            'respiratory_rate': self.respiratory_rate,
            'status': self.status,
            'is_emergency': self.is_emergency,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def get_by_pet(cls, pet_id):
        return cls.query.filter_by(pet_id=pet_id).order_by(cls.created_at.desc()).all()

    @classmethod
    def get_by_veterinarian(cls, vet_id, start_date=None, end_date=None):
        query = cls.query.filter_by(veterinarian_id=vet_id)
        if start_date:
            query = query.filter(cls.created_at >= start_date)
        if end_date:
            query = query.filter(cls.created_at <= end_date)
        return query.order_by(cls.created_at.desc()).all()


class Prescription(db.Model):
    __tablename__ = 'prescriptions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    medical_record_id = db.Column(db.String(36), db.ForeignKey('medical_records.id'), nullable=False)
    medication_id = db.Column(db.String(36))  # FK a medications (en inventory service)
    medication_name = db.Column(db.String(255), nullable=False)
    dosage = db.Column(db.String(100))
    frequency = db.Column(db.String(100))
    duration = db.Column(db.String(100))
    quantity_prescribed = db.Column(db.Integer)
    instructions = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'medical_record_id': self.medical_record_id,
            'medication_id': self.medication_id,
            'medication_name': self.medication_name,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'duration': self.duration,
            'quantity_prescribed': self.quantity_prescribed,
            'instructions': self.instructions
        }


class ExamResult(db.Model):
    __tablename__ = 'exam_results'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    medical_record_id = db.Column(db.String(36), db.ForeignKey('medical_records.id'), nullable=False)
    exam_id = db.Column(db.String(36))  # FK a exams
    exam_name = db.Column(db.String(255), nullable=False)
    result_file_url = db.Column(db.Text)
    observations = db.Column(db.Text)
    date_performed = db.Column(db.Date)
    performed_by = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'medical_record_id': self.medical_record_id,
            'exam_id': self.exam_id,
            'exam_name': self.exam_name,
            'result_file_url': self.result_file_url,
            'observations': self.observations,
            'date_performed': self.date_performed.isoformat() if self.date_performed else None,
            'performed_by': self.performed_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }