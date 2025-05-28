# microservices/auth_service/app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import sys
import os

# Agregar el directorio utils al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'utils'))

from .models import db
from .routes import auth_bp


def create_app():
    app = Flask(__name__)

    # Cargar configuración
    from ..config import config
    env = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[env])

    # Inicializar extensiones
    db.init_app(app)
    CORS(app)

    # Registrar blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Crear tablas si no existen
    with app.app_context():
        db.create_all()

    return app