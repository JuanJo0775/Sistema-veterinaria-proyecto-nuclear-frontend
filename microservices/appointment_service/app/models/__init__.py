# microservices/appointment_service/app/models/__init__.py
from .appointment import Appointment, db
from .schedule import VeterinarianSchedule

__all__ = ['Appointment', 'VeterinarianSchedule', 'db']