# utils/health_check.py - Para usar en todos los microservicios
from flask import jsonify
import psutil
import time
from datetime import datetime


def create_health_endpoint(app, service_name, db=None):
    @app.route('/health', methods=['GET'])
    def health_check():
        health_data = {
            'service': service_name,
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime': time.time() - app.start_time if hasattr(app, 'start_time') else 0,
            'memory_usage': {
                'percent': psutil.virtual_memory().percent,
                'available': psutil.virtual_memory().available
            },
            'cpu_usage': psutil.cpu_percent(interval=1)
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

    # Registrar tiempo de inicio
    app.start_time = time.time()