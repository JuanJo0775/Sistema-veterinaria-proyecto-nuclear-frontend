# microservices/notification_service/main.py
import os
import sys
from app import create_app

# Agregar directorios al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'utils'))

from untils import create_health_endpoint
from untils import setup_logger


def main():
    app = create_app()

    # Configurar logging
    logger = setup_logger('notification_service')

    # Configurar health check
    from app.models import db
    create_health_endpoint(app, 'notification_service', db)

    logger.info("🚀 Notification Service iniciado en puerto 5003")

    return app


if __name__ == '__main__':
    app = main()
    app.run(host='0.0.0.0', port=5003, debug=True)