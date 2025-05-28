# microservices/inventory_service/app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import sys
import os

# Agregar el directorio utils al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'utils'))

from .models import db
from .routes import inventory_bp
from .services import InventoryService


def create_app():
    app = Flask(__name__)

    # Cargar configuración
    from ..config import config
    env = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[env])

    # Inicializar extensiones
    db.init_app(app)
    CORS(app)

    # Inicializar servicio de inventario
    inventory_service = InventoryService()
    inventory_service.init_app(app)

    # Configurar scheduler para alertas automáticas
    if app.config.get('AUTO_ALERTS_ENABLED', True):
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

    # Registrar blueprints
    app.register_blueprint(inventory_bp, url_prefix='/inventory')

    # Crear tablas si no existen
    with app.app_context():
        db.create_all()

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