# microservices/appointment_service/app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import sys
import os

# Configurar path para importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))
service_dir = os.path.dirname(current_dir)
project_dir = os.path.dirname(os.path.dirname(service_dir))

# Agregar directorios al path
sys.path.insert(0, service_dir)
sys.path.insert(0, project_dir)

# Importaciones locales
from .models import db
from .routes import appointment_bp


def create_app():
    app = Flask(__name__)

    # Cargar configuración
    try:
        # Intentar importación relativa
        from ..config import config
    except ImportError:
        # Importación absoluta si falla la relativa
        try:
            from config import config
        except ImportError:
            # Configuración por defecto si no encuentra config.py
            class DefaultConfig:
                SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-appointment'
                SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                                          f"postgresql://{os.environ.get('POSTGRES_USER', 'postgres')}:{os.environ.get('POSTGRES_PASSWORD', 'bocato0731')}@{os.environ.get('POSTGRES_HOST', 'localhost')}:{os.environ.get('POSTGRES_PORT', '5432')}/{os.environ.get('POSTGRES_DB', 'veterinary-system')}"
                SQLALCHEMY_TRACK_MODIFICATIONS = False
                REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/1'
                AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL') or 'http://localhost:5001'
                NOTIFICATION_SERVICE_URL = os.environ.get('NOTIFICATION_SERVICE_URL') or 'http://localhost:5003'
                MEDICAL_SERVICE_URL = os.environ.get('MEDICAL_SERVICE_URL') or 'http://localhost:5004'
                FLASK_ENV = os.environ.get('FLASK_ENV') or 'development'
                DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 'yes']

            config = {'development': DefaultConfig, 'default': DefaultConfig}

    env = os.environ.get('FLASK_ENV', 'development')
    config_class = config.get(env, config.get('default'))
    app.config.from_object(config_class)

    # Inicializar extensiones
    db.init_app(app)
    CORS(app)

    # Registrar blueprints
    app.register_blueprint(appointment_bp, url_prefix='/appointments')

    # Crear tablas si no existen
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"Error creando tablas: {e}")

    return app