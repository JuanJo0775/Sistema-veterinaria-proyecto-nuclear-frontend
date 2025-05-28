# microservices/medical_service/app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import sys
import os

# Agregar el directorio utils al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'utils'))

from .models import db
from .routes import medical_bp


def create_app():
    app = Flask(__name__)

    # Cargar configuración
    from ..config import config
    env = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[env])

    # Crear directorio de uploads si no existe
    upload_folder = app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'pets'), exist_ok=True)
    os.makedirs(os.path.join(upload_folder, 'exams'), exist_ok=True)

    # Inicializar extensiones
    db.init_app(app)
    CORS(app)

    # Registrar blueprints
    app.register_blueprint(medical_bp, url_prefix='/medical')

    # Crear tablas si no existen
    with app.app_context():
        db.create_all()

    return app