# start_all.py - Versión simplificada para iniciar todos los microservicios
import os
import sys
import subprocess
import time
import signal


def setup_environment():
    """Configurar variables de entorno básicas"""
    env_vars = {
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_DB': 'veterinary-system',
        'POSTGRES_USER': 'postgres',
        'POSTGRES_PASSWORD': 'bocato0731',
        'POSTGRES_PORT': '5432',
        'FLASK_ENV': 'development',
        'FLASK_DEBUG': '1'
    }

    for key, value in env_vars.items():
        os.environ.setdefault(key, value)


def start_service(service_path, service_name):
    """Iniciar un microservicio"""
    print(f"🚀 Iniciando {service_name}...")

    try:
        process = subprocess.Popen(
            [sys.executable, 'main.py'],
            cwd=service_path,
            env=os.environ
        )
        return process
    except Exception as e:
        print(f"❌ Error iniciando {service_name}: {e}")
        return None


def main():
    print("🐾 Iniciando Sistema de Clínica Veterinaria")
    print("=" * 50)

    setup_environment()

    # Definir servicios
    services = [
        ('microservices/auth_service', 'Auth Service (Puerto 5001)'),
        ('microservices/appointment_service', 'Appointment Service (Puerto 5002)'),
        ('microservices/notification_service', 'Notification Service (Puerto 5003)'),
        ('microservices/medical_service', 'Medical Service (Puerto 5004)'),
        ('microservices/inventory_service', 'Inventory Service (Puerto 5005)')
    ]

    processes = []

    try:
        # Iniciar todos los servicios
        for service_path, service_name in services:
            process = start_service(service_path, service_name)
            if process:
                processes.append((process, service_name))
                time.sleep(2)  # Esperar un poco entre servicios

        print(f"\n✅ {len(processes)} servicios iniciados")
        print("\n🌐 URLs disponibles:")
        print("  • Auth Service:        http://localhost:5001")
        print("  • Appointment Service: http://localhost:5002")
        print("  • Notification Service: http://localhost:5003")
        print("  • Medical Service:     http://localhost:5004")
        print("  • Inventory Service:   http://localhost:5005")

        print("\n💡 Presiona Ctrl+C para detener todos los servicios")

        # Esperar hasta que se presione Ctrl+C
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servicios...")

        # Terminar todos los procesos
        for process, service_name in processes:
            try:
                process.terminate()
                print(f"🛑 Detenido {service_name}")
            except:
                pass

        # Esperar a que terminen
        for process, _ in processes:
            try:
                process.wait(timeout=5)
            except:
                process.kill()

        print("✅ Todos los servicios detenidos")


if __name__ == '__main__':
    main()