# frontend/config.py - VERSIÓN LIMPIA
import os
from datetime import timedelta



class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-frontend-super-secure-2024'

    # URLs de los microservicios
    AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL') or 'http://localhost:5001'
    APPOINTMENT_SERVICE_URL = os.environ.get('APPOINTMENT_SERVICE_URL') or 'http://localhost:5002'
    NOTIFICATION_SERVICE_URL = os.environ.get('NOTIFICATION_SERVICE_URL') or 'http://localhost:5003'
    MEDICAL_SERVICE_URL = os.environ.get('MEDICAL_SERVICE_URL') or 'http://localhost:5004'
    INVENTORY_SERVICE_URL = os.environ.get('INVENTORY_SERVICE_URL') or 'http://localhost:5005'

    # Flask Configuration
    FLASK_ENV = os.environ.get('FLASK_ENV') or 'development'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 'yes']

    # Session Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-fallback-key'
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'veterinary_frontend:'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # True en producción con HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or './uploads'

    # Timeouts para requests
    REQUEST_TIMEOUT = 10


class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = 'development'
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = 'production'
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


# Función para verificar roles de usuario
def role_required(required_roles):
    """Decorador para verificar roles de usuario"""

    def decorator(f):
        from functools import wraps
        from flask import session, redirect, url_for, flash

        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                flash('Debes iniciar sesión para acceder a esta página.', 'warning')
                return redirect(url_for('frontend.login'))

            user_role = session['user'].get('role')
            if user_role not in required_roles:
                flash('No tienes permisos para acceder a esta página.', 'error')
                return redirect(url_for('frontend.dashboard'))

            return f(*args, **kwargs)

        return decorated_function

    return decorator