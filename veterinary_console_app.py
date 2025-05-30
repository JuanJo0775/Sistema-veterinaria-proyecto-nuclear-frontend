# veterinary_console_app.py - Aplicación de consola completa para testing
import os
import sys
import time
import json
import threading
import subprocess
import requests
from datetime import datetime, timedelta
import getpass
from typing import Dict, List, Optional


class Colors:
    """Códigos de colores para la consola"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'


class VeterinaryConsoleApp:
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

        self.current_user = None
        self.auth_token = None
        self.test_data = {}
        self.running = False

        self.setup_environment()

    def setup_environment(self):
        """Configurar variables de entorno"""
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

    def print_header(self, title: str):
        """Imprimir encabezado colorido"""
        print(f"\n{Colors.CYAN}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.WHITE}{title:^60}{Colors.RESET}")
        print(f"{Colors.CYAN}{'=' * 60}{Colors.RESET}\n")

    def print_success(self, message: str):
        """Imprimir mensaje de éxito"""
        print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")

    def print_error(self, message: str):
        """Imprimir mensaje de error"""
        print(f"{Colors.RED}❌ {message}{Colors.RESET}")

    def print_warning(self, message: str):
        """Imprimir mensaje de advertencia"""
        print(f"{Colors.YELLOW}⚠️ {message}{Colors.RESET}")

    def print_info(self, message: str):
        """Imprimir mensaje informativo"""
        print(f"{Colors.BLUE}ℹ️ {message}{Colors.RESET}")

    def make_request(self, method: str, url: str, data=None, headers=None) -> dict:
        """Hacer petición HTTP y mostrar detalles"""
        try:
            print(f"{Colors.CYAN}📡 {method} {url}{Colors.RESET}")

            if data:
                print(f"{Colors.YELLOW}📤 Enviando: {json.dumps(data, indent=2, ensure_ascii=False)}{Colors.RESET}")

            if headers is None:
                headers = {}

            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
                headers['Content-Type'] = 'application/json'

            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            # Mostrar respuesta
            status_color = Colors.GREEN if response.status_code < 400 else Colors.RED
            print(f"{status_color}📥 Status: {response.status_code}{Colors.RESET}")

            try:
                response_data = response.json()
                print(
                    f"{Colors.WHITE}📋 Respuesta: {json.dumps(response_data, indent=2, ensure_ascii=False)}{Colors.RESET}")
                return response_data
            except:
                print(f"{Colors.WHITE}📋 Respuesta: {response.text}{Colors.RESET}")
                return {'raw_response': response.text}

        except requests.exceptions.ConnectionError:
            self.print_error("No se pudo conectar al servicio. ¿Está ejecutándose?")
            return {'error': 'connection_error'}
        except Exception as e:
            self.print_error(f"Error en petición: {str(e)}")
            return {'error': str(e)}

    def check_prerequisites(self) -> bool:
        """Verificar prerequisitos"""
        self.print_header("VERIFICANDO PREREQUISITOS")

        # Verificar PostgreSQL
        try:
            import psycopg2
            conn = psycopg2.connect(
                host='localhost',
                database='veterinary-system',
                user='postgres',
                password='bocato0731',
                port='5432'
            )
            conn.close()
            self.print_success("PostgreSQL disponible")
        except Exception as e:
            self.print_error(f"PostgreSQL no disponible: {e}")
            self.print_info(
                "Ejecuta: docker run -d --name postgres-local -p 5432:5432 -e POSTGRES_DB=veterinary-system -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=bocato0731 postgres:15-alpine")
            return False

        # Verificar Redis
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            self.print_success("Redis disponible")
        except Exception as e:
            self.print_error(f"Redis no disponible: {e}")
            self.print_info("Ejecuta: docker run -d --name redis-local -p 6379:6379 redis:7-alpine")
            return False

        return True

    def start_service(self, service_key: str) -> bool:
        """Iniciar un microservicio"""
        service = self.services[service_key]
        service_path = service['path']

        if not os.path.exists(service_path):
            self.print_error(f"No se encontró el directorio: {service_path}")
            return False

        try:
            print(f"{Colors.BLUE}🚀 Iniciando {service['name']}...{Colors.RESET}")

            # Crear directorios necesarios para medical service
            if service_key == 'medical_service':
                uploads_path = os.path.join(service_path, 'uploads')
                os.makedirs(os.path.join(uploads_path, 'pets'), exist_ok=True)
                os.makedirs(os.path.join(uploads_path, 'exams'), exist_ok=True)

            # Iniciar proceso
            process = subprocess.Popen(
                [sys.executable, 'main.py'],
                cwd=service_path,
                env=os.environ,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            self.services[service_key]['process'] = process
            self.services[service_key]['status'] = 'starting'

            # Esperar a que esté disponible
            for attempt in range(30):
                try:
                    response = requests.get(f"http://localhost:{service['port']}/health", timeout=2)
                    if response.status_code == 200:
                        self.services[service_key]['status'] = 'running'
                        self.print_success(f"{service['name']} iniciado en puerto {service['port']}")
                        return True
                except:
                    pass
                time.sleep(1)

            self.print_warning(f"{service['name']} no respondió en 30 segundos")
            return True

        except Exception as e:
            self.print_error(f"Error iniciando {service['name']}: {e}")
            return False

    def stop_service(self, service_key: str):
        """Detener un microservicio"""
        service = self.services[service_key]
        if service['process']:
            try:
                service['process'].terminate()
                service['process'].wait(timeout=5)
                self.print_success(f"{service['name']} detenido")
            except:
                service['process'].kill()
                self.print_warning(f"{service['name']} forzado a cerrar")

            service['process'] = None
            service['status'] = 'stopped'

    def start_all_services(self):
        """Iniciar todos los microservicios"""
        self.print_header("INICIANDO MICROSERVICIOS")

        if not self.check_prerequisites():
            return False

        startup_order = [
            'auth_service',
            'notification_service',
            'inventory_service',
            'medical_service',
            'appointment_service'
        ]

        self.running = True

        for service_key in startup_order:
            if not self.start_service(service_key):
                return False
            time.sleep(2)

        return True

    def stop_all_services(self):
        """Detener todos los microservicios"""
        self.print_header("DETENIENDO SERVICIOS")
        self.running = False

        for service_key in self.services.keys():
            self.stop_service(service_key)

    def show_services_status(self):
        """Mostrar estado de servicios"""
        self.print_header("ESTADO DE SERVICIOS")

        for service_key, service in self.services.items():
            status_icon = {
                'running': '🟢',
                'starting': '🟡',
                'stopped': '🔴'
            }.get(service['status'], '⚪')

            print(f"{status_icon} {service['name']:<20} - Puerto {service['port']} - {service['status'].upper()}")

    # =============== AUTH SERVICE TESTS ===============

    def test_auth_service(self):
        """Menú de testing para Auth Service"""
        while True:
            self.print_header("AUTH SERVICE - TESTING")
            print("1. Health Check")
            print("2. Registrar Usuario")
            print("3. Login")
            print("4. Verificar Token")
            print("5. Ver Perfil")
            print("6. Actualizar Perfil")
            print("7. Cambiar Contraseña")
            print("8. Test Completo de Autenticación")
            print("0. Volver al menú principal")

            choice = input(f"\n{Colors.CYAN}Selecciona una opción: {Colors.RESET}")

            if choice == '0':
                break
            elif choice == '1':
                self.auth_health_check()
            elif choice == '2':
                self.auth_register()
            elif choice == '3':
                self.auth_login()
            elif choice == '4':
                self.auth_verify_token()
            elif choice == '5':
                self.auth_get_profile()
            elif choice == '6':
                self.auth_update_profile()
            elif choice == '7':
                self.auth_change_password()
            elif choice == '8':
                self.auth_complete_test()

    def auth_health_check(self):
        """Health check del auth service"""
        self.print_header("AUTH SERVICE - HEALTH CHECK")
        self.make_request('GET', 'http://localhost:5001/health')

    def auth_register(self):
        """Registrar nuevo usuario"""
        self.print_header("AUTH SERVICE - REGISTRAR USUARIO")

        print("Ingresa los datos del nuevo usuario:")
        email = input("Email: ")
        password = getpass.getpass("Contraseña: ")
        first_name = input("Nombre: ")
        last_name = input("Apellido: ")
        phone = input("Teléfono (opcional): ")

        print("\nRoles disponibles:")
        print("1. client (Cliente)")
        print("2. veterinarian (Veterinario)")
        print("3. receptionist (Recepcionista)")
        print("4. auxiliary (Auxiliar)")
        print("5. admin (Administrador)")

        role_choice = input("Selecciona rol (1-5): ")
        role_map = {
            '1': 'client',
            '2': 'veterinarian',
            '3': 'receptionist',
            '4': 'auxiliary',
            '5': 'admin'
        }
        role = role_map.get(role_choice, 'client')

        data = {
            'email': email,
            'password': password,
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone if phone else None,
            'role': role
        }

        response = self.make_request('POST', 'http://localhost:5001/auth/register', data)

        if response.get('success'):
            self.test_data['last_user_id'] = response.get('user_id')
            self.print_success("Usuario registrado exitosamente")

    def auth_login(self):
        """Login de usuario"""
        self.print_header("AUTH SERVICE - LOGIN")

        email = input("Email: ")
        password = getpass.getpass("Contraseña: ")

        data = {
            'email': email,
            'password': password
        }

        response = self.make_request('POST', 'http://localhost:5001/auth/login', data)

        if response.get('success'):
            self.auth_token = response.get('token')
            self.current_user = response.get('user')
            self.print_success(f"Login exitoso como {self.current_user.get('name')} ({self.current_user.get('role')})")

    def auth_verify_token(self):
        """Verificar token actual"""
        self.print_header("AUTH SERVICE - VERIFICAR TOKEN")

        if not self.auth_token:
            self.print_warning("No hay token activo. Debes hacer login primero.")
            return

        self.make_request('POST', 'http://localhost:5001/auth/verify')

    def auth_get_profile(self):
        """Obtener perfil del usuario actual"""
        self.print_header("AUTH SERVICE - VER PERFIL")

        if not self.auth_token:
            self.print_warning("No hay token activo. Debes hacer login primero.")
            return

        self.make_request('GET', 'http://localhost:5001/auth/profile')

    def auth_update_profile(self):
        """Actualizar perfil"""
        self.print_header("AUTH SERVICE - ACTUALIZAR PERFIL")

        if not self.auth_token:
            self.print_warning("No hay token activo. Debes hacer login primero.")
            return

        print("Ingresa los nuevos datos (deja vacío para no cambiar):")
        first_name = input("Nombre: ")
        last_name = input("Apellido: ")
        phone = input("Teléfono: ")
        address = input("Dirección: ")

        data = {}
        if first_name: data['first_name'] = first_name
        if last_name: data['last_name'] = last_name
        if phone: data['phone'] = phone
        if address: data['address'] = address

        if data:
            self.make_request('PUT', 'http://localhost:5001/auth/profile', data)
        else:
            self.print_warning("No se ingresaron cambios")

    def auth_change_password(self):
        """Cambiar contraseña"""
        self.print_header("AUTH SERVICE - CAMBIAR CONTRASEÑA")

        if not self.auth_token:
            self.print_warning("No hay token activo. Debes hacer login primero.")
            return

        old_password = getpass.getpass("Contraseña actual: ")
        new_password = getpass.getpass("Nueva contraseña: ")

        data = {
            'old_password': old_password,
            'new_password': new_password
        }

        self.make_request('PUT', 'http://localhost:5001/auth/change-password', data)

    def auth_complete_test(self):
        """Test completo de autenticación"""
        self.print_header("AUTH SERVICE - TEST COMPLETO")

        # 1. Health check
        print(f"\n{Colors.BLUE}1. Health Check{Colors.RESET}")
        self.make_request('GET', 'http://localhost:5001/health')

        # 2. Registrar usuario de prueba
        print(f"\n{Colors.BLUE}2. Registrando usuario de prueba{Colors.RESET}")
        test_user = {
            'email': f'test_{int(time.time())}@example.com',
            'password': 'password123',
            'first_name': 'Usuario',
            'last_name': 'Prueba',
            'phone': '+1234567890',
            'role': 'client'
        }

        response = self.make_request('POST', 'http://localhost:5001/auth/register', test_user)

        if response.get('success'):
            # 3. Login
            print(f"\n{Colors.BLUE}3. Login con usuario de prueba{Colors.RESET}")
            login_data = {
                'email': test_user['email'],
                'password': test_user['password']
            }

            login_response = self.make_request('POST', 'http://localhost:5001/auth/login', login_data)

            if login_response.get('success'):
                old_token = self.auth_token
                self.auth_token = login_response.get('token')

                # 4. Verificar token
                print(f"\n{Colors.BLUE}4. Verificando token{Colors.RESET}")
                self.make_request('POST', 'http://localhost:5001/auth/verify')

                # 5. Ver perfil
                print(f"\n{Colors.BLUE}5. Obteniendo perfil{Colors.RESET}")
                self.make_request('GET', 'http://localhost:5001/auth/profile')

                # 6. Actualizar perfil
                print(f"\n{Colors.BLUE}6. Actualizando perfil{Colors.RESET}")
                update_data = {
                    'phone': '+0987654321',
                    'address': 'Dirección de prueba 123'
                }
                self.make_request('PUT', 'http://localhost:5001/auth/profile', update_data)

                # Restaurar token anterior
                self.auth_token = old_token

                self.print_success("Test completo de Auth Service finalizado")

    # =============== MEDICAL SERVICE TESTS ===============

    def test_medical_service(self):
        """Menú de testing para Medical Service"""
        while True:
            self.print_header("MEDICAL SERVICE - TESTING")
            print("1. Health Check")
            print("2. Gestión de Mascotas")
            print("3. Gestión de Historias Clínicas")
            print("4. Gestión de Prescripciones")
            print("5. Gestión de Resultados de Exámenes")
            print("6. Test Completo Medical Service")
            print("0. Volver al menú principal")

            choice = input(f"\n{Colors.CYAN}Selecciona una opción: {Colors.RESET}")

            if choice == '0':
                break
            elif choice == '1':
                self.medical_health_check()
            elif choice == '2':
                self.test_pet_management()
            elif choice == '3':
                self.test_medical_records()
            elif choice == '4':
                self.test_prescriptions()
            elif choice == '5':
                self.test_exam_results()
            elif choice == '6':
                self.medical_complete_test()

    def medical_health_check(self):
        """Health check del medical service"""
        self.print_header("MEDICAL SERVICE - HEALTH CHECK")
        self.make_request('GET', 'http://localhost:5004/health')

    def test_pet_management(self):
        """Testing de gestión de mascotas"""
        while True:
            self.print_header("MEDICAL SERVICE - GESTIÓN DE MASCOTAS")
            print("1. Crear Mascota")
            print("2. Ver Mascota por ID")
            print("3. Buscar Mascotas")
            print("4. Actualizar Mascota")
            print("5. Ver Mascotas por Propietario")
            print("6. Resumen Médico de Mascota")
            print("0. Volver")

            choice = input(f"\n{Colors.CYAN}Selecciona una opción: {Colors.RESET}")

            if choice == '0':
                break
            elif choice == '1':
                self.create_pet()
            elif choice == '2':
                self.get_pet_by_id()
            elif choice == '3':
                self.search_pets()
            elif choice == '4':
                self.update_pet()
            elif choice == '5':
                self.get_pets_by_owner()
            elif choice == '6':
                self.get_medical_summary()

    def create_pet(self):
        """Crear nueva mascota"""
        self.print_header("CREAR MASCOTA")

        owner_id = input("ID del propietario: ")
        name = input("Nombre de la mascota: ")
        species = input("Especie (ej: Perro, Gato): ")
        breed = input("Raza (opcional): ")
        birth_date = input("Fecha de nacimiento (YYYY-MM-DD, opcional): ")
        weight = input("Peso (kg, opcional): ")
        gender = input("Género (Macho/Hembra, opcional): ")
        allergies = input("Alergias conocidas (opcional): ")
        vaccination_status = input("Estado de vacunación (opcional): ")

        data = {
            'owner_id': owner_id,
            'name': name,
            'species': species
        }

        if breed: data['breed'] = breed
        if birth_date: data['birth_date'] = birth_date
        if weight:
            try:
                data['weight'] = float(weight)
            except:
                pass
        if gender: data['gender'] = gender
        if allergies: data['allergies'] = allergies
        if vaccination_status: data['vaccination_status'] = vaccination_status

        response = self.make_request('POST', 'http://localhost:5004/medical/pets', data)

        if response.get('success') and response.get('pet'):
            self.test_data['last_pet_id'] = response['pet']['id']
            self.print_success(f"Mascota creada con ID: {response['pet']['id']}")

    def get_pet_by_id(self):
        """Obtener mascota por ID"""
        self.print_header("VER MASCOTA POR ID")

        pet_id = input("ID de la mascota: ") or self.test_data.get('last_pet_id', '')

        if pet_id:
            self.make_request('GET', f'http://localhost:5004/medical/pets/{pet_id}')
        else:
            self.print_warning("ID de mascota requerido")

    def search_pets(self):
        """Buscar mascotas"""
        self.print_header("BUSCAR MASCOTAS")

        search_term = input("Término de búsqueda: ")

        if search_term:
            self.make_request('GET', f'http://localhost:5004/medical/pets/search?q={search_term}')
        else:
            self.print_warning("Término de búsqueda requerido")

    def update_pet(self):
        """Actualizar mascota"""
        self.print_header("ACTUALIZAR MASCOTA")

        pet_id = input("ID de la mascota: ") or self.test_data.get('last_pet_id', '')

        if not pet_id:
            self.print_warning("ID de mascota requerido")
            return

        print("Ingresa los nuevos datos (deja vacío para no cambiar):")
        name = input("Nombre: ")
        weight = input("Peso (kg): ")
        allergies = input("Alergias: ")
        vaccination_status = input("Estado de vacunación: ")

        data = {}
        if name: data['name'] = name
        if weight:
            try:
                data['weight'] = float(weight)
            except:
                pass
        if allergies: data['allergies'] = allergies
        if vaccination_status: data['vaccination_status'] = vaccination_status

        if data:
            self.make_request('PUT', f'http://localhost:5004/medical/pets/{pet_id}', data)
        else:
            self.print_warning("No se ingresaron cambios")

    def get_pets_by_owner(self):
        """Ver mascotas por propietario"""
        self.print_header("MASCOTAS POR PROPIETARIO")

        owner_id = input("ID del propietario: ")

        if owner_id:
            self.make_request('GET', f'http://localhost:5004/medical/pets/owner/{owner_id}')
        else:
            self.print_warning("ID de propietario requerido")

    def get_medical_summary(self):
        """Obtener resumen médico"""
        self.print_header("RESUMEN MÉDICO")

        pet_id = input("ID de la mascota: ") or self.test_data.get('last_pet_id', '')

        if pet_id:
            self.make_request('GET', f'http://localhost:5004/medical/summary/pet/{pet_id}')
        else:
            self.print_warning("ID de mascota requerido")

    def test_medical_records(self):
        """Testing de historias clínicas"""
        while True:
            self.print_header("MEDICAL SERVICE - HISTORIAS CLÍNICAS")
            print("1. Crear Historia Clínica")
            print("2. Ver Historia Clínica por ID")
            print("3. Actualizar Historia Clínica")
            print("4. Completar Historia Clínica")
            print("5. Ver Historias por Mascota")
            print("0. Volver")

            choice = input(f"\n{Colors.CYAN}Selecciona una opción: {Colors.RESET}")

            if choice == '0':
                break
            elif choice == '1':
                self.create_medical_record()
            elif choice == '2':
                self.get_medical_record()
            elif choice == '3':
                self.update_medical_record()
            elif choice == '4':
                self.complete_medical_record()
            elif choice == '5':
                self.get_medical_records_by_pet()

    def create_medical_record(self):
        """Crear historia clínica"""
        self.print_header("CREAR HISTORIA CLÍNICA")

        pet_id = input("ID de la mascota: ") or self.test_data.get('last_pet_id', '')
        veterinarian_id = input("ID del veterinario: ")
        symptoms = input("Síntomas descritos: ")
        examination = input("Examen físico: ")
        diagnosis = input("Diagnóstico: ")
        treatment = input("Tratamiento: ")
        weight = input("Peso en la visita (kg, opcional): ")
        temperature = input("Temperatura (°C, opcional): ")
        observations = input("Observaciones: ")

        data = {
            'pet_id': pet_id,
            'veterinarian_id': veterinarian_id,
            'symptoms_description': symptoms,
            'physical_examination': examination,
            'diagnosis': diagnosis,
            'treatment': treatment,
            'observations': observations
        }

        if weight:
            try:
                data['weight_at_visit'] = float(weight)
            except:
                pass
        if temperature:
            try:
                data['temperature'] = float(temperature)
            except:
                pass

        response = self.make_request('POST', 'http://localhost:5004/medical/records', data)

        if response.get('success') and response.get('medical_record'):
            self.test_data['last_medical_record_id'] = response['medical_record']['id']
            self.print_success(f"Historia clínica creada con ID: {response['medical_record']['id']}")

    def get_medical_record(self):
        """Ver historia clínica"""
        self.print_header("VER HISTORIA CLÍNICA")

        record_id = input("ID de la historia clínica: ") or self.test_data.get('last_medical_record_id', '')

        if record_id:
            self.make_request('GET', f'http://localhost:5004/medical/records/{record_id}')
        else:
            self.print_warning("ID de historia clínica requerido")

    def update_medical_record(self):
        """Actualizar historia clínica"""
        self.print_header("ACTUALIZAR HISTORIA CLÍNICA")

        record_id = input("ID de la historia clínica: ") or self.test_data.get('last_medical_record_id', '')

        if not record_id:
            self.print_warning("ID de historia clínica requerido")
            return

        print("Ingresa los nuevos datos (deja vacío para no cambiar):")
        diagnosis = input("Diagnóstico: ")
        treatment = input("Tratamiento: ")
        observations = input("Observaciones: ")
        next_appointment = input("Recomendación próxima cita: ")

        data = {}
        if diagnosis: data['diagnosis'] = diagnosis
        if treatment: data['treatment'] = treatment
        if observations: data['observations'] = observations
        if next_appointment: data['next_appointment_recommendation'] = next_appointment

        if data:
            self.make_request('PUT', f'http://localhost:5004/medical/records/{record_id}', data)
        else:
            self.print_warning("No se ingresaron cambios")

    def complete_medical_record(self):
        """Completar historia clínica"""
        self.print_header("COMPLETAR HISTORIA CLÍNICA")

        record_id = input("ID de la historia clínica: ") or self.test_data.get('last_medical_record_id', '')

        if record_id:
            self.make_request('PUT', f'http://localhost:5004/medical/records/{record_id}/complete')
        else:
            self.print_warning("ID de historia clínica requerido")

    def get_medical_records_by_pet(self):
        """Ver historias clínicas por mascota"""
        self.print_header("HISTORIAS CLÍNICAS POR MASCOTA")

        pet_id = input("ID de la mascota: ") or self.test_data.get('last_pet_id', '')

        if pet_id:
            self.make_request('GET', f'http://localhost:5004/medical/records/pet/{pet_id}')
        else:
            self.print_warning("ID de mascota requerido")

    def test_prescriptions(self):
        """Testing de prescripciones"""
        self.print_header("AGREGAR PRESCRIPCIÓN")

        record_id = input("ID de la historia clínica: ") or self.test_data.get('last_medical_record_id', '')
        medication_name = input("Nombre del medicamento: ")
        dosage = input("Dosis: ")
        frequency = input("Frecuencia: ")
        duration = input("Duración: ")
        quantity = input("Cantidad prescrita: ")
        instructions = input("Instrucciones: ")

        data = {
            'medical_record_id': record_id,
            'medication_name': medication_name,
            'dosage': dosage,
            'frequency': frequency,
            'duration': duration,
            'instructions': instructions
        }

        if quantity:
            try:
                data['quantity_prescribed'] = int(quantity)
            except:
                pass

        response = self.make_request('POST', 'http://localhost:5004/medical/prescriptions', data)

        if response.get('success'):
            self.print_success("Prescripción agregada exitosamente")

    def test_exam_results(self):
        """Testing de resultados de exámenes"""
        self.print_header("AGREGAR RESULTADO DE EXAMEN")

        record_id = input("ID de la historia clínica: ") or self.test_data.get('last_medical_record_id', '')
        exam_name = input("Nombre del examen: ")
        observations = input("Observaciones: ")
        date_performed = input("Fecha realizada (YYYY-MM-DD): ")
        performed_by = input("Realizado por: ")

        data = {
            'medical_record_id': record_id,
            'exam_name': exam_name,
            'observations': observations,
            'date_performed': date_performed,
            'performed_by': performed_by
        }

        response = self.make_request('POST', 'http://localhost:5004/medical/exam-results', data)

        if response.get('success'):
            self.print_success("Resultado de examen agregado exitosamente")

    def medical_complete_test(self):
        """Test completo del medical service"""
        self.print_header("MEDICAL SERVICE - TEST COMPLETO")

        # 1. Health check
        print(f"\n{Colors.BLUE}1. Health Check{Colors.RESET}")
        self.make_request('GET', 'http://localhost:5004/health')

        # 2. Crear mascota de prueba
        print(f"\n{Colors.BLUE}2. Creando mascota de prueba{Colors.RESET}")
        pet_data = {
            'owner_id': 'test-owner-id',
            'name': 'Luna',
            'species': 'Gato',
            'breed': 'Persa',
            'birth_date': '2020-03-15',
            'weight': 4.5,
            'gender': 'Hembra',
            'allergies': 'Ninguna conocida',
            'vaccination_status': 'Al día'
        }

        pet_response = self.make_request('POST', 'http://localhost:5004/medical/pets', pet_data)

        if pet_response.get('success'):
            pet_id = pet_response['pet']['id']

            # 3. Crear historia clínica
            print(f"\n{Colors.BLUE}3. Creando historia clínica{Colors.RESET}")
            record_data = {
                'pet_id': pet_id,
                'veterinarian_id': 'test-vet-id',
                'symptoms_description': 'Pérdida de apetito y letargo',
                'physical_examination': 'Temperatura normal, ganglios sin alteraciones',
                'diagnosis': 'Infección gastrointestinal leve',
                'treatment': 'Dieta blanda y medicación',
                'weight_at_visit': 4.3,
                'temperature': 38.5
            }

            record_response = self.make_request('POST', 'http://localhost:5004/medical/records', record_data)

            if record_response.get('success'):
                record_id = record_response['medical_record']['id']

                # 4. Agregar prescripción
                print(f"\n{Colors.BLUE}4. Agregando prescripción{Colors.RESET}")
                prescription_data = {
                    'medical_record_id': record_id,
                    'medication_name': 'Amoxicilina 250mg',
                    'dosage': '1 comprimido',
                    'frequency': 'Cada 12 horas',
                    'duration': '7 días',
                    'quantity_prescribed': 14,
                    'instructions': 'Administrar con comida'
                }

                self.make_request('POST', 'http://localhost:5004/medical/prescriptions', prescription_data)

                # 5. Ver historia clínica completa
                print(f"\n{Colors.BLUE}5. Obteniendo historia clínica completa{Colors.RESET}")
                self.make_request('GET', f'http://localhost:5004/medical/records/{record_id}')

                # 6. Completar historia clínica
                print(f"\n{Colors.BLUE}6. Completando historia clínica{Colors.RESET}")
                self.make_request('PUT', f'http://localhost:5004/medical/records/{record_id}/complete')

                # 7. Obtener resumen médico
                print(f"\n{Colors.BLUE}7. Obteniendo resumen médico{Colors.RESET}")
                self.make_request('GET', f'http://localhost:5004/medical/summary/pet/{pet_id}')

                self.print_success("Test completo de Medical Service finalizado")

    # =============== INVENTORY SERVICE TESTS ===============

    def test_inventory_service(self):
        """Menú de testing para Inventory Service"""
        while True:
            self.print_header("INVENTORY SERVICE - TESTING")
            print("1. Health Check")
            print("2. Gestión de Medicamentos")
            print("3. Gestión de Stock")
            print("4. Alertas y Reportes")
            print("5. Test Completo Inventory Service")
            print("0. Volver al menú principal")

            choice = input(f"\n{Colors.CYAN}Selecciona una opción: {Colors.RESET}")

            if choice == '0':
                break
            elif choice == '1':
                self.inventory_health_check()
            elif choice == '2':
                self.test_medication_management()
            elif choice == '3':
                self.test_stock_management()
            elif choice == '4':
                self.test_alerts_reports()
            elif choice == '5':
                self.inventory_complete_test()

    def inventory_health_check(self):
        """Health check del inventory service"""
        self.print_header("INVENTORY SERVICE - HEALTH CHECK")
        self.make_request('GET', 'http://localhost:5005/health')

    def test_medication_management(self):
        """Testing de gestión de medicamentos"""
        while True:
            self.print_header("INVENTORY SERVICE - GESTIÓN DE MEDICAMENTOS")
            print("1. Crear Medicamento")
            print("2. Ver Medicamento por ID")
            print("3. Buscar Medicamentos")
            print("4. Actualizar Medicamento")
            print("5. Listar Todos los Medicamentos")
            print("6. Desactivar Medicamento")
            print("0. Volver")

            choice = input(f"\n{Colors.CYAN}Selecciona una opción: {Colors.RESET}")

            if choice == '0':
                break
            elif choice == '1':
                self.create_medication()
            elif choice == '2':
                self.get_medication_by_id()
            elif choice == '3':
                self.search_medications()
            elif choice == '4':
                self.update_medication()
            elif choice == '5':
                self.list_all_medications()
            elif choice == '6':
                self.deactivate_medication()

    def create_medication(self):
        """Crear nuevo medicamento"""
        self.print_header("CREAR MEDICAMENTO")

        name = input("Nombre del medicamento: ")
        description = input("Descripción: ")
        stock_quantity = input("Cantidad inicial en stock: ")
        unit_price = input("Precio unitario: ")
        expiration_date = input("Fecha de vencimiento (YYYY-MM-DD, opcional): ")
        supplier = input("Proveedor: ")
        minimum_stock_alert = input("Alerta de stock mínimo (opcional): ")
        category = input("Categoría (ej: Antibiótico, Analgésico): ")
        presentation = input("Presentación (ej: Comprimidos, Jarabe): ")
        concentration = input("Concentración (ej: 500mg): ")
        laboratory = input("Laboratorio: ")

        data = {
            'name': name,
            'description': description,
            'unit_price': float(unit_price),
            'supplier': supplier,
            'category': category,
            'presentation': presentation,
            'concentration': concentration,
            'laboratory': laboratory
        }

        if stock_quantity:
            try:
                data['stock_quantity'] = int(stock_quantity)
            except:
                pass

        if expiration_date:
            data['expiration_date'] = expiration_date

        if minimum_stock_alert:
            try:
                data['minimum_stock_alert'] = int(minimum_stock_alert)
            except:
                pass

        response = self.make_request('POST', 'http://localhost:5005/inventory/medications', data)

        if response.get('success') and response.get('medication'):
            self.test_data['last_medication_id'] = response['medication']['id']
            self.print_success(f"Medicamento creado con ID: {response['medication']['id']}")

    def get_medication_by_id(self):
        """Ver medicamento por ID"""
        self.print_header("VER MEDICAMENTO POR ID")

        med_id = input("ID del medicamento: ") or self.test_data.get('last_medication_id', '')

        if med_id:
            self.make_request('GET', f'http://localhost:5005/inventory/medications/{med_id}')
        else:
            self.print_warning("ID de medicamento requerido")

    def search_medications(self):
        """Buscar medicamentos"""
        self.print_header("BUSCAR MEDICAMENTOS")

        search_term = input("Término de búsqueda: ")

        if search_term:
            self.make_request('GET', f'http://localhost:5005/inventory/medications/search?q={search_term}')
        else:
            self.print_warning("Término de búsqueda requerido")

    def update_medication(self):
        """Actualizar medicamento"""
        self.print_header("ACTUALIZAR MEDICAMENTO")

        med_id = input("ID del medicamento: ") or self.test_data.get('last_medication_id', '')

        if not med_id:
            self.print_warning("ID de medicamento requerido")
            return

        print("Ingresa los nuevos datos (deja vacío para no cambiar):")
        description = input("Descripción: ")
        unit_price = input("Precio unitario: ")
        supplier = input("Proveedor: ")
        minimum_stock_alert = input("Alerta de stock mínimo: ")

        data = {}
        if description: data['description'] = description
        if unit_price:
            try:
                data['unit_price'] = float(unit_price)
            except:
                pass
        if supplier: data['supplier'] = supplier
        if minimum_stock_alert:
            try:
                data['minimum_stock_alert'] = int(minimum_stock_alert)
            except:
                pass

        if data:
            self.make_request('PUT', f'http://localhost:5005/inventory/medications/{med_id}', data)
        else:
            self.print_warning("No se ingresaron cambios")

    def list_all_medications(self):
        """Listar todos los medicamentos"""
        self.print_header("LISTAR MEDICAMENTOS")

        include_inactive = input("¿Incluir inactivos? (y/N): ").lower() == 'y'
        category = input("Filtrar por categoría (opcional): ")

        url = 'http://localhost:5005/inventory/medications'
        params = []

        if include_inactive:
            params.append('include_inactive=true')
        if category:
            params.append(f'category={category}')

        if params:
            url += '?' + '&'.join(params)

        self.make_request('GET', url)

    def deactivate_medication(self):
        """Desactivar medicamento"""
        self.print_header("DESACTIVAR MEDICAMENTO")

        med_id = input("ID del medicamento: ") or self.test_data.get('last_medication_id', '')

        if med_id:
            self.make_request('PUT', f'http://localhost:5005/inventory/medications/{med_id}/deactivate')
        else:
            self.print_warning("ID de medicamento requerido")

    def test_stock_management(self):
        """Testing de gestión de stock"""
        while True:
            self.print_header("INVENTORY SERVICE - GESTIÓN DE STOCK")
            print("1. Agregar Stock (Compra)")
            print("2. Reducir Stock (Prescripción/Venta)")
            print("3. Ver Movimientos de Stock")
            print("4. Actualizar Stock Manual")
            print("0. Volver")

            choice = input(f"\n{Colors.CYAN}Selecciona una opción: {Colors.RESET}")

            if choice == '0':
                break
            elif choice == '1':
                self.add_stock()
            elif choice == '2':
                self.reduce_stock()
            elif choice == '3':
                self.view_stock_movements()
            elif choice == '4':
                self.update_stock_manual()

    def add_stock(self):
        """Agregar stock"""
        self.print_header("AGREGAR STOCK")

        med_id = input("ID del medicamento: ") or self.test_data.get('last_medication_id', '')
        quantity = input("Cantidad a agregar: ")
        reason = input("Razón (ej: Compra a proveedor): ")
        unit_cost = input("Costo unitario (opcional): ")

        data = {
            'medication_id': med_id,
            'quantity': int(quantity),
            'reason': reason,
            'user_id': 'admin-user'
        }

        if unit_cost:
            try:
                data['unit_cost'] = float(unit_cost)
            except:
                pass

        self.make_request('POST', 'http://localhost:5005/inventory/add-stock', data)

    def reduce_stock(self):
        """Reducir stock"""
        self.print_header("REDUCIR STOCK")

        med_id = input("ID del medicamento: ") or self.test_data.get('last_medication_id', '')
        quantity = input("Cantidad a reducir: ")
        reason = input("Razón (ej: Prescripción médica): ")
        reference_id = input("ID de referencia (opcional): ")

        data = {
            'medication_id': med_id,
            'quantity': int(quantity),
            'reason': reason,
            'user_id': 'vet-user'
        }

        if reference_id:
            data['reference_id'] = reference_id

        self.make_request('POST', 'http://localhost:5005/inventory/reduce-stock', data)

    def view_stock_movements(self):
        """Ver movimientos de stock"""
        self.print_header("MOVIMIENTOS DE STOCK")

        med_id = input("ID del medicamento (opcional): ") or self.test_data.get('last_medication_id', '')
        start_date = input("Fecha inicio (YYYY-MM-DD, opcional): ")
        end_date = input("Fecha fin (YYYY-MM-DD, opcional): ")
        limit = input("Límite de resultados (opcional): ")

        url = 'http://localhost:5005/inventory/movements'
        params = []

        if med_id:
            params.append(f'medication_id={med_id}')
        if start_date:
            params.append(f'start_date={start_date}')
        if end_date:
            params.append(f'end_date={end_date}')
        if limit:
            params.append(f'limit={limit}')

        if params:
            url += '?' + '&'.join(params)

        self.make_request('GET', url)

    def update_stock_manual(self):
        """Actualizar stock manualmente"""
        self.print_header("ACTUALIZAR STOCK MANUAL")

        med_id = input("ID del medicamento: ") or self.test_data.get('last_medication_id', '')
        quantity_change = input("Cambio en cantidad (positivo/negativo): ")
        reason = input("Razón: ")

        data = {
            'medication_id': med_id,
            'quantity_change': int(quantity_change),
            'reason': reason,
            'user_id': 'admin-user'
        }

        self.make_request('PUT', 'http://localhost:5005/inventory/update-stock', data)

    def test_alerts_reports(self):
        """Testing de alertas y reportes"""
        while True:
            self.print_header("INVENTORY SERVICE - ALERTAS Y REPORTES")
            print("1. Ver Medicamentos con Stock Bajo")
            print("2. Ver Medicamentos Próximos a Vencer")
            print("3. Verificar Alertas de Vencimiento")
            print("4. Resumen del Inventario")
            print("5. Reporte de Movimientos")
            print("6. Estadísticas del Inventario")
            print("7. Ver Categorías")
            print("0. Volver")

            choice = input(f"\n{Colors.CYAN}Selecciona una opción: {Colors.RESET}")

            if choice == '0':
                break
            elif choice == '1':
                self.view_low_stock()
            elif choice == '2':
                self.view_expiring_medications()
            elif choice == '3':
                self.check_expiration_alerts()
            elif choice == '4':
                self.view_inventory_summary()
            elif choice == '5':
                self.view_movement_report()
            elif choice == '6':
                self.view_inventory_stats()
            elif choice == '7':
                self.view_categories()

    def view_low_stock(self):
        """Ver medicamentos con stock bajo"""
        self.print_header("MEDICAMENTOS CON STOCK BAJO")
        self.make_request('GET', 'http://localhost:5005/inventory/alerts/low-stock')

    def view_expiring_medications(self):
        """Ver medicamentos próximos a vencer"""
        self.print_header("MEDICAMENTOS PRÓXIMOS A VENCER")

        days_threshold = input("Días de anticipación (default: 30): ") or "30"

        self.make_request('GET', f'http://localhost:5005/inventory/alerts/expiring?days={days_threshold}')

    def check_expiration_alerts(self):
        """Verificar alertas de vencimiento"""
        self.print_header("VERIFICAR ALERTAS DE VENCIMIENTO")

        days_threshold = input("Días de anticipación (default: 30): ") or "30"

        data = {
            'days_threshold': int(days_threshold)
        }

        self.make_request('POST', 'http://localhost:5005/inventory/alerts/check-expiration', data)

    def view_inventory_summary(self):
        """Ver resumen del inventario"""
        self.print_header("RESUMEN DEL INVENTARIO")
        self.make_request('GET', 'http://localhost:5005/inventory/summary')

    def view_movement_report(self):
        """Ver reporte de movimientos"""
        self.print_header("REPORTE DE MOVIMIENTOS")

        start_date = input("Fecha inicio (YYYY-MM-DD, opcional): ")
        end_date = input("Fecha fin (YYYY-MM-DD, opcional): ")

        url = 'http://localhost:5005/inventory/reports/movements'
        params = []

        if start_date:
            params.append(f'start_date={start_date}')
        if end_date:
            params.append(f'end_date={end_date}')

        if params:
            url += '?' + '&'.join(params)

        self.make_request('GET', url)

    def view_inventory_stats(self):
        """Ver estadísticas del inventario"""
        self.print_header("ESTADÍSTICAS DEL INVENTARIO")
        self.make_request('GET', 'http://localhost:5005/inventory/stats')

    def view_categories(self):
        """Ver categorías disponibles"""
        self.print_header("CATEGORÍAS DE MEDICAMENTOS")
        self.make_request('GET', 'http://localhost:5005/inventory/categories')

    def inventory_complete_test(self):
        """Test completo del inventory service"""
        self.print_header("INVENTORY SERVICE - TEST COMPLETO")

        # 1. Health check
        print(f"\n{Colors.BLUE}1. Health Check{Colors.RESET}")
        self.make_request('GET', 'http://localhost:5005/health')

        # 2. Crear medicamento de prueba
        print(f"\n{Colors.BLUE}2. Creando medicamento de prueba{Colors.RESET}")
        med_data = {
            'name': 'Ibuprofeno 400mg',
            'description': 'Antiinflamatorio no esteroideo',
            'stock_quantity': 50,
            'unit_price': 1200,
            'expiration_date': '2025-06-15',
            'supplier': 'Laboratorios Farmacéuticos SA',
            'minimum_stock_alert': 15,
            'category': 'Analgésico',
            'presentation': 'Comprimidos',
            'concentration': '400mg',
            'laboratory': 'LabFarma'
        }

        med_response = self.make_request('POST', 'http://localhost:5005/inventory/medications', med_data)

        if med_response.get('success'):
            med_id = med_response['medication']['id']

            # 3. Agregar stock
            print(f"\n{Colors.BLUE}3. Agregando stock{Colors.RESET}")
            add_stock_data = {
                'medication_id': med_id,
                'quantity': 25,
                'reason': 'Compra a proveedor',
                'unit_cost': 1150,
                'user_id': 'admin-user'
            }

            self.make_request('POST', 'http://localhost:5005/inventory/add-stock', add_stock_data)

            # 4. Reducir stock
            print(f"\n{Colors.BLUE}4. Reduciendo stock{Colors.RESET}")
            reduce_stock_data = {
                'medication_id': med_id,
                'quantity': 5,
                'reason': 'Prescripción médica',
                'reference_id': 'prescription-123',
                'user_id': 'vet-user'
            }

            self.make_request('POST', 'http://localhost:5005/inventory/reduce-stock', reduce_stock_data)

            # 5. Ver movimientos
            print(f"\n{Colors.BLUE}5. Viendo movimientos de stock{Colors.RESET}")
            self.make_request('GET', f'http://localhost:5005/inventory/movements?medication_id={med_id}')

            # 6. Ver resumen
            print(f"\n{Colors.BLUE}6. Obteniendo resumen del inventario{Colors.RESET}")
            self.make_request('GET', 'http://localhost:5005/inventory/summary')

            # 7. Ver estadísticas
            print(f"\n{Colors.BLUE}7. Obteniendo estadísticas{Colors.RESET}")
            self.make_request('GET', 'http://localhost:5005/inventory/stats')

            self.print_success("Test completo de Inventory Service finalizado")

    # =============== APPOINTMENT SERVICE TESTS ===============

    def test_appointment_service(self):
        """Menú de testing para Appointment Service"""
        while True:
            self.print_header("APPOINTMENT SERVICE - TESTING")
            print("1. Health Check")
            print("2. Gestión de Citas")
            print("3. Disponibilidad de Horarios")
            print("4. Test Completo Appointment Service")
            print("0. Volver al menú principal")

            choice = input(f"\n{Colors.CYAN}Selecciona una opción: {Colors.RESET}")

            if choice == '0':
                break
            elif choice == '1':
                self.appointment_health_check()
            elif choice == '2':
                self.test_appointment_management()
            elif choice == '3':
                self.test_availability_slots()
            elif choice == '4':
                self.appointment_complete_test()

    def appointment_health_check(self):
        """Health check del appointment service"""
        self.print_header("APPOINTMENT SERVICE - HEALTH CHECK")
        self.make_request('GET', 'http://localhost:5002/health')

    def test_appointment_management(self):
        """Testing de gestión de citas"""
        while True:
            self.print_header("APPOINTMENT SERVICE - GESTIÓN DE CITAS")
            print("1. Crear Cita")
            print("2. Ver Citas por Veterinario")
            print("3. Ver Citas por Cliente")
            print("4. Actualizar Cita")
            print("5. Confirmar Cita")
            print("6. Cancelar Cita")
            print("7. Completar Cita")
            print("8. Citas de Hoy")
            print("0. Volver")

            choice = input(f"\n{Colors.CYAN}Selecciona una opción: {Colors.RESET}")

            if choice == '0':
                break
            elif choice == '1':
                self.create_appointment()
            elif choice == '2':
                self.get_appointments_by_vet()
            elif choice == '3':
                self.get_appointments_by_client()
            elif choice == '4':
                self.update_appointment()
            elif choice == '5':
                self.confirm_appointment()
            elif choice == '6':
                self.cancel_appointment()
            elif choice == '7':
                self.complete_appointment()
            elif choice == '8':
                self.get_today_appointments()

    def create_appointment(self):
        """Crear nueva cita"""
        self.print_header("CREAR CITA")

        pet_id = input("ID de la mascota: ") or self.test_data.get('last_pet_id', '')
        veterinarian_id = input("ID del veterinario: ")
        client_id = input("ID del cliente: ")
        appointment_date = input("Fecha de la cita (YYYY-MM-DD): ")
        appointment_time = input("Hora de la cita (HH:MM): ")
        reason = input("Motivo de la consulta: ")

        data = {
            'pet_id': pet_id,
            'veterinarian_id': veterinarian_id,
            'client_id': client_id,
            'appointment_date': appointment_date,
            'appointment_time': appointment_time,
            'reason': reason
        }

        response = self.make_request('POST', 'http://localhost:5002/appointments/create', data)

        if response.get('success') and response.get('appointment'):
            self.test_data['last_appointment_id'] = response['appointment']['id']
            self.print_success(f"Cita creada con ID: {response['appointment']['id']}")

    def get_appointments_by_vet(self):
        """Ver citas por veterinario"""
        self.print_header("CITAS POR VETERINARIO")

        vet_id = input("ID del veterinario: ")
        start_date = input("Fecha inicio (YYYY-MM-DD, opcional): ")
        end_date = input("Fecha fin (YYYY-MM-DD, opcional): ")

        url = f'http://localhost:5002/appointments/by-veterinarian/{vet_id}'
        params = []

        if start_date:
            params.append(f'start_date={start_date}')
        if end_date:
            params.append(f'end_date={end_date}')

        if params:
            url += '?' + '&'.join(params)

        self.make_request('GET', url)

    def get_appointments_by_client(self):
        """Ver citas por cliente"""
        self.print_header("CITAS POR CLIENTE")

        client_id = input("ID del cliente: ")
        status = input("Estado (opcional - scheduled/confirmed/completed/cancelled): ")

        url = f'http://localhost:5002/appointments/by-client/{client_id}'

        if status:
            url += f'?status={status}'

        self.make_request('GET', url)

    def update_appointment(self):
        """Actualizar cita"""
        self.print_header("ACTUALIZAR CITA")

        appointment_id = input("ID de la cita: ") or self.test_data.get('last_appointment_id', '')

        if not appointment_id:
            self.print_warning("ID de cita requerido")
            return

        print("Ingresa los nuevos datos (deja vacío para no cambiar):")
        appointment_date = input("Nueva fecha (YYYY-MM-DD): ")
        appointment_time = input("Nueva hora (HH:MM): ")
        reason = input("Nuevo motivo: ")
        notes = input("Notas: ")

        data = {}
        if appointment_date: data['appointment_date'] = appointment_date
        if appointment_time: data['appointment_time'] = appointment_time
        if reason: data['reason'] = reason
        if notes: data['notes'] = notes

        if data:
            self.make_request('PUT', f'http://localhost:5002/appointments/update/{appointment_id}', data)
        else:
            self.print_warning("No se ingresaron cambios")

    def confirm_appointment(self):
        """Confirmar cita"""
        self.print_header("CONFIRMAR CITA")

        appointment_id = input("ID de la cita: ") or self.test_data.get('last_appointment_id', '')

        if appointment_id:
            self.make_request('PUT', f'http://localhost:5002/appointments/confirm/{appointment_id}')
        else:
            self.print_warning("ID de cita requerido")

    def cancel_appointment(self):
        """Cancelar cita"""
        self.print_header("CANCELAR CITA")

        appointment_id = input("ID de la cita: ") or self.test_data.get('last_appointment_id', '')

        if appointment_id:
            self.make_request('PUT', f'http://localhost:5002/appointments/cancel/{appointment_id}')
        else:
            self.print_warning("ID de cita requerido")

    def complete_appointment(self):
        """Completar cita"""
        self.print_header("COMPLETAR CITA")

        appointment_id = input("ID de la cita: ") or self.test_data.get('last_appointment_id', '')

        if appointment_id:
            self.make_request('PUT', f'http://localhost:5002/appointments/complete/{appointment_id}')
        else:
            self.print_warning("ID de cita requerido")

    def get_today_appointments(self):
        """Ver citas de hoy"""
        self.print_header("CITAS DE HOY")
        self.make_request('GET', 'http://localhost:5002/appointments/today')

    def test_availability_slots(self):
        """Testing de disponibilidad de horarios"""
        self.print_header("DISPONIBILIDAD DE HORARIOS")

        veterinarian_id = input("ID del veterinario: ")
        date = input("Fecha (YYYY-MM-DD): ")

        if veterinarian_id and date:
            self.make_request('GET',
                              f'http://localhost:5002/appointments/available-slots?veterinarian_id={veterinarian_id}&date={date}')
        else:
            self.print_warning("ID de veterinario y fecha requeridos")

    def appointment_complete_test(self):
        """Test completo del appointment service"""
        self.print_header("APPOINTMENT SERVICE - TEST COMPLETO")

        # 1. Health check
        print(f"\n{Colors.BLUE}1. Health Check{Colors.RESET}")
        self.make_request('GET', 'http://localhost:5002/health')

        # 2. Ver slots disponibles
        print(f"\n{Colors.BLUE}2. Verificando slots disponibles{Colors.RESET}")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        self.make_request('GET',
                          f'http://localhost:5002/appointments/available-slots?veterinarian_id=test-vet-id&date={tomorrow}')

        # 3. Crear cita de prueba
        print(f"\n{Colors.BLUE}3. Creando cita de prueba{Colors.RESET}")
        appointment_data = {
            'pet_id': self.test_data.get('last_pet_id', 'test-pet-id'),
            'veterinarian_id': 'test-vet-id',
            'client_id': 'test-client-id',
            'appointment_date': tomorrow,
            'appointment_time': '10:00',
            'reason': 'Consulta general de prueba'
        }

        appointment_response = self.make_request('POST', 'http://localhost:5002/appointments/create', appointment_data)

        if appointment_response.get('success'):
            appointment_id = appointment_response['appointment']['id']

            # 4. Confirmar cita
            print(f"\n{Colors.BLUE}4. Confirmando cita{Colors.RESET}")
            self.make_request('PUT', f'http://localhost:5002/appointments/confirm/{appointment_id}')

            # 5. Ver citas del veterinario
            print(f"\n{Colors.BLUE}5. Viendo citas del veterinario{Colors.RESET}")
            self.make_request('GET',
                              f'http://localhost:5002/appointments/by-veterinarian/test-vet-id?start_date={tomorrow}&end_date={tomorrow}')

            # 6. Actualizar cita
            print(f"\n{Colors.BLUE}6. Actualizando cita{Colors.RESET}")
            update_data = {
                'notes': 'Cita de prueba actualizada',
                'reason': 'Consulta general - seguimiento'
            }
            self.make_request('PUT', f'http://localhost:5002/appointments/update/{appointment_id}', update_data)

            # 7. Completar cita
            print(f"\n{Colors.BLUE}7. Completando cita{Colors.RESET}")
            self.make_request('PUT', f'http://localhost:5002/appointments/complete/{appointment_id}')

            self.print_success("Test completo de Appointment Service finalizado")

    # =============== NOTIFICATION SERVICE TESTS ===============

    def test_notification_service(self):
        """Menú de testing para Notification Service"""
        while True:
            self.print_header("NOTIFICATION SERVICE - TESTING")
            print("1. Health Check")
            print("2. Test de Email")
            print("3. Test de WhatsApp")
            print("4. Recordatorio de Cita")
            print("5. Alerta de Nueva Cita")
            print("6. Alerta de Inventario")
            print("7. Gestión de Notificaciones")
            print("8. Test Completo Notification Service")
            print("0. Volver al menú principal")

            choice = input(f"\n{Colors.CYAN}Selecciona una opción: {Colors.RESET}")

            if choice == '0':
                break
            elif choice == '1':
                self.notification_health_check()
            elif choice == '2':
                self.test_email()
            elif choice == '3':
                self.test_whatsapp()
            elif choice == '4':
                self.test_appointment_reminder()
            elif choice == '5':
                self.test_appointment_alert()
            elif choice == '6':
                self.test_inventory_alert()
            elif choice == '7':
                self.test_notification_management()
            elif choice == '8':
                self.notification_complete_test()

    def notification_health_check(self):
        """Health check del notification service"""
        self.print_header("NOTIFICATION SERVICE - HEALTH CHECK")
        self.make_request('GET', 'http://localhost:5003/health')

    def test_email(self):
        """Test de email"""
        self.print_header("TEST DE EMAIL")

        email = input("Email destino: ")

        data = {
            'email': email
        }

        self.make_request('POST', 'http://localhost:5003/notifications/test-email', data)

    def test_whatsapp(self):
        """Test de WhatsApp"""
        self.print_header("TEST DE WHATSAPP")

        phone = input("Número de teléfono (con código país): ")

        data = {
            'phone': phone
        }

        self.make_request('POST', 'http://localhost:5003/notifications/test-whatsapp', data)

    def test_appointment_reminder(self):
        """Test de recordatorio de cita"""
        self.print_header("RECORDATORIO DE CITA")

        user_id = input("ID del usuario: ")
        email = input("Email (opcional): ")
        phone = input("Teléfono (opcional): ")

        print("\nDatos de la cita:")
        date = input("Fecha (YYYY-MM-DD): ")
        time = input("Hora (HH:MM): ")
        vet_name = input("Nombre del veterinario: ")
        pet_name = input("Nombre de la mascota: ")
        reason = input("Motivo: ")

        data = {
            'user_id': user_id,
            'email': email if email else None,
            'phone': phone if phone else None,
            'appointment_details': {
                'date': date,
                'time': time,
                'veterinarian_name': vet_name,
                'pet_name': pet_name,
                'reason': reason
            }
        }

        self.make_request('POST', 'http://localhost:5003/notifications/send-reminder', data)

    def test_appointment_alert(self):
        """Test de alerta de nueva cita"""
        self.print_header("ALERTA DE NUEVA CITA")

        print("Datos de la cita:")
        date = input("Fecha (YYYY-MM-DD): ")
        time = input("Hora (HH:MM): ")
        vet_name = input("Nombre del veterinario: ")
        client_name = input("Nombre del cliente: ")
        pet_name = input("Nombre de la mascota: ")
        reason = input("Motivo: ")

        data = {
            'appointment_details': {
                'date': date,
                'time': time,
                'veterinarian_name': vet_name,
                'client_name': client_name,
                'pet_name': pet_name,
                'reason': reason
            },
            'receptionist_emails': ['recepcion@veterinariaclinic.com']
        }

        self.make_request('POST', 'http://localhost:5003/notifications/appointment-alert', data)

    def test_inventory_alert(self):
        """Test de alerta de inventario"""
        self.print_header("ALERTA DE INVENTARIO")

        print("Tipos de alerta:")
        print("1. Stock bajo (low_stock)")
        print("2. Próximo a vencer (expiration)")

        alert_choice = input("Selecciona tipo (1-2): ")
        alert_type = 'low_stock' if alert_choice == '1' else 'expiration'

        if alert_type == 'low_stock':
            med_name = input("Nombre del medicamento: ")
            stock_quantity = input("Cantidad en stock: ")

            data = {
                'alert_type': alert_type,
                'medication_details': {
                    'name': med_name,
                    'stock_quantity': int(stock_quantity)
                },
                'admin_emails': ['admin@veterinariaclinic.com']
            }
        else:
            med_name = input("Nombre del medicamento: ")
            expiration_date = input("Fecha de vencimiento (YYYY-MM-DD): ")

            data = {
                'alert_type': alert_type,
                'medication_details': {
                    'name': med_name,
                    'expiration_date': expiration_date
                },
                'admin_emails': ['admin@veterinariaclinic.com']
            }

        self.make_request('POST', 'http://localhost:5003/notifications/inventory-alert', data)

    def test_notification_management(self):
        """Test de gestión de notificaciones"""
        while True:
            self.print_header("GESTIÓN DE NOTIFICACIONES")
            print("1. Ver Notificaciones de Usuario")
            print("2. Marcar Notificación como Leída")
            print("3. Enviar Confirmación de Cita")
            print("4. Enviar Cancelación de Cita")
            print("0. Volver")

            choice = input(f"\n{Colors.CYAN}Selecciona una opción: {Colors.RESET}")

            if choice == '0':
                break
            elif choice == '1':
                self.get_user_notifications()
            elif choice == '2':
                self.mark_notification_read()
            elif choice == '3':
                self.send_appointment_confirmation()
            elif choice == '4':
                self.send_appointment_cancellation()

    def get_user_notifications(self):
        """Ver notificaciones de usuario"""
        self.print_header("NOTIFICACIONES DE USUARIO")

        user_id = input("ID del usuario: ")
        unread_only = input("¿Solo no leídas? (y/N): ").lower() == 'y'

        url = f'http://localhost:5003/notifications/user/{user_id}'

        if unread_only:
            url += '?unread_only=true'

        self.make_request('GET', url)

    def mark_notification_read(self):
        """Marcar notificación como leída"""
        self.print_header("MARCAR COMO LEÍDA")

        notification_id = input("ID de la notificación: ")
        user_id = input("ID del usuario: ")

        data = {
            'user_id': user_id
        }

        self.make_request('PUT', f'http://localhost:5003/notifications/mark-read/{notification_id}', data)

    def send_appointment_confirmation(self):
        """Enviar confirmación de cita"""
        self.print_header("CONFIRMACIÓN DE CITA")

        email = input("Email (opcional): ")
        phone = input("Teléfono (opcional): ")

        print("\nDatos de la cita:")
        date = input("Fecha (YYYY-MM-DD): ")
        time = input("Hora (HH:MM): ")
        vet_name = input("Nombre del veterinario: ")
        pet_name = input("Nombre de la mascota: ")

        data = {
            'email': email if email else None,
            'phone': phone if phone else None,
            'appointment_details': {
                'date': date,
                'time': time,
                'veterinarian_name': vet_name,
                'pet_name': pet_name
            }
        }

        self.make_request('POST', 'http://localhost:5003/notifications/send-confirmation', data)

    def send_appointment_cancellation(self):
        """Enviar cancelación de cita"""
        self.print_header("CANCELACIÓN DE CITA")

        email = input("Email (opcional): ")
        phone = input("Teléfono (opcional): ")

        print("\nDatos de la cita:")
        date = input("Fecha (YYYY-MM-DD): ")
        time = input("Hora (HH:MM): ")

        data = {
            'email': email if email else None,
            'phone': phone if phone else None,
            'appointment_details': {
                'date': date,
                'time': time
            }
        }

        self.make_request('POST', 'http://localhost:5003/notifications/send-cancellation', data)

    def notification_complete_test(self):
        """Test completo del notification service"""
        self.print_header("NOTIFICATION SERVICE - TEST COMPLETO")

        # 1. Health check
        print(f"\n{Colors.BLUE}1. Health Check{Colors.RESET}")
        self.make_request('GET', 'http://localhost:5003/health')

        # 2. Test de email
        print(f"\n{Colors.BLUE}2. Test de email{Colors.RESET}")
        self.make_request('POST', 'http://localhost:5003/notifications/test-email', {'email': 'test@example.com'})

        # 3. Test de WhatsApp
        print(f"\n{Colors.BLUE}3. Test de WhatsApp{Colors.RESET}")
        self.make_request('POST', 'http://localhost:5003/notifications/test-whatsapp', {'phone': '+1234567890'})

        # 4. Recordatorio de cita
        print(f"\n{Colors.BLUE}4. Enviando recordatorio de cita{Colors.RESET}")
        reminder_data = {
            'user_id': 'test-user-id',
            'email': 'cliente@example.com',
            'phone': '+1234567890',
            'appointment_details': {
                'date': '2024-12-25',
                'time': '10:00',
                'veterinarian_name': 'Juan Pérez',
                'pet_name': 'Firulais',
                'reason': 'Consulta general'
            }
        }

        self.make_request('POST', 'http://localhost:5003/notifications/send-reminder', reminder_data)

        # 5. Alerta de nueva cita
        print(f"\n{Colors.BLUE}5. Enviando alerta de nueva cita{Colors.RESET}")
        alert_data = {
            'appointment_details': {
                'date': '2024-12-25',
                'time': '10:00',
                'veterinarian_name': 'Juan Pérez',
                'client_name': 'María García',
                'pet_name': 'Firulais',
                'reason': 'Consulta general'
            },
            'receptionist_emails': ['recepcion@veterinariaclinic.com']
        }

        self.make_request('POST', 'http://localhost:5003/notifications/appointment-alert', alert_data)

        # 6. Alerta de inventario
        print(f"\n{Colors.BLUE}6. Enviando alerta de inventario{Colors.RESET}")
        inventory_alert_data = {
            'alert_type': 'low_stock',
            'medication_details': {
                'name': 'Amoxicilina 500mg',
                'stock_quantity': 5
            },
            'admin_emails': ['admin@veterinariaclinic.com']
        }

        self.make_request('POST', 'http://localhost:5003/notifications/inventory-alert', inventory_alert_data)

        self.print_success("Test completo de Notification Service finalizado")

    # =============== INTEGRATION TESTS ===============

    def run_full_integration_test(self):
        """Ejecutar test de integración completo"""
        self.print_header("TEST DE INTEGRACIÓN COMPLETO")

        print(f"{Colors.YELLOW}Este test simulará un flujo completo del sistema:{Colors.RESET}")
        print("1. Registro de usuario")
        print("2. Creación de mascota")
        print("3. Creación de medicamento")
        print("4. Agendamiento de cita")
        print("5. Creación de historia clínica")
        print("6. Prescripción con actualización de inventario")
        print("7. Completar cita")
        print("8. Envío de notificaciones")

        confirm = input(f"\n{Colors.CYAN}¿Continuar con el test? (y/N): {Colors.RESET}")

        if confirm.lower() != 'y':
            return

        # 1. Registrar cliente
        print(f"\n{Colors.BLUE}PASO 1: Registrando cliente{Colors.RESET}")
        client_data = {
            'email': f'integration_test_{int(time.time())}@example.com',
            'password': 'test123',
            'first_name': 'Cliente',
            'last_name': 'Integración',
            'phone': '+1234567890',
            'role': 'client'
        }

        client_response = self.make_request('POST', 'http://localhost:5001/auth/register', client_data)

        if not client_response.get('success'):
            self.print_error("Error registrando cliente. Abortando test.")
            return

        client_id = client_response.get('user_id')

        # 2. Registrar veterinario
        print(f"\n{Colors.BLUE}PASO 2: Registrando veterinario{Colors.RESET}")
        vet_data = {
            'email': f'vet_integration_{int(time.time())}@example.com',
            'password': 'vet123',
            'first_name': 'Dr. Juan',
            'last_name': 'Pérez',
            'phone': '+1234567891',
            'role': 'veterinarian'
        }

        vet_response = self.make_request('POST', 'http://localhost:5001/auth/register', vet_data)

        if not vet_response.get('success'):
            self.print_error("Error registrando veterinario. Abortando test.")
            return

        vet_id = vet_response.get('user_id')

        # 3. Crear mascota
        print(f"\n{Colors.BLUE}PASO 3: Creando mascota{Colors.RESET}")
        pet_data = {
            'owner_id': client_id,
            'name': 'Max',
            'species': 'Perro',
            'breed': 'Golden Retriever',
            'birth_date': '2022-01-15',
            'weight': 25.5,
            'gender': 'Macho'
        }

        pet_response = self.make_request('POST', 'http://localhost:5004/medical/pets', pet_data)

        if not pet_response.get('success'):
            self.print_error("Error creando mascota. Abortando test.")
            return

        pet_id = pet_response['pet']['id']

        # 4. Crear medicamento
        print(f"\n{Colors.BLUE}PASO 4: Creando medicamento{Colors.RESET}")
        med_data = {
            'name': 'Amoxicilina 500mg',
            'description': 'Antibiótico para infecciones',
            'stock_quantity': 100,
            'unit_price': 2500,
            'category': 'Antibiótico',
            'supplier': 'FarmaVet'
        }

        med_response = self.make_request('POST', 'http://localhost:5005/inventory/medications', med_data)

        if not med_response.get('success'):
            self.print_error("Error creando medicamento. Abortando test.")
            return

        med_id = med_response['medication']['id']

        # 5. Agendar cita
        print(f"\n{Colors.BLUE}PASO 5: Agendando cita{Colors.RESET}")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        appointment_data = {
            'pet_id': pet_id,
            'veterinarian_id': vet_id,
            'client_id': client_id,
            'appointment_date': tomorrow,
            'appointment_time': '14:00',
            'reason': 'Consulta de integración'
        }

        appointment_response = self.make_request('POST', 'http://localhost:5002/appointments/create', appointment_data)

        if not appointment_response.get('success'):
            self.print_error("Error agendando cita. Abortando test.")
            return

        appointment_id = appointment_response['appointment']['id']

        # 6. Crear historia clínica
        print(f"\n{Colors.BLUE}PASO 6: Creando historia clínica{Colors.RESET}")
        record_data = {
            'pet_id': pet_id,
            'veterinarian_id': vet_id,
            'appointment_id': appointment_id,
            'symptoms_description': 'Infección respiratoria',
            'physical_examination': 'Fiebre, congestión nasal',
            'diagnosis': 'Infección bacteriana del tracto respiratorio superior',
            'treatment': 'Antibióticos y reposo',
            'weight_at_visit': 25.0,
            'temperature': 39.2
        }

        record_response = self.make_request('POST', 'http://localhost:5004/medical/records', record_data)

        if not record_response.get('success'):
            self.print_error("Error creando historia clínica. Abortando test.")
            return

        record_id = record_response['medical_record']['id']

        # 7. Agregar prescripción
        print(f"\n{Colors.BLUE}PASO 7: Agregando prescripción{Colors.RESET}")
        prescription_data = {
            'medical_record_id': record_id,
            'medication_id': med_id,
            'medication_name': 'Amoxicilina 500mg',
            'dosage': '1 comprimido',
            'frequency': 'Cada 8 horas',
            'duration': '10 días',
            'quantity_prescribed': 30
        }

        self.make_request('POST', 'http://localhost:5004/medical/prescriptions', prescription_data)

        # 8. Completar historia clínica y cita
        print(f"\n{Colors.BLUE}PASO 8: Completando historia clínica{Colors.RESET}")
        self.make_request('PUT', f'http://localhost:5004/medical/records/{record_id}/complete')

        # 9. Verificar stock actualizado
        print(f"\n{Colors.BLUE}PASO 9: Verificando actualización de stock{Colors.RESET}")
        self.make_request('GET', f'http://localhost:5005/inventory/medications/{med_id}')

        # 10. Enviar recordatorio
        print(f"\n{Colors.BLUE}PASO 10: Enviando recordatorio de seguimiento{Colors.RESET}")
        reminder_data = {
            'user_id': client_id,
            'email': client_data['email'],
            'appointment_details': {
                'date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
                'time': '14:00',
                'veterinarian_name': f"{vet_data['first_name']} {vet_data['last_name']}",
                'pet_name': pet_data['name'],
                'reason': 'Seguimiento post-tratamiento'
            }
        }

        self.make_request('POST', 'http://localhost:5003/notifications/send-reminder', reminder_data)

        self.print_success("🎉 TEST DE INTEGRACIÓN COMPLETO FINALIZADO EXITOSAMENTE 🎉")
        print(f"\n{Colors.GREEN}Resumen del test:{Colors.RESET}")
        print(f"• Cliente creado: {client_id}")
        print(f"• Veterinario creado: {vet_id}")
        print(f"• Mascota creada: {pet_id}")
        print(f"• Medicamento creado: {med_id}")
        print(f"• Cita agendada: {appointment_id}")
        print(f"• Historia clínica creada: {record_id}")
        print(f"• Prescripción agregada y stock actualizado")
        print(f"• Recordatorio enviado")

    # =============== MAIN MENU ===============

    def show_main_menu(self):
        """Mostrar menú principal"""
        while True:
            self.print_header("SISTEMA DE CLÍNICA VETERINARIA - TESTING SUITE")

            # Mostrar estado del usuario actual
            if self.current_user:
                print(
                    f"{Colors.GREEN}👤 Usuario actual: {self.current_user.get('name')} ({self.current_user.get('role')}){Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}👤 No hay usuario logueado{Colors.RESET}")

            print("\n📋 GESTIÓN DE SERVICIOS:")
            print("1. Iniciar Todos los Microservicios")
            print("2. Detener Todos los Microservicios")
            print("3. Ver Estado de Servicios")
            print("4. Verificar Prerequisitos")

            print("\n🧪 TESTING POR MICROSERVICIO:")
            print("5. Auth Service (Autenticación)")
            print("6. Medical Service (Médico)")
            print("7. Inventory Service (Inventario)")
            print("8. Appointment Service (Citas)")
            print("9. Notification Service (Notificaciones)")

            print("\n🔗 TESTING AVANZADO:")
            print("10. Test de Integración Completo")
            print("11. Test de Carga (Múltiples Requests)")
            print("12. Test de Conectividad Entre Servicios")

            print("\n⚙️ UTILIDADES:")
            print("13. Limpiar Datos de Prueba")
            print("14. Exportar Logs de Testing")
            print("15. Configurar Variables de Entorno")

            print(f"\n{Colors.RED}0. Salir{Colors.RESET}")

            choice = input(f"\n{Colors.CYAN}Selecciona una opción: {Colors.RESET}")

            try:
                if choice == '0':
                    self.cleanup_and_exit()
                    break
                elif choice == '1':
                    self.start_all_services()
                elif choice == '2':
                    self.stop_all_services()
                elif choice == '3':
                    self.show_services_status()
                elif choice == '4':
                    self.check_prerequisites()
                elif choice == '5':
                    self.test_auth_service()
                elif choice == '6':
                    self.test_medical_service()
                elif choice == '7':
                    self.test_inventory_service()
                elif choice == '8':
                    self.test_appointment_service()
                elif choice == '9':
                    self.test_notification_service()
                elif choice == '10':
                    self.run_full_integration_test()
                elif choice == '11':
                    self.run_load_test()
                elif choice == '12':
                    self.test_service_connectivity()
                elif choice == '13':
                    self.cleanup_test_data()
                elif choice == '14':
                    self.export_test_logs()
                elif choice == '15':
                    self.configure_environment()
                else:
                    self.print_warning("Opción no válida")

            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Operación cancelada por el usuario{Colors.RESET}")
            except Exception as e:
                self.print_error(f"Error inesperado: {str(e)}")

            input(f"\n{Colors.CYAN}Presiona Enter para continuar...{Colors.RESET}")

    def run_load_test(self):
        """Ejecutar test de carga"""
        self.print_header("TEST DE CARGA")

        print("Selecciona el tipo de test de carga:")
        print("1. Health checks masivos")
        print("2. Registro de usuarios múltiples")
        print("3. Consultas de medicamentos simultáneas")
        print("4. Creación de citas concurrentes")

        choice = input(f"\n{Colors.CYAN}Selecciona una opción: {Colors.RESET}")
        requests_count = int(input("Número de requests: ") or "10")

        import concurrent.futures
        import threading

        def make_concurrent_request(request_num):
            if choice == '1':
                # Health checks
                services = ['5001', '5002', '5003', '5004', '5005']
                for port in services:
                    response = self.make_request('GET', f'http://localhost:{port}/health')
                    if response.get('status') == 'healthy':
                        print(f"{Colors.GREEN}✅ Request {request_num} - Puerto {port} OK{Colors.RESET}")
                    else:
                        print(f"{Colors.RED}❌ Request {request_num} - Puerto {port} FAIL{Colors.RESET}")

            elif choice == '2':
                # Registro de usuarios
                user_data = {
                    'email': f'load_test_{request_num}_{int(time.time())}@example.com',
                    'password': 'test123',
                    'first_name': f'Usuario{request_num}',
                    'last_name': 'Test',
                    'role': 'client'
                }
                response = self.make_request('POST', 'http://localhost:5001/auth/register', user_data)
                if response.get('success'):
                    print(f"{Colors.GREEN}✅ Usuario {request_num} creado{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ Error creando usuario {request_num}{Colors.RESET}")

            elif choice == '3':
                # Consultas de medicamentos
                response = self.make_request('GET', 'http://localhost:5005/inventory/medications')
                if response.get('success'):
                    print(f"{Colors.GREEN}✅ Consulta {request_num} exitosa{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ Error en consulta {request_num}{Colors.RESET}")

            elif choice == '4':
                # Creación de citas
                tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                hour = 8 + (request_num % 8)  # Distribuir en horarios
                appointment_data = {
                    'pet_id': f'test-pet-{request_num}',
                    'veterinarian_id': 'test-vet-id',
                    'client_id': f'test-client-{request_num}',
                    'appointment_date': tomorrow,
                    'appointment_time': f'{hour:02d}:00',
                    'reason': f'Consulta de carga {request_num}'
                }
                response = self.make_request('POST', 'http://localhost:5002/appointments/create', appointment_data)
                if response.get('success'):
                    print(f"{Colors.GREEN}✅ Cita {request_num} creada{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ Error creando cita {request_num}{Colors.RESET}")

        print(f"\n{Colors.BLUE}Ejecutando {requests_count} requests concurrentes...{Colors.RESET}")

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_concurrent_request, i) for i in range(requests_count)]
            concurrent.futures.wait(futures)

        end_time = time.time()

        self.print_success(f"Test de carga completado en {end_time - start_time:.2f} segundos")

    def test_service_connectivity(self):
        """Test de conectividad entre servicios"""
        self.print_header("TEST DE CONECTIVIDAD ENTRE SERVICIOS")

        # Test 1: Auth -> Medical (verificación de token)
        print(f"\n{Colors.BLUE}1. Testing Auth -> Medical Service{Colors.RESET}")

        # Crear usuario y obtener token
        test_user = {
            'email': f'connectivity_test_{int(time.time())}@example.com',
            'password': 'test123',
            'first_name': 'Test',
            'last_name': 'Connectivity',
            'role': 'veterinarian'
        }

        user_response = self.make_request('POST', 'http://localhost:5001/auth/register', test_user)
        if user_response.get('success'):
            login_response = self.make_request('POST', 'http://localhost:5001/auth/login', {
                'email': test_user['email'],
                'password': test_user['password']
            })

            if login_response.get('success'):
                old_token = self.auth_token
                self.auth_token = login_response.get('token')

                # Probar acceso a medical service con token
                self.make_request('GET', 'http://localhost:5004/health')

                self.auth_token = old_token

        # Test 2: Medical -> Inventory (actualización de stock)
        print(f"\n{Colors.BLUE}2. Testing Medical -> Inventory Service{Colors.RESET}")

        # Crear medicamento
        med_data = {
            'name': 'Test Connectivity Med',
            'stock_quantity': 50,
            'unit_price': 1000,
            'category': 'Test'
        }

        med_response = self.make_request('POST', 'http://localhost:5005/inventory/medications', med_data)

        if med_response.get('success'):
            med_id = med_response['medication']['id']

            # Simular prescripción que debe actualizar inventario
            prescription_data = {
                'medical_record_id': 'test-record',
                'medication_id': med_id,
                'medication_name': 'Test Connectivity Med',
                'quantity_prescribed': 5
            }

            self.make_request('POST', 'http://localhost:5004/medical/prescriptions', prescription_data)

            # Verificar que el stock se actualizó
            self.make_request('GET', f'http://localhost:5005/inventory/medications/{med_id}')

        # Test 3: Appointment -> Notification (nueva cita)
        print(f"\n{Colors.BLUE}3. Testing Appointment -> Notification Service{Colors.RESET}")

        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        appointment_data = {
            'pet_id': 'test-connectivity-pet',
            'veterinarian_id': 'test-connectivity-vet',
            'client_id': 'test-connectivity-client',
            'appointment_date': tomorrow,
            'appointment_time': '15:00',
            'reason': 'Test de conectividad'
        }

        self.make_request('POST', 'http://localhost:5002/appointments/create', appointment_data)

        # Test 4: Inventory -> Notification (alertas)
        print(f"\n{Colors.BLUE}4. Testing Inventory -> Notification Service{Colors.RESET}")

        # Crear medicamento con stock bajo
        low_stock_med = {
            'name': 'Med Stock Bajo',
            'stock_quantity': 2,
            'unit_price': 1000,
            'minimum_stock_alert': 10,
            'category': 'Test'
        }

        self.make_request('POST', 'http://localhost:5005/inventory/medications', low_stock_med)

        # Verificar alertas de stock bajo
        self.make_request('GET', 'http://localhost:5005/inventory/alerts/low-stock')

        self.print_success("Test de conectividad entre servicios completado")

    def cleanup_test_data(self):
        """Limpiar datos de prueba"""
        self.print_header("LIMPIAR DATOS DE PRUEBA")

        print(f"{Colors.YELLOW}⚠️ Esta operación no eliminará datos de la base de datos directamente.{Colors.RESET}")
        print(f"{Colors.YELLOW}Para una limpieza completa, necesitarás acceso directo a PostgreSQL.{Colors.RESET}")

        confirm = input(f"\n{Colors.CYAN}¿Limpiar datos de prueba de la sesión actual? (y/N): {Colors.RESET}")

        if confirm.lower() == 'y':
            self.test_data.clear()
            self.auth_token = None
            self.current_user = None
            self.print_success("Datos de sesión limpiados")

            # Mostrar comandos SQL para limpieza manual
            print(f"\n{Colors.BLUE}Para limpiar la base de datos manualmente:{Colors.RESET}")
            print("docker exec -it postgres-local psql -U postgres -d veterinary-system")
            print("DELETE FROM notifications WHERE title LIKE '%prueba%' OR title LIKE '%test%';")
            print("DELETE FROM prescriptions WHERE medication_name LIKE '%test%' OR medication_name LIKE '%prueba%';")
            print("DELETE FROM medical_records WHERE diagnosis LIKE '%test%' OR diagnosis LIKE '%prueba%';")
            print("DELETE FROM appointments WHERE reason LIKE '%test%' OR reason LIKE '%prueba%';")
            print("DELETE FROM pets WHERE name LIKE '%test%' OR name LIKE '%prueba%';")
            print("DELETE FROM medications WHERE name LIKE '%test%' OR name LIKE '%prueba%';")
            print("DELETE FROM users WHERE email LIKE '%test%' OR email LIKE '%prueba%';")

    def export_test_logs(self):
        """Exportar logs de testing"""
        self.print_header("EXPORTAR LOGS DE TESTING")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"test_logs_{timestamp}.txt"

        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"LOGS DE TESTING - Sistema de Clínica Veterinaria\n")
                f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")

                f.write("ESTADO DE SERVICIOS:\n")
                for service_key, service in self.services.items():
                    f.write(f"- {service['name']}: {service['status']}\n")

                f.write(f"\nDATOS DE PRUEBA GENERADOS:\n")
                for key, value in self.test_data.items():
                    f.write(f"- {key}: {value}\n")

                f.write(f"\nUSUARIO ACTUAL:\n")
                if self.current_user:
                    f.write(f"- Nombre: {self.current_user.get('name')}\n")
                    f.write(f"- Email: {self.current_user.get('email')}\n")
                    f.write(f"- Rol: {self.current_user.get('role')}\n")
                else:
                    f.write("- No hay usuario logueado\n")

            self.print_success(f"Logs exportados a: {log_file}")

        except Exception as e:
            self.print_error(f"Error exportando logs: {str(e)}")

    def configure_environment(self):
        """Configurar variables de entorno"""
        self.print_header("CONFIGURAR VARIABLES DE ENTORNO")

        print("Variables de entorno actuales:")
        env_vars = [
            'POSTGRES_HOST', 'POSTGRES_DB', 'POSTGRES_USER',
            'POSTGRES_PASSWORD', 'POSTGRES_PORT', 'FLASK_ENV', 'FLASK_DEBUG'
        ]

        for var in env_vars:
            value = os.environ.get(var, 'No configurada')
            print(f"  {var}: {value}")

        print(f"\n{Colors.YELLOW}Configuración de base de datos:{Colors.RESET}")
        print(f"Host: {os.environ.get('POSTGRES_HOST', 'localhost')}")
        print(f"Puerto: {os.environ.get('POSTGRES_PORT', '5432')}")
        print(f"Base de datos: {os.environ.get('POSTGRES_DB', 'veterinary-system')}")
        print(f"Usuario: {os.environ.get('POSTGRES_USER', 'postgres')}")

        modify = input(f"\n{Colors.CYAN}¿Modificar configuración? (y/N): {Colors.RESET}")

        if modify.lower() == 'y':
            print("\nIngresa los nuevos valores (deja vacío para mantener actual):")

            for var in env_vars:
                current = os.environ.get(var, '')
                new_value = input(f"{var} [{current}]: ")
                if new_value:
                    os.environ[var] = new_value
                    self.print_success(f"{var} actualizada")

    def cleanup_and_exit(self):
        """Limpiar y salir"""
        self.print_header("FINALIZANDO APLICACIÓN")

        if self.running:
            print("Deteniendo servicios...")
            self.stop_all_services()

        print(f"\n{Colors.GREEN}¡Gracias por usar el Testing Suite de Clínica Veterinaria!{Colors.RESET}")
        print(f"{Colors.BLUE}Desarrollado para testing completo de microservicios{Colors.RESET}")


def main():
    """Función principal"""
    try:
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("🐾" + "=" * 58 + "🐾")
        print("🐾  SISTEMA DE CLÍNICA VETERINARIA - TESTING SUITE    🐾")
        print("🐾  Aplicación de Consola para Testing Completo      🐾")
        print("🐾  Arquitectura de Microservicios - Python Flask    🐾")
        print("🐾" + "=" * 58 + "🐾")
        print(f"{Colors.RESET}\n")

        app = VeterinaryConsoleApp()
        app.show_main_menu()

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Aplicación interrumpida por el usuario{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}Error fatal: {str(e)}{Colors.RESET}")
    finally:
        print(f"\n{Colors.GREEN}¡Hasta luego!{Colors.RESET}")


if __name__ == '__main__':
    main()