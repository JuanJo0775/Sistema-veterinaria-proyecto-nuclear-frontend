# main_principal.py - Ejecutor principal del sistema de clínica veterinaria
import os
import sys
import time
import signal
import subprocess
import threading
from datetime import datetime
import psutil
import requests

# Agregar directorios al path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)


class VeterinarySystemManager:
    def __init__(self):
        self.services = {
            'auth_service': {
                'name': 'Auth Service',
                'port': 5001,
                'path': 'microservices/auth_service',
                'process': None,
                'status': 'stopped'
            },
            'appointment_service': {
                'name': 'Appointment Service',
                'port': 5002,
                'path': 'microservices/appointment_service',
                'process': None,
                'status': 'stopped'
            },
            'notification_service': {
                'name': 'Notification Service',
                'port': 5003,
                'path': 'microservices/notification_service',
                'process': None,
                'status': 'stopped'
            },
            'medical_service': {
                'name': 'Medical Service',
                'port': 5004,
                'path': 'microservices/medical_service',
                'process': None,
                'status': 'stopped'
            },
            'inventory_service': {
                'name': 'Inventory Service',
                'port': 5005,
                'path': 'microservices/inventory_service',
                'process': None,
                'status': 'stopped'
            }
        }

        self.running = False
        self.setup_environment()

    def setup_environment(self):
        """Configurar variables de entorno comunes"""
        os.environ.setdefault('POSTGRES_HOST', 'localhost')
        os.environ.setdefault('POSTGRES_DB', 'veterinary-system')
        os.environ.setdefault('POSTGRES_USER', 'postgres')
        os.environ.setdefault('POSTGRES_PASSWORD', 'bocato0731')
        os.environ.setdefault('POSTGRES_PORT', '5432')
        os.environ.setdefault('FLASK_ENV', 'development')
        os.environ.setdefault('FLASK_DEBUG', '1')

        # Variables específicas por servicio
        service_env = {
            'auth_service': {
                'REDIS_URL': 'redis://localhost:6379/0',
                'SECRET_KEY': 'dev-secret-key-auth',
                'JWT_SECRET_KEY': 'dev-jwt-secret-key'
            },
            'appointment_service': {
                'REDIS_URL': 'redis://localhost:6379/1',
                'SECRET_KEY': 'dev-secret-key-appointment',
                'AUTH_SERVICE_URL': 'http://localhost:5001',
                'NOTIFICATION_SERVICE_URL': 'http://localhost:5003',
                'MEDICAL_SERVICE_URL': 'http://localhost:5004'
            },
            'notification_service': {
                'REDIS_URL': 'redis://localhost:6379/2',
                'SECRET_KEY': 'dev-secret-key-notification',
                'GMAIL_USER': 'dev@veterinariaclinic.com',
                'GMAIL_PASSWORD': 'dev_password',
                'TWILIO_ACCOUNT_SID': 'dev_account_sid',
                'TWILIO_AUTH_TOKEN': 'dev_auth_token',
                'TWILIO_PHONE_NUMBER': '+1234567890',
                'AUTH_SERVICE_URL': 'http://localhost:5001',
                'APPOINTMENT_SERVICE_URL': 'http://localhost:5002',
                'MEDICAL_SERVICE_URL': 'http://localhost:5004',
                'INVENTORY_SERVICE_URL': 'http://localhost:5005'
            },
            'medical_service': {
                'REDIS_URL': 'redis://localhost:6379/3',
                'SECRET_KEY': 'dev-secret-key-medical',
                'UPLOAD_FOLDER': './uploads',
                'AUTH_SERVICE_URL': 'http://localhost:5001',
                'APPOINTMENT_SERVICE_URL': 'http://localhost:5002',
                'NOTIFICATION_SERVICE_URL': 'http://localhost:5003',
                'INVENTORY_SERVICE_URL': 'http://localhost:5005'
            },
            'inventory_service': {
                'REDIS_URL': 'redis://localhost:6379/4',
                'SECRET_KEY': 'dev-secret-key-inventory',
                'AUTO_ALERTS_ENABLED': 'true',
                'LOW_STOCK_THRESHOLD_DAYS': '7',
                'AUTH_SERVICE_URL': 'http://localhost:5001',
                'APPOINTMENT_SERVICE_URL': 'http://localhost:5002',
                'NOTIFICATION_SERVICE_URL': 'http://localhost:5003',
                'MEDICAL_SERVICE_URL': 'http://localhost:5004'
            }
        }

        # Aplicar variables de entorno específicas
        for service_name, env_vars in service_env.items():
            for key, value in env_vars.items():
                os.environ.setdefault(key, value)

    def check_prerequisites(self):
        """Verificar que PostgreSQL y Redis estén disponibles"""
        print("🔍 Verificando prerequisitos...")

        # Verificar PostgreSQL
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=os.environ['POSTGRES_HOST'],
                database=os.environ['POSTGRES_DB'],
                user=os.environ['POSTGRES_USER'],
                password=os.environ['POSTGRES_PASSWORD'],
                port=os.environ['POSTGRES_PORT']
            )
            conn.close()
            print("✅ PostgreSQL disponible")
        except Exception as e:
            print(f"❌ PostgreSQL no disponible: {e}")
            print(
                "💡 Ejecuta: docker run -d --name postgres-local -p 5432:5432 -e POSTGRES_DB=veterinary-system -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=bocato0731 postgres:15-alpine")
            return False

        # Verificar Redis
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            print("✅ Redis disponible")
        except Exception as e:
            print(f"❌ Redis no disponible: {e}")
            print("💡 Ejecuta: docker run -d --name redis-local -p 6379:6379 redis:7-alpine")
            return False

        return True

    def check_port_available(self, port):
        """Verificar si un puerto está disponible"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                return False
        return True

    def start_service(self, service_key):
        """Iniciar un microservicio específico"""
        service = self.services[service_key]

        # Verificar que el puerto esté disponible
        if not self.check_port_available(service['port']):
            print(f"❌ Puerto {service['port']} ya está en uso para {service['name']}")
            return False

        try:
            # Cambiar al directorio del servicio
            service_path = os.path.join(current_dir, service['path'])

            # Crear directorios necesarios para medical service
            if service_key == 'medical_service':
                uploads_path = os.path.join(service_path, 'uploads')
                os.makedirs(os.path.join(uploads_path, 'pets'), exist_ok=True)
                os.makedirs(os.path.join(uploads_path, 'exams'), exist_ok=True)

            # Iniciar el proceso
            env = os.environ.copy()
            process = subprocess.Popen(
                [sys.executable, 'main_principal.py'],
                cwd=service_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )

            self.services[service_key]['process'] = process
            self.services[service_key]['status'] = 'starting'

            print(f"🚀 Iniciando {service['name']} en puerto {service['port']}...")

            # Iniciar thread para capturar logs
            log_thread = threading.Thread(
                target=self.capture_logs,
                args=(service_key, process),
                daemon=True
            )
            log_thread.start()

            return True

        except Exception as e:
            print(f"❌ Error iniciando {service['name']}: {e}")
            self.services[service_key]['status'] = 'error'
            return False

    def capture_logs(self, service_key, process):
        """Capturar y mostrar logs del servicio"""
        service = self.services[service_key]

        for line in process.stdout:
            if line.strip():
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] [{service['name']}] {line.strip()}")

    def wait_for_service_ready(self, service_key, timeout=30):
        """Esperar a que un servicio esté listo"""
        service = self.services[service_key]
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"http://localhost:{service['port']}/health", timeout=2)
                if response.status_code == 200:
                    self.services[service_key]['status'] = 'running'
                    print(f"✅ {service['name']} está listo")
                    return True
            except:
                pass
            time.sleep(1)

        print(f"⚠️ {service['name']} no respondió en {timeout} segundos")
        self.services[service_key]['status'] = 'timeout'
        return False

    def start_all_services(self):
        """Iniciar todos los microservicios en orden"""
        print("🎯 Iniciando Sistema de Clínica Veterinaria")
        print("=" * 50)

        if not self.check_prerequisites():
            return False

        # Orden de inicio (considerando dependencias)
        startup_order = [
            'auth_service',  # Primero autenticación
            'notification_service',  # Notificaciones
            'inventory_service',  # Inventario
            'medical_service',  # Servicio médico
            'appointment_service'  # Citas (depende de otros)
        ]

        self.running = True

        for service_key in startup_order:
            if not self.running:
                break

            if self.start_service(service_key):
                # Esperar un poco antes del siguiente servicio
                time.sleep(3)
                self.wait_for_service_ready(service_key)
            else:
                print(f"❌ Falló al iniciar {self.services[service_key]['name']}")
                self.stop_all_services()
                return False

        if self.running:
            self.show_status()
            return True
        return False

    def stop_service(self, service_key):
        """Detener un microservicio específico"""
        service = self.services[service_key]

        if service['process']:
            try:
                service['process'].terminate()
                service['process'].wait(timeout=5)
                print(f"🛑 {service['name']} detenido")
            except subprocess.TimeoutExpired:
                service['process'].kill()
                print(f"🔪 {service['name']} forzado a cerrar")
            except Exception as e:
                print(f"❌ Error deteniendo {service['name']}: {e}")

            service['process'] = None
            service['status'] = 'stopped'

    def stop_all_services(self):
        """Detener todos los microservicios"""
        print("\n🛑 Deteniendo todos los servicios...")
        self.running = False

        for service_key in self.services.keys():
            self.stop_service(service_key)

        print("✅ Todos los servicios detenidos")

    def show_status(self):
        """Mostrar el estado de todos los servicios"""
        print("\n📊 Estado del Sistema:")
        print("=" * 50)

        running_count = 0

        for service_key, service in self.services.items():
            status_icon = {
                'running': '🟢',
                'starting': '🟡',
                'stopped': '🔴',
                'error': '❌',
                'timeout': '⚠️'
            }.get(service['status'], '⚪')

            print(f"{status_icon} {service['name']:<20} - Puerto {service['port']} - {service['status'].upper()}")

            if service['status'] == 'running':
                running_count += 1

        print(f"\n✅ Servicios ejecutándose: {running_count}/5")

        if running_count == 5:
            print("\n🌐 URLs disponibles:")
            print("  • Auth Service:        http://localhost:5001")
            print("  • Appointment Service: http://localhost:5002")
            print("  • Notification Service: http://localhost:5003")
            print("  • Medical Service:     http://localhost:5004")
            print("  • Inventory Service:   http://localhost:5005")

            print("\n📊 Health Checks:")
            print("  curl http://localhost:5001/health")
            print("  curl http://localhost:5002/health")
            print("  curl http://localhost:5003/health")
            print("  curl http://localhost:5004/health")
            print("  curl http://localhost:5005/health")

    def monitor_services(self):
        """Monitorear los servicios en un loop"""
        try:
            while self.running:
                time.sleep(10)  # Verificar cada 10 segundos

                # Verificar si algún proceso murió
                for service_key, service in self.services.items():
                    if service['process'] and service['process'].poll() is not None:
                        print(f"⚠️ {service['name']} se detuvo inesperadamente")
                        service['status'] = 'stopped'
                        service['process'] = None

        except KeyboardInterrupt:
            pass

    def signal_handler(self, signum, frame):
        """Manejar señales del sistema"""
        print(f"\n🛑 Recibida señal {signum}, deteniendo servicios...")
        self.stop_all_services()
        sys.exit(0)


def main():
    print("🐾 Sistema de Gestión para Clínica Veterinaria")
    print("🏗️ Arquitectura de Microservicios con Python Flask")
    print("=" * 60)

    manager = VeterinarySystemManager()

    # Configurar manejo de señales
    signal.signal(signal.SIGINT, manager.signal_handler)
    signal.signal(signal.SIGTERM, manager.signal_handler)

    try:
        if manager.start_all_services():
            print(f"\n🎉 ¡Sistema iniciado exitosamente!")
            print("💡 Presiona Ctrl+C para detener todos los servicios")

            # Monitorear servicios
            manager.monitor_services()
        else:
            print("❌ Error iniciando el sistema")
            return 1

    except KeyboardInterrupt:
        print("\n🛑 Deteniendo sistema...")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
    finally:
        manager.stop_all_services()

    return 0


if __name__ == '__main__':
    exit(main())