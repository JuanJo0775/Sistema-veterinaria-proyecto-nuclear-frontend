# microservices/medical_service/app/models/medical_record.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

# Crear instancia local de db
db = SQLAlchemy()


class MedicalRecord(db.Model):
    __tablename__ = 'medical_records'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # TEMPORAL: Sin FK para evitar problemas
    pet_id = db.Column(UUID(as_uuid=True), nullable=False)  # Sin FK por ahora
    veterinarian_id = db.Column(UUID(as_uuid=True), nullable=False)  # FK a users
    appointment_id = db.Column(UUID(as_uuid=True))  # FK a appointments (opcional)

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

    # Relaciones desactivadas temporalmente
    # prescriptions = db.relationship('Prescription', backref='medical_record', lazy=True, cascade='all, delete-orphan')
    # exam_results = db.relationship('ExamResult', backref='medical_record', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        try:
            return {
                'id': str(self.id) if self.id else None,
                'pet_id': str(self.pet_id) if self.pet_id else None,
                'veterinarian_id': str(self.veterinarian_id) if self.veterinarian_id else None,
                'appointment_id': str(self.appointment_id) if self.appointment_id else None,
                'symptoms_description': self.symptoms_description or '',
                'physical_examination': self.physical_examination or '',
                'diagnosis': self.diagnosis or '',
                'treatment': self.treatment or '',
                'medications_prescribed': self.medications_prescribed or '',
                'exams_requested': self.exams_requested or '',
                'observations': self.observations or '',
                'next_appointment_recommendation': self.next_appointment_recommendation or '',
                'weight_at_visit': float(self.weight_at_visit) if self.weight_at_visit is not None else None,
                'temperature': float(self.temperature) if self.temperature is not None else None,
                'pulse': int(self.pulse) if self.pulse is not None else None,
                'respiratory_rate': int(self.respiratory_rate) if self.respiratory_rate is not None else None,
                'status': self.status or 'draft',
                'is_emergency': bool(self.is_emergency) if self.is_emergency is not None else False,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }
        except Exception as e:
            print(f"❌ Error en to_dict(): {e}")
            return {
                'id': str(self.id) if hasattr(self, 'id') and self.id else 'unknown',
                'error': f'Error serializing record: {str(e)}'
            }

    @classmethod
    def get_by_pet(cls, pet_id):
        # Convertir string a UUID si es necesario
        if isinstance(pet_id, str):
            pet_id = uuid.UUID(pet_id)
        return cls.query.filter_by(pet_id=pet_id).order_by(cls.created_at.desc()).all()

    @classmethod
    def get_by_veterinarian(cls, vet_id, start_date=None, end_date=None):
        # Convertir string a UUID si es necesario
        if isinstance(vet_id, str):
            vet_id = uuid.UUID(vet_id)

        query = cls.query.filter_by(veterinarian_id=vet_id)
        if start_date:
            query = query.filter(cls.created_at >= start_date)
        if end_date:
            query = query.filter(cls.created_at <= end_date)
        return query.order_by(cls.created_at.desc()).all()


class Prescription(db.Model):
    __tablename__ = 'prescriptions'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medical_record_id = db.Column(UUID(as_uuid=True), nullable=False)  # Sin FK temporal
    medication_id = db.Column(UUID(as_uuid=True))  # FK a medications (en inventory service)
    medication_name = db.Column(db.String(255), nullable=False)
    dosage = db.Column(db.String(100))
    frequency = db.Column(db.String(100))
    duration = db.Column(db.String(100))
    quantity_prescribed = db.Column(db.Integer)
    instructions = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': str(self.id),
            'medical_record_id': str(self.medical_record_id),
            'medication_id': str(self.medication_id) if self.medication_id else None,
            'medication_name': self.medication_name,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'duration': self.duration,
            'quantity_prescribed': self.quantity_prescribed,
            'instructions': self.instructions
        }


class ExamResult(db.Model):
    __tablename__ = 'exam_results'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medical_record_id = db.Column(UUID(as_uuid=True), nullable=False)  # Sin FK temporal
    exam_id = db.Column(UUID(as_uuid=True))  # FK a exams
    exam_name = db.Column(db.String(255), nullable=False)
    result_file_url = db.Column(db.Text)
    observations = db.Column(db.Text)
    date_performed = db.Column(db.Date)
    performed_by = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': str(self.id),
            'medical_record_id': str(self.medical_record_id),
            'exam_id': str(self.exam_id) if self.exam_id else None,
            'exam_name': self.exam_name,
            'result_file_url': self.result_file_url,
            'observations': self.observations,
            'date_performed': self.date_performed.isoformat() if self.date_performed else None,
            'performed_by': self.performed_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }