# frontend/app/__init__.py - VERSIÓN CORREGIDA
from flask import Flask
from flask_session import Session
import sys
import os

# Configurar path para importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))
service_dir = os.path.dirname(current_dir)
project_dir = os.path.dirname(service_dir)

# Agregar directorios al path
sys.path.insert(0, service_dir)
sys.path.insert(0, project_dir)

# Importaciones locales
from .routes import frontend_bp
from .services import APIClient


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
            from datetime import timedelta

            class DefaultConfig:
                SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-frontend-super-secure-2024'
                AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL') or 'http://localhost:5001'
                APPOINTMENT_SERVICE_URL = os.environ.get('APPOINTMENT_SERVICE_URL') or 'http://localhost:5002'
                NOTIFICATION_SERVICE_URL = os.environ.get('NOTIFICATION_SERVICE_URL') or 'http://localhost:5003'
                MEDICAL_SERVICE_URL = os.environ.get('MEDICAL_SERVICE_URL') or 'http://localhost:5004'
                INVENTORY_SERVICE_URL = os.environ.get('INVENTORY_SERVICE_URL') or 'http://localhost:5005'
                FLASK_ENV = os.environ.get('FLASK_ENV') or 'development'
                DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 'yes']

                # Session Configuration
                SESSION_TYPE = 'filesystem'
                SESSION_PERMANENT = True
                SESSION_USE_SIGNER = True
                SESSION_KEY_PREFIX = 'veterinary_frontend:'
                PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
                SESSION_COOKIE_SECURE = False
                SESSION_COOKIE_HTTPONLY = True
                SESSION_COOKIE_SAMESITE = 'Lax'

                # Upload Configuration
                UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or './uploads'
                MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
                ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

            config = {'development': DefaultConfig, 'default': DefaultConfig}

    env = os.environ.get('FLASK_ENV', 'development')
    config_class = config.get(env, config.get('default'))
    app.config.from_object(config_class)

    # =============== CONFIGURAR UPLOADS (UNA SOLA VEZ) ===============
    setup_upload_config(app)

    # Inicializar Flask-Session
    try:
        Session(app)
        print("✅ Flask-Session inicializado correctamente")
    except Exception as e:
        print(f"⚠️ Error inicializando Flask-Session: {e}")

    # Inicializar el cliente API
    api_client = APIClient()
    api_client.init_app(app)

    # Hacer el cliente API disponible globalmente
    app.api_client = api_client

    # Registrar blueprints
    app.register_blueprint(frontend_bp)

    print(f"✅ Frontend configurado - Entorno: {env}")
    try:
        from .routes.frontend_routes import initialize_app_resources
        initialize_app_resources(app)
    except Exception as e:
        print(f"⚠️ Error inicializando recursos: {e}")

    return app



def setup_upload_config(app):
    """Configurar directorio de uploads (función separada para evitar duplicación)"""
    try:
        # Obtener directorio de uploads
        upload_folder = app.config.get('UPLOAD_FOLDER', './uploads')

        # Convertir a ruta absoluta si es relativa
        if not os.path.isabs(upload_folder):
            upload_folder = os.path.join(os.getcwd(), upload_folder)

        # Actualizar configuración con ruta absoluta
        app.config['UPLOAD_FOLDER'] = upload_folder

        # Crear directorios necesarios
        directories_to_create = [
            upload_folder,
            os.path.join(upload_folder, 'pets'),
            os.path.join(upload_folder, 'exams'),
            os.path.join(upload_folder, 'flask_session')
        ]

        for directory in directories_to_create:
            os.makedirs(directory, exist_ok=True)

        print(f"✅ Upload folder configurado: {upload_folder}")
        print(f"✅ Subdirectorios creados: pets, exams, flask_session")

    except Exception as e:
        print(f"❌ Error configurando uploads: {e}")
        # Configurar directorio por defecto en caso de error
        default_upload = os.path.join(os.getcwd(), 'uploads')
        app.config['UPLOAD_FOLDER'] = default_upload
        os.makedirs(default_upload, exist_ok=True)
        print(f"⚠️ Usando directorio por defecto: {default_upload}")