# microservices/inventory_service/main.py
import os
import sys
import atexit
from app import create_app

# Agregar directorios al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'utils'))

from utils import create_health_endpoint
from utils import setup_logger


def main():
    app = create_app()

    # Configurar logging
    logger = setup_logger('inventory_service')

    # Configurar health check
    from app.models import db
    create_health_endpoint(app, 'inventory_service', db)

    # Configurar cierre limpio del scheduler
    def shutdown_scheduler():
        if hasattr(app, 'scheduler') and app.scheduler:
            app.scheduler.shutdown()
            logger.info("📅 Scheduler detenido")

    atexit.register(shutdown_scheduler)

    logger.info("🚀 Inventory Service iniciado en puerto 5005")
    if app.config.get('AUTO_ALERTS_ENABLED', True):
        logger.info("📅 Alertas automáticas habilitadas")

    return app


if __name__ == '__main__':
    app = main()
    app.run(host='0.0.0.0', port=5005, debug=True)