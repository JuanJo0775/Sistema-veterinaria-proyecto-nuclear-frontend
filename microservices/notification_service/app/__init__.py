# microservices/notification_service/app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_mail import Mail
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
from .routes import notification_bp
from .services import EmailService, WhatsAppService


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
                SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-notification'
                SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                                          f"postgresql://{os.environ.get('POSTGRES_USER', 'postgres')}:{os.environ.get('POSTGRES_PASSWORD', 'bocato0731')}@{os.environ.get('POSTGRES_HOST', 'localhost')}:{os.environ.get('POSTGRES_PORT', '5432')}/{os.environ.get('POSTGRES_DB', 'veterinary-system')}"
                SQLALCHEMY_TRACK_MODIFICATIONS = False
                REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/2'

                # Email Configuration
                MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
                MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
                MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
                MAIL_USERNAME = os.environ.get('GMAIL_USER')
                MAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD')
                MAIL_DEFAULT_SENDER = os.environ.get('GMAIL_USER') or 'noreply@veterinariaclinic.com'

                # Twilio Configuration
                TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
                TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
                TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER') or '+1234567890'

                # Service URLs
                AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL') or 'http://localhost:5001'
                APPOINTMENT_SERVICE_URL = os.environ.get('APPOINTMENT_SERVICE_URL') or 'http://localhost:5002'
                MEDICAL_SERVICE_URL = os.environ.get('MEDICAL_SERVICE_URL') or 'http://localhost:5004'
                INVENTORY_SERVICE_URL = os.environ.get('INVENTORY_SERVICE_URL') or 'http://localhost:5005'

                FLASK_ENV = os.environ.get('FLASK_ENV') or 'development'
                DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 'yes']

            config = {'development': DefaultConfig, 'default': DefaultConfig}

    env = os.environ.get('FLASK_ENV', 'development')
    config_class = config.get(env, config.get('default'))
    app.config.from_object(config_class)

    # Inicializar extensiones
    db.init_app(app)
    CORS(app)

    # Inicializar Flask-Mail
    try:
        mail = Mail(app)
    except Exception as e:
        print(f"Warning: No se pudo inicializar Flask-Mail: {e}")

    # Inicializar servicios de notificación
    email_service = EmailService()
    email_service.init_app(app)

    whatsapp_service = WhatsAppService()
    whatsapp_service.init_app(app)

    # Registrar blueprints
    app.register_blueprint(notification_bp, url_prefix='/notifications')

    # Crear tablas si no existen
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"Error creando tablas: {e}")

    return app