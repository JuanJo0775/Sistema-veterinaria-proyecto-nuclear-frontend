# microservices/medical_service/app/models/__init__.py
from .pet import Pet, db
from .medical_record import MedicalRecord, Prescription, ExamResult

__all__ = ['Pet', 'MedicalRecord', 'Prescription', 'ExamResult', 'db']