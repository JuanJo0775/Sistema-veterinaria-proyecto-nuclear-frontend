# microservices/inventory_service/app/__init__.py
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
from .routes import inventory_bp
from .services import InventoryService


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
                SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-inventory'
                SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                                          f"postgresql://{os.environ.get('POSTGRES_USER', 'postgres')}:{os.environ.get('POSTGRES_PASSWORD', 'bocato0731')}@{os.environ.get('POSTGRES_HOST', 'localhost')}:{os.environ.get('POSTGRES_PORT', '5432')}/{os.environ.get('POSTGRES_DB', 'veterinary-system')}"
                SQLALCHEMY_TRACK_MODIFICATIONS = False
                REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/4'

                # Configuración de alertas automáticas
                AUTO_ALERTS_ENABLED = os.environ.get('AUTO_ALERTS_ENABLED', 'true').lower() == 'true'
                LOW_STOCK_THRESHOLD_DAYS = int(os.environ.get('LOW_STOCK_THRESHOLD_DAYS', '7'))

                # Service URLs
                AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL') or 'http://localhost:5001'
                APPOINTMENT_SERVICE_URL = os.environ.get('APPOINTMENT_SERVICE_URL') or 'http://localhost:5002'
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

    # Inicializar servicio de inventario
    inventory_service = InventoryService()
    inventory_service.init_app(app)

    # Configurar scheduler para alertas automáticas
    if app.config.get('AUTO_ALERTS_ENABLED', True):
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            scheduler = BackgroundScheduler()

            # Verificar vencimientos diariamente a las 9:00 AM
            scheduler.add_job(
                func=lambda: _check_expiration_alerts(app, inventory_service),
                trigger='cron',
                hour=9,
                minute=0,
                id='check_expiration_alerts'
            )

            scheduler.start()
            app.scheduler = scheduler
        except ImportError:
            print("Warning: APScheduler no disponible, alertas automáticas deshabilitadas")
        except Exception as e:
            print(f"Warning: Error configurando scheduler: {e}")

    # Registrar blueprints
    app.register_blueprint(inventory_bp, url_prefix='/inventory')

    # Crear tablas si no existen
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"Error creando tablas: {e}")

    return app


def _check_expiration_alerts(app, inventory_service):
    """Función para verificar alertas de vencimiento (ejecutada por scheduler)"""
    with app.app_context():
        try:
            threshold_days = app.config.get('LOW_STOCK_THRESHOLD_DAYS', 7)
            expiring_medications = inventory_service.check_expiration_alerts(threshold_days)
            print(f"📅 Verificación automática: {len(expiring_medications)} medicamentos próximos a vencer")
        except Exception as e:
            print(f"Error en verificación automática de vencimientos: {e}")