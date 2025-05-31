# microservices/appointment_service/app/models/__init__.py
from flask_sqlalchemy import SQLAlchemy

# Usar la instancia de db del módulo principal
from .. import db

# Crear instancia de db local para este módulo
db = SQLAlchemy()

# Importar modelos específicos
from .appointment import Appointment
from .schedule import VeterinarianSchedule

__all__ = ['Appointment', 'VeterinarianSchedule', 'db']