# microservices/appointment_service/main_principal.py
import os
import sys

# Agregar el directorio actual y padre al path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

# Ahora importar el módulo app
try:
    from app import create_app
except ImportError:
    # Si falla, intentar con la estructura de paquetes
    import app
    from app import create_app

# Importar utilidades
try:
    from utils import create_health_endpoint, setup_logger
except ImportError:
    # Si no encuentra utils, crear funciones básicas
    import logging
    import time
    from datetime import datetime
    from flask import jsonify


    def setup_logger(name, level=logging.INFO):
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)
        return logger


    def create_health_endpoint(app, service_name, db=None):
        @app.route('/health', methods=['GET'])
        def health_check():
            health_data = {
                'service': service_name,
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat()
            }

            # Check database connection if provided
            if db:
                try:
                    db.session.execute('SELECT 1')
                    health_data['database'] = 'connected'
                except Exception as e:
                    health_data['database'] = 'disconnected'
                    health_data['database_error'] = str(e)
                    health_data['status'] = 'unhealthy'

            status_code = 200 if health_data['status'] == 'healthy' else 503
            return jsonify(health_data), status_code


def main():
    app = create_app()

    # Configurar logging
    logger = setup_logger('appointment_service')

    # Configurar health check
    try:
        from app.models import db
        create_health_endpoint(app, 'appointment_service', db)
    except ImportError:
        create_health_endpoint(app, 'appointment_service')

    logger.info("🚀 Appointment Service iniciado en puerto 5002")

    return app


if __name__ == '__main__':
    app = main()
    app.run(host='0.0.0.0', port=5002, debug=True)