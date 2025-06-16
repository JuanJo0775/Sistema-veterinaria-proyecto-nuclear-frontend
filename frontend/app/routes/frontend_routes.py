# frontend/app/routes/frontend_routes.py - VERSIÓN CORREGIDA
import io
from datetime import datetime, time


from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from functools import wraps
import requests
from flask import send_from_directory
import os
import psycopg2
import psycopg2.extras
import uuid
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from frontend.config import role_required
from flask import Response

frontend_bp = Blueprint('frontend', __name__)


@frontend_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Servir archivos subidos (fotos de mascotas, documentos, etc.)"""
    try:
        # CORRECCIÓN 1: Usar directorio estático del frontend
        uploads_dir = os.path.join(current_app.static_folder, 'uploads')

        # Si el directorio no existe, crearlo
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir, exist_ok=True)
            os.makedirs(os.path.join(uploads_dir, 'pets'), exist_ok=True)
            os.makedirs(os.path.join(uploads_dir, 'exams'), exist_ok=True)

        # CORRECCIÓN 2: Verificar si el archivo existe localmente primero
        local_file_path = os.path.join(uploads_dir, filename)
        if os.path.exists(local_file_path):
            return send_from_directory(uploads_dir, filename)

        # CORRECCIÓN 3: Si no existe localmente, hacer proxy desde Medical Service
        return proxy_file_from_medical_service(filename)

    except Exception as e:
        print(f"❌ Error sirviendo archivo {filename}: {e}")
        # CORRECCIÓN 4: Retornar imagen placeholder en lugar de 404
        return redirect(url_for('static', filename='images/placeholder-pet.png'))


@frontend_bp.route('/uploads/pets/<pet_id>/<filename>')
def pet_photo(pet_id, filename):
    """Servir fotos específicas de mascotas"""
    try:
        # CORRECCIÓN 5: Verificar múltiples ubicaciones
        uploads_dir = os.path.join(current_app.static_folder, 'uploads')
        pets_dir = os.path.join(uploads_dir, 'pets', pet_id)

        # Crear directorio si no existe
        os.makedirs(pets_dir, exist_ok=True)

        local_file_path = os.path.join(pets_dir, filename)

        # Si existe localmente, servirlo
        if os.path.exists(local_file_path):
            return send_from_directory(pets_dir, filename)

        # CORRECCIÓN 6: Intentar desde el directorio raíz de uploads
        root_file_path = os.path.join(uploads_dir, filename)
        if os.path.exists(root_file_path):
            return send_from_directory(uploads_dir, filename)

        # CORRECCIÓN 7: Hacer proxy desde Medical Service con mejor manejo de errores
        try:
            return proxy_pet_photo_from_medical_service(pet_id, filename)
        except:
            # Si falla el proxy, retornar placeholder
            return redirect(url_for('static', filename='images/placeholder-pet.png'))

    except Exception as e:
        print(f"❌ Error sirviendo foto de mascota {pet_id}/{filename}: {e}")
        return redirect(url_for('static', filename='images/placeholder-pet.png'))


def proxy_file_from_medical_service(filename):
    """Hacer proxy de archivo genérico desde Medical Service"""
    try:
        import requests

        # CORRECCIÓN 8: URL más específica para archivos
        medical_url = f"{current_app.config.get('MEDICAL_SERVICE_URL', 'http://localhost:5004')}/uploads/{filename}"

        response = requests.get(medical_url, timeout=10, stream=True)

        if response.status_code == 200:
            from flask import Response
            return Response(
                response.iter_content(chunk_size=8192),
                mimetype=response.headers.get('content-type', 'application/octet-stream'),
                headers={
                    'Content-Length': response.headers.get('content-length'),
                    'Cache-Control': 'public, max-age=3600'
                }
            )
        else:
            raise Exception(f"HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ Error haciendo proxy de archivo {filename}: {e}")
        raise


def proxy_pet_photo_from_medical_service(pet_id, filename):
    """Hacer proxy de la foto desde el Medical Service"""
    try:
        import requests

        # CORRECCIÓN 9: Múltiples rutas para intentar
        possible_urls = [
            f"{current_app.config.get('MEDICAL_SERVICE_URL', 'http://localhost:5004')}/uploads/pets/{pet_id}/{filename}",
            f"{current_app.config.get('MEDICAL_SERVICE_URL', 'http://localhost:5004')}/medical/pets/{pet_id}/photo/{filename}",
            f"{current_app.config.get('MEDICAL_SERVICE_URL', 'http://localhost:5004')}/uploads/{filename}"
        ]

        for url in possible_urls:
            try:
                response = requests.get(url, timeout=5, stream=True)

                if response.status_code == 200:
                    from flask import Response
                    return Response(
                        response.iter_content(chunk_size=8192),
                        mimetype=response.headers.get('content-type', 'image/jpeg'),
                        headers={
                            'Content-Length': response.headers.get('content-length'),
                            'Cache-Control': 'public, max-age=3600'
                        }
                    )
            except:
                continue

        # Si ninguna URL funciona, lanzar excepción
        raise Exception("No se pudo obtener la imagen desde ninguna ruta")

    except Exception as e:
        print(f"❌ Error haciendo proxy de foto {pet_id}/{filename}: {e}")
        raise


@frontend_bp.route('/api/admin/pets/<pet_id>/photo/check')
@role_required(['admin'])
def api_check_pet_photo(pet_id):
    """Verificar si existe foto de mascota y retornar URL correcta"""
    try:
        # Verificar en directorio local primero
        uploads_dir = os.path.join(current_app.static_folder, 'uploads')
        pets_dir = os.path.join(uploads_dir, 'pets', pet_id)

        if os.path.exists(pets_dir):
            # Buscar archivos de imagen en el directorio
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            for file in os.listdir(pets_dir):
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    return jsonify({
                        'success': True,
                        'has_photo': True,
                        'photo_url': url_for('frontend.pet_photo', pet_id=pet_id, filename=file)
                    })

        # Si no hay foto local, verificar en Medical Service
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        medical_url = f"{current_app.config.get('MEDICAL_SERVICE_URL', 'http://localhost:5004')}/medical/pets/{pet_id}"

        response = requests.get(medical_url, headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('pet', {}).get('photo_url'):
                return jsonify({
                    'success': True,
                    'has_photo': True,
                    'photo_url': data['pet']['photo_url']
                })

        return jsonify({
            'success': True,
            'has_photo': False,
            'photo_url': None
        })

    except Exception as e:
        print(f"❌ Error verificando foto de mascota {pet_id}: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== CONFIGURACIÓN DE UPLOADS ===============


def ensure_placeholder_images():
    """Asegurar que existan las imágenes placeholder necesarias"""
    try:
        from flask import current_app
        import os

        # Obtener directorio estático
        static_dir = current_app.static_folder
        if not static_dir:
            static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static')

        images_dir = os.path.join(static_dir, 'images')
        os.makedirs(images_dir, exist_ok=True)

        placeholder_path = os.path.join(images_dir, 'placeholder-pet.png')

        # Solo crear si no existe
        if not os.path.exists(placeholder_path):
            create_simple_placeholder_image(placeholder_path)
            print(f"✅ Imagen placeholder creada en: {placeholder_path}")

        return True

    except Exception as e:
        print(f"⚠️ No se pudo crear imagen placeholder: {e}")
        return False


def create_simple_placeholder_image(filepath):
    """Crear imagen placeholder básica usando solo bibliotecas estándar"""
    try:
        # Intentar usar PIL si está disponible
        try:
            from PIL import Image, ImageDraw

            # Crear imagen 200x200 con color de fondo
            img = Image.new('RGB', (200, 200), color='#D8F3DC')
            draw = ImageDraw.Draw(img)

            # Dibujar círculo de fondo
            margin = 20
            draw.ellipse([margin, margin, 180, 180],
                         fill='#52B788', outline='#2D6A4F', width=4)

            # Dibujar forma simple de mascota
            # Cabeza
            draw.ellipse([85, 70, 115, 100], fill='#D8F3DC')
            # Cuerpo
            draw.ellipse([80, 95, 120, 140], fill='#D8F3DC')
            # Orejas
            draw.ellipse([88, 60, 96, 75], fill='#D8F3DC')
            draw.ellipse([104, 60, 112, 75], fill='#D8F3DC')

            # Guardar imagen
            img.save(filepath, 'PNG')
            return True

        except ImportError:
            # Si PIL no está disponible, crear archivo básico
            print("⚠️ PIL no disponible, creando placeholder básico")

            # Crear un archivo PNG básico (1x1 pixel transparente)
            png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'

            with open(filepath, 'wb') as f:
                f.write(png_data)

            return True

    except Exception as e:
        print(f"❌ Error creando placeholder: {e}")
        return False


def setup_upload_directories():
    """Configurar directorios de uploads necesarios"""
    try:
        from flask import current_app
        import os

        # Directorio de uploads en static
        static_dir = current_app.static_folder
        if not static_dir:
            static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static')

        uploads_dir = os.path.join(static_dir, 'uploads')
        pets_dir = os.path.join(uploads_dir, 'pets')
        exams_dir = os.path.join(uploads_dir, 'exams')

        # Crear directorios
        os.makedirs(uploads_dir, exist_ok=True)
        os.makedirs(pets_dir, exist_ok=True)
        os.makedirs(exams_dir, exist_ok=True)

        print(f"✅ Directorios de uploads configurados: {uploads_dir}")
        return True

    except Exception as e:
        print(f"⚠️ Error configurando directorios: {e}")
        return False

def login_required(f):
    """Decorador para rutas que requieren autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('frontend.login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(required_roles):
    """Decorador para rutas que requieren roles específicos"""
    def decorator(f):
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


# =============== RUTAS PÚBLICAS ===============

@frontend_bp.route('/')
def index():
    """Página principal/landing"""
    return render_template('index.html')


@frontend_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            # Llamar al auth service
            auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/login"
            response = requests.post(auth_url, json={
                'email': email,
                'password': password
            }, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # Guardar datos del usuario en la sesión
                    session['user'] = data['user']
                    session['token'] = data['token']
                    session.permanent = True

                    flash('¡Bienvenido!', 'success')
                    print(f"🔐 Usuario logueado: {data['user']}")

                    return redirect(url_for('frontend.dashboard'))
                else:
                    flash(data.get('message', 'Error al iniciar sesión'), 'error')
            else:
                flash('Credenciales inválidas', 'error')

        except requests.RequestException as e:
            print(f"❌ Error de conexión: {e}")
            flash('Error de conexión con el servidor', 'error')

    return render_template('auth/login.html')


@frontend_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Página de registro"""
    if request.method == 'POST':
        user_data = {
            'email': request.form.get('email'),
            'password': request.form.get('password'),
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'phone': request.form.get('phone'),
            'address': request.form.get('address'),
            'role': 'client'
        }

        try:
            auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/register"
            response = requests.post(auth_url, json=user_data, timeout=10)

            if response.status_code == 201:
                flash('¡Registro exitoso! Ahora puedes iniciar sesión.', 'success')
                return redirect(url_for('frontend.login'))
            else:
                data = response.json()
                flash(data.get('message', 'Error al registrarse'), 'error')

        except requests.RequestException as e:
            flash('Error de conexión con el servidor', 'error')

    return render_template('auth/register.html')


@frontend_bp.route('/logout')
def logout():
    """Cerrar sesión"""
    session.clear()
    flash('Sesión cerrada exitosamente', 'info')
    return redirect(url_for('frontend.index'))


# =============== RUTAS PROTEGIDAS ===============

@frontend_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal - redirige según el rol"""
    user_role = session['user'].get('role')
    print(f"🔄 Dashboard redirect para rol: {user_role}")

    if user_role == 'admin':
        return redirect(url_for('frontend.admin_dashboard'))
    elif user_role == 'veterinarian':
        return redirect(url_for('frontend.veterinarian_dashboard'))
    elif user_role == 'receptionist':
        return redirect(url_for('frontend.receptionist_dashboard'))
    elif user_role == 'auxiliary':
        return redirect(url_for('frontend.auxiliary_dashboard'))
    elif user_role == 'client':
        return redirect(url_for('frontend.client_dashboard'))
    else:
        flash('Rol de usuario no válido', 'error')
        return redirect(url_for('frontend.logout'))


# =============== DASHBOARDS POR ROL ===============

@frontend_bp.route('/admin/dashboard')
@role_required(['admin'])
def admin_dashboard():
    """Dashboard principal para administradores"""

    # AGREGAR ESTA LÍNEA AL INICIO DE LA FUNCIÓN:
    ensure_placeholder_images()
    setup_upload_directories()

    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener resumen del inventario
        inventory_summary = {}
        try:
            inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/summary"
            inventory_response = requests.get(inventory_url, headers=headers, timeout=10)
            if inventory_response.status_code == 200:
                inventory_data = inventory_response.json()
                if inventory_data.get('success'):
                    inventory_summary = inventory_data.get('summary', {})
        except Exception as e:
            print(f"⚠️ Error obteniendo inventario: {e}")

        # Obtener estadísticas de citas
        appointments_today = []
        try:
            appointments_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/today"
            appointments_response = requests.get(appointments_url, headers=headers, timeout=10)
            if appointments_response.status_code == 200:
                appointments_data = appointments_response.json()
                if appointments_data.get('success'):
                    appointments_today = appointments_data.get('appointments', [])
        except Exception as e:
            print(f"⚠️ Error obteniendo citas: {e}")

        # Preparar datos para el template
        user = session.get('user', {})
        template_data = {
            'inventory_summary': inventory_summary,
            'appointments_today': appointments_today,
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Administrador',
            'user_role': user.get('role', 'admin').title(),
            'user_initial': user.get('first_name', 'A')[0].upper() if user.get('first_name') else 'A'
        }

        return render_template('admin/dashboard.html', **template_data)

    except Exception as e:
        print(f"❌ Error en admin dashboard: {e}")
        flash('Error al cargar el dashboard', 'error')
        user = session.get('user', {})
        return render_template('admin/dashboard.html',
                               inventory_summary={},
                               appointments_today=[],
                               user=user,
                               user_name='Administrador',
                               user_role='Admin',
                               user_initial='A')

# =============== RUTAS ESPECÍFICAS PARA SECCIONES ADMIN ===============

@frontend_bp.route('/admin/users')
@role_required(['admin'])
def admin_users():
    """Página de gestión de usuarios - ÚNICA DEFINICIÓN"""
    try:
        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Administrador',
            'user_role': user.get('role', 'admin').title(),
            'user_initial': user.get('first_name', 'A')[0].upper() if user.get('first_name') else 'A'
        }

        return render_template('admin/sections/users-management.html', **template_data)

    except Exception as e:
        print(f"❌ Error en admin users: {e}")
        flash('Error al cargar la gestión de usuarios', 'error')
        return redirect(url_for('frontend.admin_dashboard'))



@frontend_bp.route('/admin/appointments')
@role_required(['admin'])
def admin_appointments():
    """Página de gestión de citas"""
    user = session.get('user', {})
    template_data = {
        'user': user,
        'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Administrador',
        'user_role': user.get('role', 'admin').title(),
        'user_initial': user.get('first_name', 'A')[0].upper() if user.get('first_name') else 'A'
    }
    return render_template('admin/sections/appointments-management.html', **template_data)


# =============== OTROS DASHBOARDS ===============





@frontend_bp.route('/receptionist/dashboard')
@role_required(['receptionist'])
def receptionist_dashboard():
    """Dashboard para recepcionistas"""
    return render_template('receptionist/dashboard.html')


@frontend_bp.route('/auxiliary/dashboard')
@role_required(['auxiliary'])
def auxiliary_dashboard():
    """Dashboard para auxiliares"""
    return render_template('auxiliary/dashboard.html')


# =============== API ENDPOINTS PARA AJAX ===============

@frontend_bp.route('/api/user-info')
@login_required
def user_info():
    """Información del usuario actual"""
    return jsonify({
        'success': True,
        'user': session['user']
    })


@frontend_bp.route('/api/dashboard-data')
@login_required
def dashboard_data():
    """Datos para el dashboard (AJAX)"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Datos del inventario
        inventory_data = {}
        try:
            inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/summary"
            inventory_response = requests.get(inventory_url, headers=headers, timeout=5)
            if inventory_response.status_code == 200:
                inv_json = inventory_response.json()
                if inv_json.get('success'):
                    inventory_data = inv_json.get('summary', {})
        except:
            pass

        # Citas de hoy
        appointments_count = 0
        try:
            appointments_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/today"
            appointments_response = requests.get(appointments_url, headers=headers, timeout=5)
            if appointments_response.status_code == 200:
                app_json = appointments_response.json()
                if app_json.get('success'):
                    appointments_count = len(app_json.get('appointments', []))
        except:
            pass

        return jsonify({
            'success': True,
            'data': {
                'total_pets': 0,
                'appointments_today': appointments_count,
                'low_stock_count': inventory_data.get('low_stock_count', 0),
                'inventory_value': inventory_data.get('total_inventory_value', 0),
                'notifications_count': 0
            }
        })

    except Exception as e:
        print(f"❌ Error obteniendo datos del dashboard: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/users')
@role_required(['admin'])
def api_get_users():
    """API endpoint para obtener usuarios (para AJAX del frontend)"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener usuarios desde Auth Service
        auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/users"
        response = requests.get(auth_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
        elif response.status_code == 403:
            return jsonify({
                'success': False,
                'message': 'Token de autorización inválido o expirado'
            }), 403
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Auth Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Auth Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de autenticación'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_get_users: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/users', methods=['POST'])
@role_required(['admin'])
def api_create_user():
    """Crear nuevo usuario"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        # Crear usuario en Auth Service
        auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/register"
        response = requests.post(auth_url, json=data, headers=headers, timeout=10)

        if response.status_code == 201:
            return jsonify(response.json())
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith(
                'application/json') else {}
            return jsonify({
                'success': False,
                'message': error_data.get('message', f'Error del Auth Service: {response.status_code}')
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Auth Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de autenticación'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_create_user: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/users/<user_id>', methods=['PUT'])
@role_required(['admin'])
def api_update_user(user_id):
    """Actualizar usuario específico"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        # Actualizar usuario en Auth Service
        auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/users/{user_id}"
        response = requests.put(auth_url, json=data, headers=headers, timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith(
                'application/json') else {}
            return jsonify({
                'success': False,
                'message': error_data.get('message', f'Error del Auth Service: {response.status_code}')
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Auth Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de autenticación'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_update_user: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/users/<user_id>/toggle-status', methods=['PUT'])
@role_required(['admin'])
def api_toggle_user_status(user_id):
    """Activar/Desactivar usuario"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Cambiar estado en Auth Service
        auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/users/{user_id}/toggle-status"
        response = requests.put(auth_url, headers=headers, timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith(
                'application/json') else {}
            return jsonify({
                'success': False,
                'message': error_data.get('message', f'Error del Auth Service: {response.status_code}')
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Auth Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de autenticación'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_toggle_user_status: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/users/<user_id>', methods=['DELETE'])
@role_required(['admin'])
def api_delete_user(user_id):
    """Eliminar usuario definitivamente"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Verificar que no sea el usuario actual
        current_user = session.get('user', {})
        if current_user.get('id') == user_id:
            return jsonify({
                'success': False,
                'message': 'No puedes eliminar tu propia cuenta'
            }), 400

        # Eliminar usuario en Auth Service
        auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/users/{user_id}"
        response = requests.delete(auth_url, headers=headers, timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        elif response.status_code == 400:
            # Error de validación (como intentar eliminar propia cuenta)
            error_data = response.json() if response.headers.get('content-type', '').startswith(
                'application/json') else {}
            return jsonify({
                'success': False,
                'message': error_data.get('message', 'No se puede eliminar este usuario')
            }), 400
        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith(
                'application/json') else {}
            return jsonify({
                'success': False,
                'message': error_data.get('message', f'Error del Auth Service: {response.status_code}')
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Auth Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de autenticación'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_delete_user: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@frontend_bp.route('/admin/schedules')
@role_required(['admin'])
def admin_schedules():
    """Página de gestión de horarios"""
    user = session.get('user', {})
    template_data = {
        'user': user,
        'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Administrador',
        'user_role': user.get('role', 'admin').title(),
        'user_initial': user.get('first_name', 'A')[0].upper() if user.get('first_name') else 'A'
    }
    return render_template('admin/sections/schedules-management.html', **template_data)


# =============== API ENDPOINTS PARA HORARIOS ===============

@frontend_bp.route('/api/admin/schedules')
@role_required(['admin'])
def api_get_schedules():
    """API endpoint para obtener horarios (para AJAX del frontend)"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener horarios desde Auth Service
        auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/schedules"
        response = requests.get(auth_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
        elif response.status_code == 403:
            return jsonify({
                'success': False,
                'message': 'Token de autorización inválido o expirado'
            }), 403
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Auth Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Auth Service para horarios: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de autenticación'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_get_schedules: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/schedules/<user_id>', methods=['PUT'])
@role_required(['admin'])
def api_update_user_schedule(user_id):
    """Actualizar horario de un usuario específico - VERSIÓN CORREGIDA FINAL"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        print(f"📝 Frontend: Actualizando horario para usuario: {user_id}")
        print(f"📝 Datos recibidos: {data}")

        # PASO 1: Actualizar en Auth Service (principal)
        auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/schedules/{user_id}"

        success = False
        response_data = None

        try:
            print(f"📡 Enviando a Auth Service: {auth_url}")
            response = requests.put(auth_url, json=data, headers=headers, timeout=10)
            print(f"📡 Respuesta Auth Service: {response.status_code}")

            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('success'):
                    success = True
                    print("✅ Horario actualizado en Auth Service")
                else:
                    print(f"❌ Error en Auth Service: {response_data.get('message')}")
            else:
                print(f"❌ Error HTTP Auth Service: {response.status_code}")

        except requests.RequestException as auth_error:
            print(f"❌ Error conectando con Auth Service: {auth_error}")

        if not success:
            return jsonify({
                'success': False,
                'message': 'Error actualizando horario en Auth Service'
            }), 500

        # PASO 2: Verificar si es veterinario y sincronizar
        print("🔍 Verificando si usuario es veterinario...")

        user_role = None

        # Intentar obtener rol del usuario
        try:
            user_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/users/{user_id}"
            user_response = requests.get(user_url, headers=headers, timeout=5)

            if user_response.status_code == 200:
                user_info = user_response.json()
                if user_info.get('success'):
                    user_role = user_info.get('user', {}).get('role')
                    print(f"✅ Rol obtenido: {user_role}")
            else:
                print(f"⚠️ Error obteniendo usuario: {user_response.status_code}")

        except requests.RequestException as user_error:
            print(f"⚠️ Error obteniendo información del usuario: {user_error}")

        # PASO 3: Si es veterinario, sincronizar con Appointment Service
        if user_role == 'veterinarian':
            print("👨‍⚕️ Usuario es veterinario, sincronizando con Appointment Service...")

            try:
                sync_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/schedules/staff/{user_id}"
                sync_response = requests.put(sync_url, json=data, headers=headers, timeout=10)

                if sync_response.status_code == 200:
                    sync_data = sync_response.json()
                    if sync_data.get('success'):
                        print("✅ Horario sincronizado en Appointment Service")
                    else:
                        print(f"⚠️ Error sincronizando: {sync_data.get('message')}")
                else:
                    print(f"⚠️ Error HTTP sincronizando: {sync_response.status_code}")

            except requests.RequestException as sync_error:
                print(f"⚠️ Error sincronizando con Appointment Service: {sync_error}")
                # No fallar la operación principal por esto

        elif user_role:
            print(f"ℹ️ Usuario tiene rol '{user_role}', no requiere sincronización")
        else:
            print("⚠️ No se pudo determinar el rol del usuario")

        # PASO 4: Verificar que se guardó correctamente
        print("🔍 Verificando sincronización...")
        try:
            verify_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/schedules/veterinarians-v2"
            verify_response = requests.get(verify_url, headers=headers, timeout=5)

            if verify_response.status_code == 200:
                verify_data = verify_response.json()
                if verify_data.get('success'):
                    vet_schedules = verify_data.get('veterinarian_schedules', {})
                    if user_id in vet_schedules:
                        schedule_count = len(vet_schedules[user_id])
                        print(
                            f"✅ Verificación exitosa: {schedule_count} horarios encontrados para veterinario {user_id}")
                    else:
                        print(f"⚠️ No se encontraron horarios para veterinario {user_id} después de la sincronización")

        except Exception as verify_error:
            print(f"⚠️ Error verificando sincronización: {verify_error}")

        return jsonify(response_data)

    except Exception as e:
        print(f"❌ Error general en api_update_user_schedule: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


# TAMBIÉN AGREGAR ESTE ENDPOINT PARA VERIFICACIÓN
@frontend_bp.route('/api/admin/schedules/verify/<user_id>')
@role_required(['admin'])
def api_verify_user_schedule(user_id):
    """Verificar horarios de un usuario en ambos servicios"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        result = {
            'user_id': user_id,
            'auth_service': {'success': False, 'schedules': None},
            'appointment_service': {'success': False, 'schedules': None}
        }

        # Verificar en Auth Service
        try:
            auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/schedules"
            auth_response = requests.get(auth_url, headers=headers, timeout=5)

            if auth_response.status_code == 200:
                auth_data = auth_response.json()
                if auth_data.get('success'):
                    user_schedule = next((s for s in auth_data.get('schedules', []) if s.get('user_id') == user_id),
                                         None)
                    if user_schedule:
                        result['auth_service'] = {
                            'success': True,
                            'schedules': user_schedule.get('weekly_schedule', {})
                        }

        except Exception as auth_error:
            print(f"Error verificando Auth Service: {auth_error}")

        # Verificar en Appointment Service
        try:
            appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/schedules/{user_id}"
            appointment_response = requests.get(appointment_url, headers=headers, timeout=5)

            if appointment_response.status_code == 200:
                appointment_data = appointment_response.json()
                if appointment_data.get('success'):
                    result['appointment_service'] = {
                        'success': True,
                        'schedules': appointment_data.get('schedules', [])
                    }

        except Exception as appointment_error:
            print(f"Error verificando Appointment Service: {appointment_error}")

        return jsonify({
            'success': True,
            'verification': result
        })

    except Exception as e:
        print(f"❌ Error en verificación: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@frontend_bp.route('/admin/clients')
@role_required(['admin'])
def admin_clients():
    """Página de gestión de clientes"""
    try:
        # Configurar recursos necesarios
        ensure_placeholder_images()
        setup_upload_directories()

        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Administrador',
            'user_role': user.get('role', 'admin').title(),
            'user_initial': user.get('first_name', 'A')[0].upper() if user.get('first_name') else 'A'
        }

        print(f"✅ Cargando página de gestión de clientes para usuario: {user.get('email')}")
        return render_template('admin/sections/clients-management.html', **template_data)

    except Exception as e:
        print(f"❌ Error en admin_clients: {e}")
        flash('Error al cargar la gestión de clientes', 'error')
        return redirect(url_for('frontend.admin_dashboard'))


@frontend_bp.route('/admin/pets')
@role_required(['admin'])
def admin_pets():
    """Página de gestión de mascotas"""

    # AGREGAR ESTAS LÍNEAS AL INICIO:
    ensure_placeholder_images()
    setup_upload_directories()

    user = session.get('user', {})
    template_data = {
        'user': user,
        'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Administrador',
        'user_role': user.get('role', 'admin').title(),
        'user_initial': user.get('first_name', 'A')[0].upper() if user.get('first_name') else 'A'
    }
    return render_template('admin/sections/pets-management.html', **template_data)

def initialize_app_resources(app):
    """Función para inicializar recursos de la aplicación"""
    with app.app_context():
        ensure_placeholder_images()
        setup_upload_directories()
        print("🚀 Recursos de la aplicación inicializados")

@frontend_bp.route('/api/admin/pets')
@role_required(['admin'])
def api_get_pets():
    """API endpoint para obtener mascotas (para AJAX del frontend)"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener todas las mascotas desde Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets"
        response = requests.get(medical_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('pets'):
                # Enriquecer datos con información de propietarios
                pets = data['pets']
                enriched_pets = []

                # Obtener usuarios para mapear propietarios
                try:
                    auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/users"
                    users_response = requests.get(auth_url, headers=headers, timeout=5)
                    users_data = []

                    if users_response.status_code == 200:
                        users_json = users_response.json()
                        if users_json.get('success'):
                            users_data = users_json.get('users', [])

                    # Crear mapa de usuarios
                    users_map = {user['id']: user for user in users_data}

                    # Enriquecer datos de mascotas
                    for pet in pets:
                        owner_id = pet.get('owner_id')
                        owner = users_map.get(owner_id, {})

                        enriched_pet = {
                            **pet,
                            'owner_name': f"{owner.get('first_name', '')} {owner.get('last_name', '')}".strip() or 'Propietario desconocido',
                            'owner_email': owner.get('email', ''),
                            'owner_phone': owner.get('phone', '')
                        }
                        enriched_pets.append(enriched_pet)

                except Exception as e:
                    print(f"⚠️ Error obteniendo propietarios: {e}")
                    enriched_pets = pets

                return jsonify({
                    'success': True,
                    'pets': enriched_pets,
                    'total': len(enriched_pets)
                })
            else:
                return jsonify({
                    'success': True,
                    'pets': [],
                    'total': 0
                })
        else:
            # Si falla, retornar array vacío para que el frontend use datos de ejemplo
            return jsonify({
                'success': False,
                'message': f'Error del Medical Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_get_pets: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/pets', methods=['POST'])
@role_required(['admin'])
def api_create_pet():
    """Crear nueva mascota"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        # Validar datos básicos
        if not data.get('name') or not data.get('owner_id') or not data.get('species'):
            return jsonify({
                'success': False,
                'message': 'Campos requeridos: name, owner_id, species'
            }), 400

        # Crear mascota en Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets"
        response = requests.post(medical_url, json=data, headers=headers, timeout=10)

        if response.status_code == 201:
            return jsonify(response.json())
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith(
                'application/json') else {}
            return jsonify({
                'success': False,
                'message': error_data.get('message', f'Error del Medical Service: {response.status_code}')
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_create_pet: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/pets/<pet_id>', methods=['PUT'])
@role_required(['admin'])
def api_update_pet(pet_id):
    """Actualizar mascota específica"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        # Actualizar mascota en Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}"
        response = requests.put(medical_url, json=data, headers=headers, timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith(
                'application/json') else {}
            return jsonify({
                'success': False,
                'message': error_data.get('message', f'Error del Medical Service: {response.status_code}')
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_update_pet: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/pets/<pet_id>', methods=['DELETE'])
@role_required(['admin'])
def api_delete_pet(pet_id):
    """Eliminar mascota definitivamente"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Eliminar mascota en Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}"
        response = requests.delete(medical_url, headers=headers, timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Mascota no encontrada'
            }), 404
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith(
                'application/json') else {}
            return jsonify({
                'success': False,
                'message': error_data.get('message', f'Error del Medical Service: {response.status_code}')
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_delete_pet: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/pets/<pet_id>/photo', methods=['POST'])
@role_required(['admin'])
def api_upload_pet_photo(pet_id):
    """Subir foto de mascota - VERSIÓN CORREGIDA"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Verificar que hay un archivo
        if 'photo' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No se encontró archivo'
            }), 400

        file = request.files['photo']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No se seleccionó archivo'
            }), 400

        # CORRECCIÓN 12: Validaciones más estrictas
        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
        file_extension = file.filename.lower().split('.')[-1]

        if file_extension not in allowed_extensions:
            return jsonify({
                'success': False,
                'message': 'Tipo de archivo no permitido. Use JPG, PNG o GIF'
            }), 400

        # CORRECCIÓN 13: Validar tamaño del archivo
        file.seek(0, 2)  # Ir al final del archivo
        file_size = file.tell()
        file.seek(0)  # Volver al inicio

        if file_size > 5 * 1024 * 1024:  # 5MB
            return jsonify({
                'success': False,
                'message': 'El archivo es demasiado grande. Máximo 5MB'
            }), 400

        # CORRECCIÓN 14: Guardar localmente primero, luego enviar al Medical Service
        uploads_dir = os.path.join(current_app.static_folder, 'uploads')
        pets_dir = os.path.join(uploads_dir, 'pets', pet_id)
        os.makedirs(pets_dir, exist_ok=True)

        # Generar nombre único
        import uuid
        from werkzeug.utils import secure_filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        secure_name = secure_filename(file.filename)
        unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{secure_name}"

        local_file_path = os.path.join(pets_dir, unique_filename)

        # Guardar archivo localmente
        file.save(local_file_path)

        # CORRECCIÓN 15: También enviar al Medical Service para consistencia
        try:
            file.seek(0)  # Reset file pointer
            files = {'file': (unique_filename, file.stream, file.content_type)}
            medical_url = f"{current_app.config.get('MEDICAL_SERVICE_URL', 'http://localhost:5004')}/medical/pets/{pet_id}/photo"

            medical_response = requests.post(
                medical_url,
                files=files,
                headers={'Authorization': headers['Authorization']},
                timeout=10
            )

            if medical_response.status_code == 200:
                medical_data = medical_response.json()
                print(f"✅ Foto también guardada en Medical Service: {medical_data}")

        except Exception as medical_error:
            print(f"⚠️ Error enviando a Medical Service (pero archivo guardado localmente): {medical_error}")

        # Retornar URL local
        photo_url = url_for('frontend.pet_photo', pet_id=pet_id, filename=unique_filename)

        return jsonify({
            'success': True,
            'message': 'Foto subida exitosamente',
            'photo_url': photo_url,
            'filename': unique_filename
        })

    except Exception as e:
        print(f"❌ Error subiendo foto: {e}")
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


@frontend_bp.route('/api/admin/pets/<pet_id>/medical-records')
@role_required(['admin'])
def api_get_pet_medical_records(pet_id):
    """Obtener historia clínica de una mascota"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener registros médicos desde Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/records/pet/{pet_id}"
        response = requests.get(medical_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify(data)
            else:
                return jsonify({
                    'success': True,
                    'records': [],
                    'total': 0
                })
        else:
            # Si falla, retornar array vacío para que el frontend use datos de ejemplo
            return jsonify({
                'success': False,
                'message': f'Error del Medical Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_get_pet_medical_records: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/pets/search')
@role_required(['admin'])
def api_search_pets():
    """Buscar mascotas"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        search_term = request.args.get('q', '')

        if not search_term:
            return jsonify({
                'success': False,
                'message': 'Parámetro de búsqueda requerido'
            }), 400

        # Buscar mascotas en Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/search?q={search_term}"
        response = requests.get(medical_url, headers=headers, timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith(
                'application/json') else {}
            return jsonify({
                'success': False,
                'message': error_data.get('message', f'Error del Medical Service: {response.status_code}')
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_search_pets: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== ESTADÍSTICAS DE MASCOTAS ===============

@frontend_bp.route('/api/admin/pets/stats')
@role_required(['admin'])
def api_get_pets_stats():
    """Obtener estadísticas de mascotas"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener todas las mascotas para calcular estadísticas
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets"
        response = requests.get(medical_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('pets'):
                pets = data['pets']

                # Calcular estadísticas
                total_pets = len(pets)
                dogs = len([p for p in pets if p.get('species') == 'perro'])
                cats = len([p for p in pets if p.get('species') == 'gato'])
                others = len([p for p in pets if p.get('species') not in ['perro', 'gato']])

                # Estadísticas por vacunación
                complete_vaccination = len([p for p in pets if p.get('vaccination_status') == 'completo'])
                partial_vaccination = len([p for p in pets if p.get('vaccination_status') == 'parcial'])
                pending_vaccination = len([p for p in pets if p.get('vaccination_status') == 'pendiente'])

                # Estadísticas por edad (aproximadas)
                from datetime import datetime, date
                today = date.today()
                puppies = 0
                young = 0
                adult = 0
                senior = 0

                for pet in pets:
                    birth_date = pet.get('birth_date')
                    if birth_date:
                        try:
                            birth = datetime.strptime(birth_date, '%Y-%m-%d').date()
                            age_years = (today - birth).days / 365.25

                            if age_years < 1:
                                puppies += 1
                            elif age_years < 3:
                                young += 1
                            elif age_years <= 7:
                                adult += 1
                            else:
                                senior += 1
                        except:
                            pass

                return jsonify({
                    'success': True,
                    'stats': {
                        'total_pets': total_pets,
                        'by_species': {
                            'dogs': dogs,
                            'cats': cats,
                            'others': others
                        },
                        'by_vaccination': {
                            'complete': complete_vaccination,
                            'partial': partial_vaccination,
                            'pending': pending_vaccination,
                            'unknown': total_pets - complete_vaccination - partial_vaccination - pending_vaccination
                        },
                        'by_age': {
                            'puppies': puppies,
                            'young': young,
                            'adult': adult,
                            'senior': senior
                        }
                    }
                })
            else:
                return jsonify({
                    'success': True,
                    'stats': {
                        'total_pets': 0,
                        'by_species': {'dogs': 0, 'cats': 0, 'others': 0},
                        'by_vaccination': {'complete': 0, 'partial': 0, 'pending': 0, 'unknown': 0},
                        'by_age': {'puppies': 0, 'young': 0, 'adult': 0, 'senior': 0}
                    }
                })
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Medical Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_get_pets_stats: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== RUTAS ESPECÍFICAS PARA MASCOTAS ===============

@frontend_bp.route('/api/admin/pets/by-owner/<owner_id>')
@role_required(['admin'])
def api_get_pets_by_owner(owner_id):
    """Obtener mascotas de un propietario específico"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener mascotas del propietario desde Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/owner/{owner_id}"
        response = requests.get(medical_url, headers=headers, timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith(
                'application/json') else {}
            return jsonify({
                'success': False,
                'message': error_data.get('message', f'Error del Medical Service: {response.status_code}')
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_get_pets_by_owner: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== ENDPOINTS PARA REPORTES ===============

@frontend_bp.route('/api/admin/pets/<pet_id>/report')
@role_required(['admin'])
def api_get_pet_report(pet_id):
    """Generar reporte individual de mascota"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener datos completos de la mascota
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/summary/pet/{pet_id}"
        response = requests.get(medical_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify(data)
            else:
                return jsonify({
                    'success': False,
                    'message': 'No se pudo generar el reporte'
                }), 404
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith(
                'application/json') else {}
            return jsonify({
                'success': False,
                'message': error_data.get('message', f'Error del Medical Service: {response.status_code}')
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_get_pet_report: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== RUTAS PARA HISTORIAS CLÍNICAS - CORREGIDAS ===============

@frontend_bp.route('/admin/medical-records')
@role_required(['admin'])
def admin_medical_records():
    """Página de gestión de historias clínicas"""
    try:
        # Configurar recursos necesarios
        ensure_placeholder_images()
        setup_upload_directories()

        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Administrador',
            'user_role': user.get('role', 'admin').title(),
            'user_initial': user.get('first_name', 'A')[0].upper() if user.get('first_name') else 'A'
        }
        return render_template('admin/sections/medical-records.html', **template_data)

    except Exception as e:
        print(f"❌ Error en admin_medical_records: {e}")
        flash('Error al cargar la gestión de historias clínicas', 'error')
        return redirect(url_for('frontend.admin_dashboard'))


# =============== API ENDPOINTS PARA HISTORIAS CLÍNICAS ===============

@frontend_bp.route('/api/admin/medical-records')
@role_required(['admin'])
def api_get_medical_records():
    """API endpoint para obtener todas las historias clínicas"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # PASO 1: Obtener todas las mascotas
        print("📡 Obteniendo mascotas...")
        pets_data = []

        try:
            pets_response = requests.get(
                f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets",
                headers=headers,
                timeout=10
            )

            if pets_response.status_code == 200:
                pets_json = pets_response.json()
                if pets_json.get('success'):
                    pets_data = pets_json.get('pets', [])
                    print(f"✅ {len(pets_data)} mascotas obtenidas")
        except Exception as e:
            print(f"⚠️ Error obteniendo mascotas: {e}")

        # PASO 2: Obtener historias clínicas para cada mascota
        all_records = []

        for pet in pets_data:
            try:
                records_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/records/pet/{pet['id']}"
                records_response = requests.get(records_url, headers=headers, timeout=10)

                if records_response.status_code == 200:
                    records_data = records_response.json()
                    if records_data.get('success') and records_data.get('medical_records'):
                        # Enriquecer cada registro con datos de la mascota
                        for record in records_data['medical_records']:
                            record.update({
                                'pet_name': pet['name'],
                                'pet_species': pet['species'],
                                'pet_breed': pet.get('breed', ''),
                                'owner_name': pet.get('owner_name', 'Propietario desconocido'),
                                'owner_id': pet['owner_id']
                            })
                        all_records.extend(records_data['medical_records'])

            except Exception as e:
                print(f"⚠️ Error obteniendo historias de mascota {pet['id']}: {e}")
                continue

        # PASO 3: Enriquecer con datos de veterinarios
        try:
            print("📡 Obteniendo veterinarios...")
            users_response = requests.get(
                f"{current_app.config['AUTH_SERVICE_URL']}/auth/users",
                headers=headers,
                timeout=10
            )

            if users_response.status_code == 200:
                users_data = users_response.json()
                if users_data.get('success'):
                    veterinarians = {
                        user['id']: f"{user['first_name']} {user['last_name']}"
                        for user in users_data['users']
                        if user['role'] == 'veterinarian'
                    }

                    # Agregar nombres de veterinarios a los registros
                    for record in all_records:
                        vet_id = record.get('veterinarian_id')
                        record['veterinarian_name'] = veterinarians.get(vet_id, 'Veterinario desconocido')

                    print(f"✅ {len(veterinarians)} veterinarios procesados")

        except Exception as e:
            print(f"⚠️ Error obteniendo veterinarios: {e}")

        # PASO 4: Ordenar por fecha más reciente
        all_records.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        print(f"✅ Total de historias clínicas obtenidas: {len(all_records)}")

        return jsonify({
            'success': True,
            'medical_records': all_records,
            'total': len(all_records)
        })

    except Exception as e:
        print(f"❌ Error en api_get_medical_records: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/medical-records', methods=['POST'])
@role_required(['admin'])
def api_create_medical_record():
    """Crear nueva historia clínica"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        print(f"📡 Creando historia clínica con datos: {data}")

        # Validar datos básicos
        required_fields = ['pet_id', 'veterinarian_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        # Validar UUIDs
        import uuid
        try:
            uuid.UUID(str(data.get('pet_id')))
            uuid.UUID(str(data.get('veterinarian_id')))
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'IDs de mascota o veterinario inválidos'
            }), 400

        # Crear historia clínica en Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/records"
        response = requests.post(medical_url, json=data, headers=headers, timeout=15)

        print(f"📡 Respuesta Medical Service: {response.status_code}")

        if response.status_code == 201:
            response_data = response.json()
            if response_data.get('success'):
                record = response_data.get('medical_record', {})

                # Enriquecer respuesta con datos adicionales
                try:
                    # Obtener datos de la mascota
                    pet_response = requests.get(
                        f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{record.get('pet_id')}",
                        headers=headers,
                        timeout=5
                    )

                    if pet_response.status_code == 200:
                        pet_data = pet_response.json()
                        if pet_data.get('success'):
                            pet = pet_data['pet']
                            record.update({
                                'pet_name': pet['name'],
                                'pet_species': pet['species'],
                                'owner_name': 'Propietario'  # Simplificado por ahora
                            })

                    # Obtener datos del veterinario
                    users_response = requests.get(
                        f"{current_app.config['AUTH_SERVICE_URL']}/auth/users",
                        headers=headers,
                        timeout=5
                    )

                    if users_response.status_code == 200:
                        users_data = users_response.json()
                        if users_data.get('success'):
                            vet = next(
                                (u for u in users_data['users'] if u['id'] == record.get('veterinarian_id')),
                                None
                            )
                            if vet:
                                record['veterinarian_name'] = f"{vet['first_name']} {vet['last_name']}"

                except Exception as e:
                    print(f"⚠️ Error enriqueciendo datos: {e}")

                print(f"✅ Historia clínica creada: {record.get('id')}")

                return jsonify({
                    'success': True,
                    'message': 'Historia clínica creada exitosamente',
                    'medical_record': record
                })

        # Manejar errores del Medical Service
        try:
            error_data = response.json()
            error_message = error_data.get('message', f'Error del Medical Service: {response.status_code}')
        except:
            error_message = f'Error del Medical Service: {response.status_code}'

        print(f"❌ Error Medical Service: {error_message}")

        return jsonify({
            'success': False,
            'message': error_message
        }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_create_medical_record: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


@frontend_bp.route('/api/admin/medical-records/<record_id>', methods=['GET'])
@role_required(['admin'])
def api_get_medical_record(record_id):
    """Obtener historia clínica específica"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener historia clínica del Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/records/{record_id}"
        response = requests.get(medical_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                record = data.get('medical_record', {})

                # Enriquecer con datos adicionales
                try:
                    # Datos de la mascota
                    pet_response = requests.get(
                        f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{record.get('pet_id')}",
                        headers=headers,
                        timeout=5
                    )

                    if pet_response.status_code == 200:
                        pet_data = pet_response.json()
                        if pet_data.get('success'):
                            pet = pet_data['pet']
                            record.update({
                                'pet_name': pet['name'],
                                'pet_species': pet['species'],
                                'owner_name': 'Propietario'
                            })

                    # Datos del veterinario
                    users_response = requests.get(
                        f"{current_app.config['AUTH_SERVICE_URL']}/auth/users",
                        headers=headers,
                        timeout=5
                    )

                    if users_response.status_code == 200:
                        users_data = users_response.json()
                        if users_data.get('success'):
                            vet = next(
                                (u for u in users_data['users'] if u['id'] == record.get('veterinarian_id')),
                                None
                            )
                            if vet:
                                record['veterinarian_name'] = f"{vet['first_name']} {vet['last_name']}"

                except Exception as e:
                    print(f"⚠️ Error enriqueciendo datos: {e}")

                return jsonify({
                    'success': True,
                    'medical_record': record
                })

        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Historia clínica no encontrada'
            }), 404
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Medical Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_get_medical_record: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/medical-records/<record_id>', methods=['PUT'])
@role_required(['admin'])
def api_update_medical_record(record_id):
    """Actualizar historia clínica específica"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        # Actualizar historia clínica en Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/records/{record_id}"
        response = requests.put(medical_url, json=data, headers=headers, timeout=10)

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Historia clínica actualizada exitosamente',
                    'medical_record': response_data.get('medical_record', {})
                })

        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Historia clínica no encontrada'
            }), 404
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Medical Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_update_medical_record: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/medical-records/<record_id>/complete', methods=['PUT'])
@role_required(['admin'])
def api_complete_medical_record(record_id):
    """Marcar historia clínica como completada"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Completar historia clínica en Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/records/{record_id}/complete"
        response = requests.put(medical_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Historia clínica marcada como completada',
                    'medical_record': data.get('medical_record', {})
                })

        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Historia clínica no encontrada'
            }), 404
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Medical Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_complete_medical_record: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/medical-records/<record_id>', methods=['DELETE'])
@role_required(['admin'])
def api_delete_medical_record(record_id):
    """Eliminar historia clínica definitivamente"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Eliminar historia clínica en Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/records/{record_id}"
        response = requests.delete(medical_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Historia clínica eliminada exitosamente'
                })

        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Historia clínica no encontrada'
            }), 404
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Medical Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_delete_medical_record: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== API ENDPOINTS PARA PRESCRIPCIONES ===============

@frontend_bp.route('/api/admin/prescriptions', methods=['POST'])
@role_required(['admin'])
def api_create_prescription():
    """Crear nueva prescripción"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        # Validar datos básicos
        required_fields = ['medical_record_id', 'medication_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        # Crear prescripción en Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/prescriptions"
        response = requests.post(medical_url, json=data, headers=headers, timeout=10)

        if response.status_code == 201:
            response_data = response.json()
            if response_data.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Prescripción creada exitosamente',
                    'prescription': response_data.get('prescription', {})
                })

        # Manejar errores
        try:
            error_data = response.json()
            error_message = error_data.get('message', f'Error del Medical Service: {response.status_code}')
        except:
            error_message = f'Error del Medical Service: {response.status_code}'

        return jsonify({
            'success': False,
            'message': error_message
        }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_create_prescription: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500




# =============== ESTADÍSTICAS DE HISTORIAS CLÍNICAS ===============

@frontend_bp.route('/api/admin/medical-records/stats')
@role_required(['admin'])
def api_get_medical_records_stats():
    """Obtener estadísticas de historias clínicas"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener todas las historias clínicas usando nuestra propia API
        records_response = requests.get(
            'http://localhost:3000/api/admin/medical-records',
            headers={'Authorization': f"Bearer {session.get('token')}"},
            timeout=10
        )

        default_stats = {
            'total_records': 0,
            'records_today': 0,
            'emergency_records': 0,
            'completed_records': 0,
            'by_status': {
                'draft': 0,
                'completed': 0,
                'reviewed': 0
            },
            'by_species': {
                'perro': 0,
                'gato': 0,
                'otros': 0
            }
        }

        if records_response.status_code != 200:
            return jsonify({
                'success': True,
                'stats': default_stats
            })

        records_data = records_response.json()
        if not records_data.get('success'):
            return jsonify({
                'success': True,
                'stats': default_stats
            })

        records = records_data.get('medical_records', [])

        # Calcular estadísticas
        from datetime import datetime, date
        today = date.today()

        total_records = len(records)

        records_today = 0
        for record in records:
            try:
                created_date = datetime.fromisoformat(record['created_at'].replace('Z', '+00:00')).date()
                if created_date == today:
                    records_today += 1
            except:
                pass

        emergency_records = len([r for r in records if r.get('is_emergency', False)])
        completed_records = len([r for r in records if r.get('status') == 'completed'])

        # Por estado
        by_status = {
            'draft': len([r for r in records if r.get('status') == 'draft']),
            'completed': len([r for r in records if r.get('status') == 'completed']),
            'reviewed': len([r for r in records if r.get('status') == 'reviewed'])
        }

        # Por especie
        by_species = {
            'perro': len([r for r in records if r.get('pet_species') == 'perro']),
            'gato': len([r for r in records if r.get('pet_species') == 'gato']),
            'otros': len([r for r in records if r.get('pet_species') not in ['perro', 'gato']])
        }

        return jsonify({
            'success': True,
            'stats': {
                'total_records': total_records,
                'records_today': records_today,
                'emergency_records': emergency_records,
                'completed_records': completed_records,
                'by_status': by_status,
                'by_species': by_species
            }
        })

    except Exception as e:
        print(f"❌ Error en api_get_medical_records_stats: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# =============== RUTAS PARA GESTIÓN DE CITAS ===============

@frontend_bp.route('/appointments')
@role_required(['admin', 'receptionist', 'veterinarian'])  # ← CORREGIDO
def appointments():
    """Lista de citas - redirige al admin"""
    user_role = session['user'].get('role')

    if user_role == 'admin':
        return redirect(url_for('frontend.admin_appointments'))
    elif user_role == 'receptionist':
        return redirect(url_for('frontend.receptionist_dashboard'))
    elif user_role == 'veterinarian':
        return redirect(url_for('frontend.veterinarian_dashboard'))
    else:
        flash('No tienes permisos para acceder a las citas', 'error')
        return redirect(url_for('frontend.dashboard'))

@frontend_bp.route('/api/admin/appointments')
@role_required(['admin'])
def api_get_appointments():
    """API endpoint para obtener todas las citas"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Parámetros de filtro opcionales
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        veterinarian_id = request.args.get('veterinarian_id')
        status = request.args.get('status')
        client_id = request.args.get('client_id')

        # CORRECCIÓN: Usar la ruta correcta del Appointment Service
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/appointments"
        params = {}

        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if veterinarian_id:
            params['veterinarian_id'] = veterinarian_id
        if status:
            params['status'] = status
        if client_id:
            params['client_id'] = client_id

        print(f"📡 Llamando a: {appointment_url} con parámetros: {params}")
        response = requests.get(appointment_url, headers=headers, params=params, timeout=10)
        print(f"📡 Respuesta del Appointment Service: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                # Enriquecer datos de citas con información de usuarios y mascotas
                appointments = data.get('appointments', [])
                enriched_appointments = []

                # Obtener usuarios para mapear veterinarios y clientes
                try:
                    users_response = requests.get(
                        f"{current_app.config['AUTH_SERVICE_URL']}/auth/users",
                        headers=headers,
                        timeout=5
                    )
                    users_data = []
                    if users_response.status_code == 200:
                        users_json = users_response.json()
                        if users_json.get('success'):
                            users_data = users_json.get('users', [])

                    users_map = {user['id']: user for user in users_data}

                    # Obtener mascotas
                    pets_response = requests.get(
                        f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets",
                        headers=headers,
                        timeout=5
                    )
                    pets_data = []
                    if pets_response.status_code == 200:
                        pets_json = pets_response.json()
                        if pets_json.get('success'):
                            pets_data = pets_json.get('pets', [])

                    pets_map = {pet['id']: pet for pet in pets_data}

                    # Enriquecer cada cita
                    for appointment in appointments:
                        vet_id = appointment.get('veterinarian_id')
                        client_id = appointment.get('client_id')
                        pet_id = appointment.get('pet_id')

                        vet = users_map.get(vet_id, {})
                        client = users_map.get(client_id, {})
                        pet = pets_map.get(pet_id, {})

                        enriched_appointment = {
                            **appointment,
                            'veterinarian_name': f"{vet.get('first_name', '')} {vet.get('last_name', '')}".strip() or 'Veterinario desconocido',
                            'client_name': f"{client.get('first_name', '')} {client.get('last_name', '')}".strip() or 'Cliente desconocido',
                            'client_email': client.get('email', ''),
                            'client_phone': client.get('phone', ''),
                            'pet_name': pet.get('name', 'Mascota desconocida'),
                            'pet_species': pet.get('species', 'unknown')
                        }
                        enriched_appointments.append(enriched_appointment)

                except Exception as e:
                    print(f"⚠️ Error enriqueciendo datos de citas: {e}")
                    enriched_appointments = appointments

                return jsonify({
                    'success': True,
                    'appointments': enriched_appointments,
                    'total': len(enriched_appointments)
                })
            else:
                return jsonify({
                    'success': True,
                    'appointments': [],
                    'total': 0
                })
        else:
            # Si falla, retornar datos de ejemplo como fallback
            print(f"⚠️ Error conectando con Appointment Service: {response.status_code}")
            print(f"⚠️ URL llamada: {appointment_url}")
            example_appointments = get_example_appointments_data()
            return jsonify({
                'success': True,
                'appointments': example_appointments,
                'total': len(example_appointments),
                'message': 'Usando datos de ejemplo - Servicio no disponible'
            })

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        # Fallback con datos de ejemplo
        example_appointments = get_example_appointments_data()
        return jsonify({
            'success': True,
            'appointments': example_appointments,
            'total': len(example_appointments),
            'message': 'Usando datos de ejemplo (sin conexión)'
        })
    except Exception as e:
        print(f"❌ Error en api_get_appointments: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


def get_example_appointments_data():
    """Datos de ejemplo para citas cuando no hay conexión con el servicio"""
    from datetime import datetime, timedelta

    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(days=7)

    return [
        {
            'id': 'apt_001',
            'pet_id': 'pet_001',
            'pet_name': 'Max',
            'pet_species': 'perro',
            'client_id': 'client_001',
            'client_name': 'Carlos López',
            'client_phone': '+1234567893',
            'client_email': 'carlos@example.com',
            'veterinarian_id': 'vet_001',
            'veterinarian_name': 'Dr. Juan Pérez',
            'appointment_date': today.strftime('%Y-%m-%d'),
            'appointment_time': '10:00',
            'status': 'confirmed',
            'priority': 'normal',
            'reason': 'Consulta de rutina y vacunación anual',
            'notes': 'Primera visita del año. Revisar historial de vacunas.',
            'created_at': today.isoformat(),
            'updated_at': today.isoformat()
        },
        {
            'id': 'apt_002',
            'pet_id': 'pet_002',
            'pet_name': 'Luna',
            'pet_species': 'gato',
            'client_id': 'client_001',
            'client_name': 'Carlos López',
            'client_phone': '+1234567893',
            'client_email': 'carlos@example.com',
            'veterinarian_id': 'vet_001',
            'veterinarian_name': 'Dr. Juan Pérez',
            'appointment_date': tomorrow.strftime('%Y-%m-%d'),
            'appointment_time': '14:30',
            'status': 'scheduled',
            'priority': 'urgent',
            'reason': 'Control post-operatorio esterilización',
            'notes': 'Revisar cicatrización y retirar puntos si es necesario.',
            'created_at': today.isoformat(),
            'updated_at': today.isoformat()
        },
        {
            'id': 'apt_003',
            'pet_id': 'pet_003',
            'pet_name': 'Rocky',
            'pet_species': 'perro',
            'client_id': 'client_002',
            'client_name': 'María González',
            'client_phone': '+1234567894',
            'client_email': 'maria@example.com',
            'veterinarian_id': 'vet_002',
            'veterinarian_name': 'Dra. Laura Rodríguez',
            'appointment_date': next_week.strftime('%Y-%m-%d'),
            'appointment_time': '16:00',
            'status': 'scheduled',
            'priority': 'emergency',
            'reason': 'Dificultad respiratoria - Emergencia',
            'notes': 'Cliente reporta respiración muy dificultosa desde anoche.',
            'created_at': today.isoformat(),
            'updated_at': today.isoformat()
        }
    ]


@frontend_bp.route('/api/admin/appointments', methods=['POST'])
@role_required(['admin'])
def api_create_appointment():
    """Crear nueva cita"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        # Validar datos básicos
        required_fields = ['pet_id', 'veterinarian_id', 'client_id', 'appointment_date', 'appointment_time']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        # Crear cita en Appointment Service
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/create"
        response = requests.post(appointment_url, json=data, headers=headers, timeout=10)

        if response.status_code == 201:
            response_data = response.json()
            if response_data.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Cita creada exitosamente',
                    'appointment': response_data.get('appointment', {})
                })

        # Manejar errores
        try:
            error_data = response.json()
            error_message = error_data.get('message', f'Error del Appointment Service: {response.status_code}')
        except:
            error_message = f'Error del Appointment Service: {response.status_code}'

        return jsonify({
            'success': False,
            'message': error_message
        }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_create_appointment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/appointments/<appointment_id>', methods=['GET'])
@role_required(['admin'])
def api_get_appointment(appointment_id):
    """Obtener cita específica"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener cita del Appointment Service
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/appointments/{appointment_id}"
        response = requests.get(appointment_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                appointment = data.get('appointment', {})

                # Enriquecer con datos adicionales
                try:
                    # Obtener usuarios para veterinario y cliente
                    users_response = requests.get(
                        f"{current_app.config['AUTH_SERVICE_URL']}/auth/users",
                        headers=headers,
                        timeout=5
                    )

                    if users_response.status_code == 200:
                        users_data = users_response.json()
                        if users_data.get('success'):
                            users = {user['id']: user for user in users_data['users']}

                            # Enriquecer veterinario
                            vet_id = appointment.get('veterinarian_id')
                            if vet_id and vet_id in users:
                                vet = users[vet_id]
                                appointment['veterinarian_name'] = f"{vet['first_name']} {vet['last_name']}"

                            # Enriquecer cliente
                            client_id = appointment.get('client_id')
                            if client_id and client_id in users:
                                client = users[client_id]
                                appointment.update({
                                    'client_name': f"{client['first_name']} {client['last_name']}",
                                    'client_email': client.get('email', ''),
                                    'client_phone': client.get('phone', '')
                                })

                    # Obtener mascota
                    pet_id = appointment.get('pet_id')
                    if pet_id:
                        pet_response = requests.get(
                            f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}",
                            headers=headers,
                            timeout=5
                        )
                        if pet_response.status_code == 200:
                            pet_data = pet_response.json()
                            if pet_data.get('success'):
                                pet = pet_data['pet']
                                appointment.update({
                                    'pet_name': pet['name'],
                                    'pet_species': pet['species'],
                                    'pet_breed': pet.get('breed', '')
                                })

                except Exception as e:
                    print(f"⚠️ Error enriqueciendo datos de cita: {e}")

                return jsonify({
                    'success': True,
                    'appointment': appointment
                })

        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Cita no encontrada'
            }), 404
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Appointment Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_get_appointment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/appointments/<appointment_id>', methods=['PUT'])
@role_required(['admin'])
def api_update_appointment(appointment_id):
    """Actualizar cita específica"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        # Actualizar cita en Appointment Service
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/update/{appointment_id}"
        response = requests.put(appointment_url, json=data, headers=headers, timeout=10)

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Cita actualizada exitosamente',
                    'appointment': response_data.get('appointment', {})
                })

        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Cita no encontrada'
            }), 404
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Appointment Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_update_appointment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/appointments/<appointment_id>/confirm', methods=['PUT'])
@role_required(['admin'])
def api_confirm_appointment(appointment_id):
    """Confirmar cita"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Confirmar cita en Appointment Service
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/confirm/{appointment_id}"
        response = requests.put(appointment_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Cita confirmada exitosamente',
                    'appointment': data.get('appointment', {})
                })

        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Cita no encontrada'
            }), 404
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Appointment Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_confirm_appointment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/appointments/<appointment_id>/complete', methods=['PUT'])
@role_required(['admin'])
def api_complete_appointment(appointment_id):
    """Completar cita"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Completar cita en Appointment Service
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/complete/{appointment_id}"
        response = requests.put(appointment_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Cita completada exitosamente',
                    'appointment': data.get('appointment', {})
                })

        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Cita no encontrada'
            }), 404
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith(
                'application/json') else {}
            return jsonify({
                'success': False,
                'message': error_data.get('message', f'Error del Appointment Service: {response.status_code}')
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_complete_appointment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/appointments/<appointment_id>/cancel', methods=['PUT'])
@role_required(['admin'])
def api_cancel_appointment(appointment_id):
    """Cancelar cita"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Cancelar cita en Appointment Service
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/cancel/{appointment_id}"
        response = requests.put(appointment_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Cita cancelada exitosamente',
                    'appointment': data.get('appointment', {})
                })

        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Cita no encontrada'
            }), 404
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Appointment Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_cancel_appointment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/appointments/<appointment_id>', methods=['DELETE'])
@role_required(['admin'])
def api_delete_appointment(appointment_id):
    """Eliminar cita definitivamente"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Eliminar cita en Appointment Service
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/appointments/{appointment_id}"
        response = requests.delete(appointment_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Cita eliminada exitosamente'
                })

        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Cita no encontrada'
            }), 404
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Appointment Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_delete_appointment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/appointments/today')
@role_required(['admin'])
def api_get_today_appointments():
    """Obtener citas de hoy"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener citas de hoy desde Appointment Service
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/today"
        response = requests.get(appointment_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify(data)
            else:
                return jsonify({
                    'success': True,
                    'appointments': [],
                    'total': 0
                })
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Appointment Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_get_today_appointments: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/appointments/available-slots')
@role_required(['admin'])
def api_get_available_slots():
    """Obtener horarios disponibles"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener parámetros
        veterinarian_id = request.args.get('veterinarian_id')
        date = request.args.get('date')

        if not veterinarian_id or not date:
            return jsonify({
                'success': False,
                'message': 'Parámetros requeridos: veterinarian_id, date'
            }), 400

        # Obtener slots disponibles desde Appointment Service
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/available-slots"
        params = {
            'veterinarian_id': veterinarian_id,
            'date': date
        }

        response = requests.get(appointment_url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify(data)
            else:
                return jsonify({
                    'success': True,
                    'available_slots': [],
                    'date': date,
                    'veterinarian_id': veterinarian_id
                })
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Appointment Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_get_available_slots: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/appointments/stats')
@role_required(['admin'])
def api_get_appointments_stats():
    """Obtener estadísticas de citas"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener todas las citas para calcular estadísticas
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments"
        response = requests.get(appointment_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                appointments = data.get('appointments', [])

                # Calcular estadísticas
                from datetime import datetime, date
                today = date.today()

                total_appointments = len(appointments)
                today_appointments = len([a for a in appointments
                                          if a.get('appointment_date') == today.isoformat()])

                # Por estado
                scheduled = len([a for a in appointments if a.get('status') == 'scheduled'])
                confirmed = len([a for a in appointments if a.get('status') == 'confirmed'])
                completed = len([a for a in appointments if a.get('status') == 'completed'])
                cancelled = len([a for a in appointments if a.get('status') == 'cancelled'])

                return jsonify({
                    'success': True,
                    'stats': {
                        'total_appointments': total_appointments,
                        'today_appointments': today_appointments,
                        'by_status': {
                            'scheduled': scheduled,
                            'confirmed': confirmed,
                            'completed': completed,
                            'cancelled': cancelled
                        }
                    }
                })
            else:
                return jsonify({
                    'success': True,
                    'stats': {
                        'total_appointments': 0,
                        'today_appointments': 0,
                        'by_status': {
                            'scheduled': 0,
                            'confirmed': 0,
                            'completed': 0,
                            'cancelled': 0
                        }
                    }
                })
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Appointment Service: {response.status_code}'
            }), response.status_code

    except Exception as e:
        print(f"❌ Error en api_get_appointments_stats: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/admin/inventory')
@role_required(['admin'])
def admin_inventory():
    """Página de gestión de inventario"""
    try:
        # Configurar recursos necesarios
        ensure_placeholder_images()
        setup_upload_directories()

        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Administrador',
            'user_role': user.get('role', 'admin').title(),
            'user_initial': user.get('first_name', 'A')[0].upper() if user.get('first_name') else 'A'
        }

        print(f"✅ Cargando página de gestión de inventario para usuario: {user.get('email')}")
        return render_template('admin/sections/inventory-management.html', **template_data)

    except Exception as e:
        print(f"❌ Error en admin_inventory: {e}")
        flash('Error al cargar la gestión de inventario', 'error')
        return redirect(url_for('frontend.admin_dashboard'))


# =============== API ENDPOINTS PARA INVENTARIO ===============

@frontend_bp.route('/api/admin/inventory/medications')
@role_required(['admin'])
def api_get_medications():
    """API endpoint para obtener medicamentos - VERSIÓN DEFINITIVA"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Parámetros de filtro opcionales
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        category = request.args.get('category')
        search = request.args.get('search')

        # Construir URL con parámetros
        params = {}
        if include_inactive:
            params['include_inactive'] = 'true'
        if category:
            params['category'] = category

        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/medications"

        if search:
            inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/medications/search"
            params['q'] = search

        response = requests.get(inventory_url, headers=headers, params=params, timeout=10)

        print(f"📡 Llamada a Inventory Service: {inventory_url}")
        print(f"📡 Parámetros: {params}")
        print(f"📡 Respuesta: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                medications = data.get('medications', [])

                # Enriquecer datos de medicamentos con cálculos
                for med in medications:
                    # Calcular días hasta vencimiento
                    if med.get('expiration_date'):
                        try:
                            from datetime import datetime, date
                            exp_date = datetime.strptime(med['expiration_date'], '%Y-%m-%d').date()
                            today = date.today()
                            days_to_expiry = (exp_date - today).days
                            med['days_to_expiration'] = days_to_expiry
                        except:
                            med['days_to_expiration'] = None

                    # Calcular estado del stock
                    stock = med.get('stock_quantity', 0)
                    min_stock = med.get('minimum_stock_alert', 10)

                    if stock == 0:
                        med['stock_status'] = 'out_of_stock'
                    elif stock <= min_stock:
                        med['stock_status'] = 'low_stock'
                    else:
                        med['stock_status'] = 'in_stock'

                    # Calcular valor total
                    unit_price = med.get('unit_price', 0)
                    total_value = float(unit_price) * stock if unit_price else 0
                    med['total_value'] = total_value

                print(f"✅ {len(medications)} medicamentos obtenidos y enriquecidos")

                return jsonify({
                    'success': True,
                    'medications': medications,
                    'total': len(medications)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': data.get('message', 'Error desconocido')
                }), 400
        else:
            # Fallback con datos de ejemplo si el servicio no está disponible
            print(f"⚠️ Inventory Service no disponible: {response.status_code}")
            example_medications = get_example_medications_data()
            return jsonify({
                'success': True,
                'medications': example_medications,
                'total': len(example_medications),
                'message': 'Usando datos de ejemplo - Servicio no disponible'
            })

    except requests.RequestException as e:
        print(f"❌ Error conectando con Inventory Service: {e}")
        # Fallback con datos de ejemplo
        example_medications = get_example_medications_data()
        return jsonify({
            'success': True,
            'medications': example_medications,
            'total': len(example_medications),
            'message': 'Usando datos de ejemplo (sin conexión)'
        })
    except Exception as e:
        print(f"❌ Error en api_get_medications: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/inventory/medications', methods=['POST'])
@role_required(['admin'])
def api_create_medication():
    """Crear nuevo medicamento"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        print(f"📡 Creando medicamento: {data.get('name')}")

        # Validar datos básicos
        required_fields = ['name', 'unit_price']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        # Crear medicamento en Inventory Service
        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/medications"
        response = requests.post(inventory_url, json=data, headers=headers, timeout=10)

        if response.status_code == 201:
            response_data = response.json()
            if response_data.get('success'):
                print(f"✅ Medicamento creado: {response_data.get('medication', {}).get('id')}")
                return jsonify(response_data)

        # Manejar errores
        try:
            error_data = response.json()
            error_message = error_data.get('message', f'Error del Inventory Service: {response.status_code}')
        except:
            error_message = f'Error del Inventory Service: {response.status_code}'

        return jsonify({
            'success': False,
            'message': error_message
        }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Inventory Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de inventario'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_create_medication: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/inventory/medications/<medication_id>', methods=['PUT'])
@role_required(['admin'])
def api_update_medication(medication_id):
    """Actualizar medicamento específico"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        print(f"📡 Actualizando medicamento: {medication_id}")

        # Actualizar medicamento en Inventory Service
        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/medications/{medication_id}"
        response = requests.put(inventory_url, json=data, headers=headers, timeout=10)

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success'):
                print(f"✅ Medicamento actualizado: {medication_id}")
                return jsonify(response_data)

        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Medicamento no encontrado'
            }), 404
        else:
            try:
                error_data = response.json()
                error_message = error_data.get('message', f'Error del Inventory Service: {response.status_code}')
            except:
                error_message = f'Error del Inventory Service: {response.status_code}'

            return jsonify({
                'success': False,
                'message': error_message
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Inventory Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de inventario'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_update_medication: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/inventory/medications/<medication_id>', methods=['DELETE'])
@role_required(['admin'])
def api_delete_medication(medication_id):
    """Eliminar/desactivar medicamento"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"📡 Eliminando medicamento: {medication_id}")

        # Desactivar medicamento en Inventory Service
        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/medications/{medication_id}/deactivate"
        response = requests.put(inventory_url, headers=headers, timeout=10)

        if response.status_code == 200:
            print(f"✅ Medicamento desactivado: {medication_id}")
            return jsonify({
                'success': True,
                'message': 'Medicamento eliminado exitosamente'
            })
        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Medicamento no encontrado'
            }), 404
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Inventory Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Inventory Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de inventario'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_delete_medication: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/inventory/summary')
@role_required(['admin'])
def api_get_inventory_summary():
    """Obtener resumen del inventario"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener resumen desde Inventory Service
        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/summary"
        response = requests.get(inventory_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify(data)

        # Fallback con datos calculados localmente
        return jsonify({
            'success': True,
            'summary': {
                'total_medications': 0,
                'total_inventory_value': 0,
                'low_stock_count': 0,
                'out_of_stock_count': 0,
                'expiring_soon_count': 0
            },
            'message': 'Datos no disponibles del servicio'
        })

    except Exception as e:
        print(f"❌ Error en api_get_inventory_summary: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/inventory/stock/update', methods=['POST'])
@role_required(['admin'])
def api_update_stock():
    """Actualizar stock de medicamento - VERSIÓN CORREGIDA"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        print(f"📦 Datos recibidos para actualizar stock: {data}")

        # CORRECCIÓN PRINCIPAL: Limpiar y validar campos opcionales
        movement_type = data.get('movement_type')
        medication_id = data.get('medication_id')
        quantity = data.get('quantity', 0)
        reason = data.get('reason', '')

        # Limpiar reference_id - convertir string vacío a None
        reference_id = data.get('reference_id')
        if reference_id == '' or reference_id == 'null' or not reference_id:
            reference_id = None

        # Limpiar user_id - usar el ID del usuario actual de la sesión
        user_id = session.get('user', {}).get('id')
        if not user_id:
            user_id = None

        # Validar datos básicos
        if not all([medication_id, movement_type, reason]):
            return jsonify({
                'success': False,
                'message': 'Campos requeridos: medication_id, movement_type, reason'
            }), 400

        if quantity <= 0:
            return jsonify({
                'success': False,
                'message': 'La cantidad debe ser mayor a 0'
            }), 400

        # Preparar datos según el tipo de movimiento
        if movement_type == 'in':
            endpoint = '/inventory/add-stock'
            request_data = {
                'medication_id': medication_id,
                'quantity': quantity,
                'reason': reason,
                'user_id': user_id
            }
            # Solo agregar unit_cost si existe y es válido
            unit_cost = data.get('unit_cost')
            if unit_cost and float(unit_cost) > 0:
                request_data['unit_cost'] = float(unit_cost)

        elif movement_type == 'out':
            endpoint = '/inventory/reduce-stock'
            request_data = {
                'medication_id': medication_id,
                'quantity': quantity,
                'reason': reason,
                'reference_id': reference_id,  # Puede ser None
                'user_id': user_id
            }

        else:  # adjustment
            endpoint = '/inventory/update-stock'
            quantity_change = data.get('quantity_change', 0)
            request_data = {
                'medication_id': medication_id,
                'quantity_change': quantity_change,
                'reason': reason,
                'reference_id': reference_id,  # Puede ser None
                'user_id': user_id
            }

        print(f"📦 Enviando a {endpoint}: {request_data}")

        # Hacer petición al Inventory Service
        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}{endpoint}"
        response = requests.post(inventory_url, json=request_data, headers=headers, timeout=10)

        print(f"📦 Respuesta del Inventory Service: {response.status_code}")

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success'):
                print(f"✅ Stock actualizado exitosamente")
                return jsonify(response_data)

        # Manejar errores
        try:
            error_data = response.json()
            error_message = error_data.get('message', f'Error del Inventory Service: {response.status_code}')
        except:
            error_message = f'Error del Inventory Service: {response.status_code}'

        print(f"❌ Error: {error_message}")
        return jsonify({
            'success': False,
            'message': error_message
        }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Inventory Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de inventario'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_update_stock: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


@frontend_bp.route('/api/admin/inventory/movements')
@role_required(['admin'])
def api_get_stock_movements():
    """Obtener movimientos de stock"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener parámetros de consulta
        medication_id = request.args.get('medication_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit')

        # Construir URL con parámetros
        params = {}
        if medication_id:
            params['medication_id'] = medication_id
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if limit:
            params['limit'] = limit

        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/movements"
        response = requests.get(inventory_url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify(data)

        # Fallback con datos vacíos
        return jsonify({
            'success': True,
            'movements': [],
            'total': 0,
            'message': 'Datos no disponibles del servicio'
        })

    except Exception as e:
        print(f"❌ Error en api_get_stock_movements: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/inventory/alerts/low-stock')
@role_required(['admin'])
def api_get_low_stock_alerts():
    """Obtener alertas de stock bajo"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/alerts/low-stock"
        response = requests.get(inventory_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify(data)

        return jsonify({
            'success': True,
            'low_stock_medications': [],
            'total': 0
        })

    except Exception as e:
        print(f"❌ Error en api_get_low_stock_alerts: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/inventory/alerts/expiring')
@role_required(['admin'])
def api_get_expiring_medications():
    """Obtener medicamentos próximos a vencer"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        days = request.args.get('days', 30)

        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/alerts/expiring"
        params = {'days': days}
        response = requests.get(inventory_url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify(data)

        return jsonify({
            'success': True,
            'expiring_medications': [],
            'total': 0
        })

    except Exception as e:
        print(f"❌ Error en api_get_expiring_medications: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/inventory/categories')
@role_required(['admin'])
def api_get_medication_categories():
    """Obtener categorías de medicamentos"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/categories"
        response = requests.get(inventory_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify(data)

        # Fallback con categorías por defecto
        default_categories = [
            'Antibiótico', 'Analgésico', 'Antiinflamatorio', 'Antiparasitario',
            'Vitaminas', 'Vacunas', 'Sedante', 'Antiséptico', 'Suplemento'
        ]
        return jsonify({
            'success': True,
            'categories': default_categories
        })

    except Exception as e:
        print(f"❌ Error en api_get_medication_categories: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/inventory/search')
@role_required(['admin'])
def api_search_medications():
    """Buscar medicamentos"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        search_term = request.args.get('q', '')

        if not search_term:
            return jsonify({
                'success': False,
                'message': 'Parámetro de búsqueda requerido'
            }), 400

        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/medications/search"
        params = {'q': search_term}
        response = requests.get(inventory_url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify(data)

        return jsonify({
            'success': True,
            'medications': [],
            'total': 0,
            'search_term': search_term
        })

    except Exception as e:
        print(f"❌ Error en api_search_medications: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== DATOS DE EJEMPLO PARA FALLBACK ===============

def get_example_medications_data():
    """Datos de ejemplo mejorados para medicamentos cuando no hay conexión"""
    from datetime import datetime, timedelta

    today = datetime.now()
    future_date = today + timedelta(days=180)
    near_expiry = today + timedelta(days=25)

    return [
        {
            'id': 'med_001',
            'name': 'Amoxicilina 500mg',
            'category': 'Antibiótico',
            'presentation': 'Comprimidos',
            'concentration': '500mg',
            'laboratory': 'Laboratorios Veterinarios S.A.',
            'supplier': 'Distribuidora Médica',
            'unit_price': 2500.0,
            'stock_quantity': 45,
            'minimum_stock_alert': 20,
            'expiration_date': future_date.strftime('%Y-%m-%d'),
            'batch_number': 'AMX2024-001',
            'description': 'Antibiótico de amplio espectro para infecciones bacterianas',
            'storage_conditions': 'Conservar en lugar fresco y seco, temperatura ambiente',
            'is_active': True,
            'created_at': today.isoformat(),
            'updated_at': today.isoformat(),
            'stock_status': 'in_stock',
            'total_value': 112500.0,
            'days_to_expiration': 180
        },
        {
            'id': 'med_002',
            'name': 'Meloxicam 2mg/ml',
            'category': 'Antiinflamatorio',
            'presentation': 'Inyectable',
            'concentration': '2mg/ml',
            'laboratory': 'VetPharma',
            'supplier': 'Distribuidora Médica',
            'unit_price': 8500.0,
            'stock_quantity': 8,
            'minimum_stock_alert': 15,
            'expiration_date': near_expiry.strftime('%Y-%m-%d'),
            'batch_number': 'MLX2024-002',
            'description': 'Antiinflamatorio no esteroideo para dolor y inflamación',
            'storage_conditions': 'Refrigerar entre 2-8°C',
            'is_active': True,
            'created_at': today.isoformat(),
            'updated_at': today.isoformat(),
            'stock_status': 'low_stock',
            'total_value': 68000.0,
            'days_to_expiration': 25
        },
        {
            'id': 'med_003',
            'name': 'Vacuna Múltiple DHPP',
            'category': 'Vacunas',
            'presentation': 'Vial',
            'concentration': '1ml/dosis',
            'laboratory': 'BioVet',
            'supplier': 'Vacunas Veterinarias',
            'unit_price': 15000.0,
            'stock_quantity': 0,
            'minimum_stock_alert': 10,
            'expiration_date': near_expiry.strftime('%Y-%m-%d'),
            'batch_number': 'VAC2024-003',
            'description': 'Vacuna múltiple para perros (Distemper, Hepatitis, Parvovirus, Parainfluenza)',
            'storage_conditions': 'Conservar refrigerado 2-8°C, no congelar',
            'is_active': True,
            'created_at': today.isoformat(),
            'updated_at': today.isoformat(),
            'stock_status': 'out_of_stock',
            'total_value': 0.0,
            'days_to_expiration': 25
        },
        {
            'id': 'med_004',
            'name': 'Tramadol 50mg',
            'category': 'Analgésico',
            'presentation': 'Comprimidos',
            'concentration': '50mg',
            'laboratory': 'PainRelief Vet',
            'supplier': 'Farmacia Veterinaria Central',
            'unit_price': 1200.0,
            'stock_quantity': 120,
            'minimum_stock_alert': 30,
            'expiration_date': future_date.strftime('%Y-%m-%d'),
            'batch_number': 'TRA2024-004',
            'description': 'Analgésico opioide para dolor moderado a severo',
            'storage_conditions': 'Conservar en lugar seguro, temperatura ambiente',
            'is_active': True,
            'created_at': today.isoformat(),
            'updated_at': today.isoformat(),
            'stock_status': 'in_stock',
            'total_value': 144000.0,
            'days_to_expiration': 180
        },
        {
            'id': 'med_005',
            'name': 'Ivermectina 1mg/ml',
            'category': 'Antiparasitario',
            'presentation': 'Solución oral',
            'concentration': '1mg/ml',
            'laboratory': 'Parasit Control',
            'supplier': 'Antiparasitarios Vet',
            'unit_price': 3200.0,
            'stock_quantity': 25,
            'minimum_stock_alert': 20,
            'expiration_date': future_date.strftime('%Y-%m-%d'),
            'batch_number': 'IVE2024-005',
            'description': 'Antiparasitario interno y externo de amplio espectro',
            'storage_conditions': 'Proteger de la luz, temperatura ambiente',
            'is_active': True,
            'created_at': today.isoformat(),
            'updated_at': today.isoformat(),
            'stock_status': 'in_stock',
            'total_value': 80000.0,
            'days_to_expiration': 180
        }
    ]

@frontend_bp.route('/api/admin/inventory/alerts/check-expiration', methods=['POST'])
@role_required(['admin'])
def api_check_expiration_alerts():
    """Verificar y enviar alertas de vencimiento"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json() or {}

        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/alerts/check-expiration"
        response = requests.post(inventory_url, json=data, headers=headers, timeout=10)

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success'):
                return jsonify(response_data)

        return jsonify({
            'success': False,
            'message': f'Error del Inventory Service: {response.status_code}'
        }), response.status_code

    except Exception as e:
        print(f"❌ Error en api_check_expiration_alerts: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/inventory/export/csv')
@role_required(['admin'])
def api_export_inventory_csv():
    """Exportar inventario a CSV"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Redirigir al Inventory Service para descargar CSV
        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/export/csv"
        response = requests.get(inventory_url, headers=headers, timeout=30)

        if response.status_code == 200:
            # Reenviar la respuesta CSV al cliente
            from flask import Response
            return Response(
                response.content,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=inventario_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
                }
            )
        else:
            return jsonify({
                'success': False,
                'message': 'Error generando CSV'
            }), response.status_code

    except Exception as e:
        print(f"❌ Error en api_export_inventory_csv: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/admin/inventory/stats')
@role_required(['admin'])
def api_get_inventory_stats():
    """Obtener estadísticas del inventario"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/stats"
        response = requests.get(inventory_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify(data)

        return jsonify({
            'success': True,
            'stats': {
                'total_medications': 0,
                'by_species': {'dogs': 0, 'cats': 0, 'others': 0},
                'by_vaccination': {'complete': 0, 'partial': 0, 'pending': 0, 'unknown': 0},
                'by_age': {'puppies': 0, 'young': 0, 'adult': 0, 'senior': 0}
            }
        })

    except Exception as e:
        print(f"❌ Error en api_get_inventory_stats: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500






# =============== RUTAS DEL CLIENTE - COMPLETAS ===============

@frontend_bp.route('/client/dashboard')
@role_required(['client'])
def client_dashboard():
    """Dashboard principal para clientes"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener estadísticas básicas del cliente
        client_stats = {
            'my_pets_count': 0,
            'upcoming_appointments_count': 0,
            'pending_confirmations': 0,
            'unread_notifications': 0
        }

        # Intentar obtener datos reales de los servicios
        try:
            # Contar mascotas del cliente
            pets_response = requests.get(
                f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/owner/{user['id']}",
                headers=headers, timeout=5
            )
            if pets_response.status_code == 200:
                pets_data = pets_response.json()
                if pets_data.get('success'):
                    client_stats['my_pets_count'] = len(pets_data.get('pets', []))
        except:
            pass

        try:
            # Contar citas próximas
            appointments_response = requests.get(
                f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/client/{user['id']}/upcoming",
                headers=headers, timeout=5
            )
            if appointments_response.status_code == 200:
                apt_data = appointments_response.json()
                if apt_data.get('success'):
                    appointments = apt_data.get('appointments', [])
                    client_stats['upcoming_appointments_count'] = len(appointments)
                    client_stats['pending_confirmations'] = len(
                        [a for a in appointments if a.get('status') == 'scheduled'])
        except:
            pass

        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Cliente',
            'user_role': 'Cliente',
            'user_initial': user.get('first_name', 'C')[0].upper() if user.get('first_name') else 'C',
            **client_stats
        }

        return render_template('client/dashboard.html', **template_data)

    except Exception as e:
        print(f"❌ Error en client dashboard: {e}")
        flash('Error al cargar el dashboard', 'error')
        return redirect(url_for('frontend.login'))


@frontend_bp.route('/client/pets')
@role_required(['client'])
def client_pets():
    """Página de mascotas del cliente"""
    user = session.get('user', {})
    template_data = {
        'user': user,
        'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Cliente',
        'user_initial': user.get('first_name', 'C')[0].upper() if user.get('first_name') else 'C'
    }
    return render_template('client/sections/my-pets.html', **template_data)


@frontend_bp.route('/client/pets/add')
@role_required(['client'])
def client_add_pet():
    """Página para registrar nueva mascota"""
    user = session.get('user', {})
    template_data = {
        'user': user,
        'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Cliente',
        'user_initial': user.get('first_name', 'C')[0].upper() if user.get('first_name') else 'C'
    }
    return render_template('client/sections/add-pet.html', **template_data)


@frontend_bp.route('/client/appointments')
@role_required(['client'])
def client_appointments():
    """Página de citas del cliente"""
    user = session.get('user', {})
    template_data = {
        'user': user,
        'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Cliente',
        'user_initial': user.get('first_name', 'C')[0].upper() if user.get('first_name') else 'C'
    }
    return render_template('client/sections/appointments.html', **template_data)


@frontend_bp.route('/client/appointments/book')
@role_required(['client'])
def client_book_appointment():
    """Página para agendar cita"""
    user = session.get('user', {})
    template_data = {
        'user': user,
        'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Cliente',
        'user_initial': user.get('first_name', 'C')[0].upper() if user.get('first_name') else 'C'
    }
    return render_template('client/sections/book-appointment.html', **template_data)

@frontend_bp.route('/client/notifications')
@role_required(['client'])
def client_notifications():
    """Página de notificaciones"""
    user = session.get('user', {})
    template_data = {
        'user': user,
        'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Cliente',
        'user_initial': user.get('first_name', 'C')[0].upper() if user.get('first_name') else 'C'
    }
    return render_template('client/sections/notifications.html', **template_data)


@frontend_bp.route('/client/settings')
@role_required(['client'])
def client_settings():
    """Página de configuración"""
    user = session.get('user', {})
    template_data = {
        'user': user,
        'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Cliente',
        'user_initial': user.get('first_name', 'C')[0].upper() if user.get('first_name') else 'C'
    }
    return render_template('client/sections/settings.html', **template_data)


# =============== API ENDPOINTS DEL CLIENTE ===============



@frontend_bp.route('/api/client/pets/<pet_id>')
@role_required(['client'])
def api_client_pet_details(pet_id):
    """API para obtener detalles específicos de una mascota del cliente"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener detalles de la mascota
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}"
        response = requests.get(medical_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                pet = data.get('pet', {})

                # Verificar que la mascota pertenece al cliente
                if pet.get('owner_id') != user['id']:
                    return jsonify({
                        'success': False,
                        'message': 'No tienes acceso a esta mascota'
                    }), 403

                # Intentar obtener historial médico básico
                try:
                    records_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/records/pet/{pet_id}"
                    records_response = requests.get(records_url, headers=headers, timeout=5)

                    if records_response.status_code == 200:
                        records_data = records_response.json()
                        if records_data.get('success'):
                            pet['recent_visits'] = len(records_data.get('medical_records', []))
                            pet['last_visit'] = None
                            records = records_data.get('medical_records', [])
                            if records:
                                # Ordenar por fecha y tomar la más reciente
                                sorted_records = sorted(records, key=lambda x: x.get('created_at', ''), reverse=True)
                                pet['last_visit'] = sorted_records[0].get('created_at')
                        else:
                            pet['recent_visits'] = 0
                    else:
                        pet['recent_visits'] = 0
                except:
                    pet['recent_visits'] = 0

                return jsonify({
                    'success': True,
                    'pet': pet
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Mascota no encontrada'
                }), 404
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Medical Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_client_pet_details: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/client/pets/stats')
@role_required(['client'])
def api_client_pets_stats():
    """API para obtener estadísticas de mascotas del cliente"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener todas las mascotas del cliente
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/owner/{user['id']}"
        response = requests.get(medical_url, headers=headers, timeout=10)

        stats = {
            'total_pets': 0,
            'dogs_count': 0,
            'cats_count': 0,
            'upcoming_appointments': 0,
            'vaccination_complete': 0,
            'vaccination_pending': 0
        }

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                pets = data.get('pets', [])

                stats['total_pets'] = len(pets)
                stats['dogs_count'] = len([p for p in pets if p.get('species') == 'perro'])
                stats['cats_count'] = len([p for p in pets if p.get('species') == 'gato'])
                stats['vaccination_complete'] = len([p for p in pets if p.get('vaccination_status') == 'completo'])
                stats['vaccination_pending'] = len(
                    [p for p in pets if p.get('vaccination_status') in ['pendiente', 'parcial']])

        # Intentar obtener citas próximas
        try:
            appointments_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/client/{user['id']}/upcoming"
            appointments_response = requests.get(appointments_url, headers=headers, timeout=5)

            if appointments_response.status_code == 200:
                apt_data = appointments_response.json()
                if apt_data.get('success'):
                    stats['upcoming_appointments'] = len(apt_data.get('appointments', []))
        except:
            pass

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        print(f"❌ Error en api_client_pets_stats: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/client/appointments/upcoming')
@role_required(['client'])
def api_client_upcoming_appointments():
    """API para obtener citas próximas del cliente - VERSIÓN CORREGIDA"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"📅 Obteniendo citas próximas para cliente: {user['id']}")

        # CORRECCIÓN: Usar la nueva ruta específica
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/client/{user['id']}/upcoming"
        response = requests.get(appointment_url, headers=headers, timeout=10)

        print(f"📡 Upcoming appointments response: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                appointments = data.get('appointments', [])

                # Enriquecer con datos de mascotas
                try:
                    medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/owner/{user['id']}"
                    pets_response = requests.get(medical_url, headers=headers, timeout=5)

                    if pets_response.status_code == 200:
                        pets_data = pets_response.json()
                        if pets_data.get('success'):
                            pets_map = {pet['id']: pet for pet in pets_data.get('pets', [])}

                            for appointment in appointments:
                                pet_id = appointment.get('pet_id')
                                if pet_id and pet_id in pets_map:
                                    pet = pets_map[pet_id]
                                    appointment['pet_name'] = pet['name']
                                    appointment['pet_species'] = pet['species']
                except Exception as e:
                    print(f"⚠️ Error enriqueciendo citas próximas: {e}")

                return jsonify({
                    'success': True,
                    'appointments': appointments,
                    'total': len(appointments)
                })
            else:
                return jsonify({
                    'success': True,
                    'appointments': [],
                    'total': 0
                })
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Appointment Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_client_upcoming_appointments: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@frontend_bp.route('/api/client/dashboard/stats')
@role_required(['client'])
def api_client_dashboard_stats():
    """API para estadísticas del dashboard del cliente"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        stats = {
            'unread_notifications': 0,
            'pending_appointments': 0,
            'total_pets': 0
        }

        # Intentar obtener notificaciones no leídas
        try:
            notif_url = f"{current_app.config['NOTIFICATION_SERVICE_URL']}/notifications/user/{user['id']}/unread/count"
            notif_response = requests.get(notif_url, headers=headers, timeout=5)
            if notif_response.status_code == 200:
                notif_data = notif_response.json()
                if notif_data.get('success'):
                    stats['unread_notifications'] = notif_data.get('count', 0)
        except:
            pass

        # Obtener conteo de mascotas
        try:
            pets_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/owner/{user['id']}"
            pets_response = requests.get(pets_url, headers=headers, timeout=5)
            if pets_response.status_code == 200:
                pets_data = pets_response.json()
                if pets_data.get('success'):
                    stats['total_pets'] = len(pets_data.get('pets', []))
        except:
            pass

        # Obtener citas pendientes
        try:
            appointments_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/client/{user['id']}/upcoming"
            appointments_response = requests.get(appointments_url, headers=headers, timeout=5)
            if appointments_response.status_code == 200:
                apt_data = appointments_response.json()
                if apt_data.get('success'):
                    appointments = apt_data.get('appointments', [])
                    stats['pending_appointments'] = len([a for a in appointments if a.get('status') == 'scheduled'])
        except:
            pass

        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        print(f"❌ Error en api_client_dashboard_stats: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@frontend_bp.route('/api/client/pets', methods=['POST'])
@role_required(['client'])
def api_client_create_pet():
    """API para crear nueva mascota del cliente (solo datos, sin foto)"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Convertir FormData a JSON
        data = {}
        for key in request.form:
            value = request.form[key]
            if key == 'weight' and value:
                try:
                    data[key] = float(value)
                except ValueError:
                    data[key] = value
            else:
                data[key] = value

        # Agregar owner_id del usuario actual
        data['owner_id'] = user['id']

        print(f"📡 Enviando datos al Medical Service: {data}")

        # Enviar como JSON al Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets"
        response = requests.post(medical_url, json=data, headers=headers, timeout=15)

        print(f"📡 Respuesta Medical Service: {response.status_code}")

        if response.status_code == 201:
            result = response.json()
            if result.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Mascota registrada exitosamente',
                    'pet': result.get('pet', {})
                })

        # Manejar errores
        try:
            error_data = response.json()
            error_message = error_data.get('message', f'Error del Medical Service: {response.status_code}')
        except:
            error_message = f'Error del Medical Service: {response.status_code}'

        return jsonify({
            'success': False,
            'message': error_message
        }), 400

    except Exception as e:
        print(f"❌ Error en api_client_create_pet: {e}")
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500

""""@frontend_bp.route('/api/client/pets', methods=['POST'])
@role_required(['client'])
def api_client_create_pet():

    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener datos del formulario
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Si viene como FormData (con posible foto)
            data = {}

            # Obtener todos los campos del formulario
            for key in request.form:
                value = request.form[key]
                # Convertir valores numéricos
                if key == 'weight' and value:
                    try:
                        data[key] = float(value)
                    except ValueError:
                        data[key] = value
                else:
                    data[key] = value

            # Agregar owner_id del usuario actual
            data['owner_id'] = user['id']

            # PASO 1: Crear la mascota sin foto primero
            medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets"
            response = requests.post(medical_url, json=data, headers=headers, timeout=15)

            if response.status_code == 201:
                result = response.json()
                if result.get('success'):
                    pet = result.get('pet', {})
                    pet_id = pet.get('id')

                    # PASO 2: Subir foto si existe
                    if 'photo' in request.files:
                        photo = request.files['photo']
                        if photo and photo.filename:
                            try:
                                # Subir foto por separado
                                files = {'photo': photo}
                                photo_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}/photo"
                                photo_response = requests.post(
                                    photo_url,
                                    files=files,
                                    headers={'Authorization': headers['Authorization']},
                                    timeout=15
                                )

                                if photo_response.status_code == 200:
                                    photo_result = photo_response.json()
                                    if photo_result.get('success'):
                                        pet['photo_url'] = photo_result.get('photo_url')
                                        print(f"✅ Foto subida exitosamente: {pet['photo_url']}")
                                else:
                                    print(f"⚠️ Error subiendo foto: {photo_response.status_code}")
                            except Exception as photo_error:
                                print(f"⚠️ Error subiendo foto: {photo_error}")
                                # No fallar la creación de la mascota por la foto

                    return jsonify({
                        'success': True,
                        'message': 'Mascota registrada exitosamente',
                        'pet': pet
                    })

        else:
            # Si viene como JSON directo
            data = request.get_json()
            data['owner_id'] = user['id']

            medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets"
            response = requests.post(medical_url, json=data, headers=headers, timeout=15)

        # Manejar errores del Medical Service
        if response.status_code != 201:
            try:
                error_data = response.json()
                error_message = error_data.get('message', f'Error del Medical Service: {response.status_code}')
            except:
                error_message = f'Error del Medical Service: {response.status_code}'

            print(f"❌ Error Medical Service: {response.status_code} - {error_message}")
            return jsonify({
                'success': False,
                'message': error_message
            }), 400

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_client_create_pet: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500
"""

# =============== PROXY ROUTES PARA MICROSERVICIOS ===============



@frontend_bp.route('/api/client/appointments/upcoming')
@role_required(['client'])
def api_client_appointments_upcoming_proxy():
    """Proxy para citas próximas del cliente"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        apt_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/client/{user['id']}/upcoming"
        response = requests.get(apt_url, headers=headers, timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'success': True, 'appointments': []})

    except Exception as e:
        return jsonify({'success': True, 'appointments': []})



@frontend_bp.route('/client/pets/edit')
@role_required(['client'])
def client_pets_edit():
    """Página para editar mascota del cliente"""
    try:
        # Verificar que se especificó un ID de mascota
        pet_id = request.args.get('pet')
        if not pet_id:
            flash('No se especificó qué mascota editar', 'error')
            return redirect(url_for('frontend.client_pets'))

        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Verificar que la mascota existe y pertenece al usuario
        try:
            medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}"
            response = requests.get(medical_url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    pet = data.get('pet', {})

                    # Verificar que la mascota pertenece al usuario actual
                    if pet.get('owner_id') != user['id']:
                        flash('No tienes permisos para editar esta mascota', 'error')
                        return redirect(url_for('frontend.client_pets'))

                    print(f"✅ Accediendo a edición de mascota: {pet.get('name')} (ID: {pet_id})")
                else:
                    flash('Mascota no encontrada', 'error')
                    return redirect(url_for('frontend.client_pets'))
            else:
                flash('Error verificando la mascota', 'error')
                return redirect(url_for('frontend.client_pets'))

        except requests.RequestException as e:
            print(f"❌ Error conectando con Medical Service: {e}")
            flash('Error de conexión. Inténtalo de nuevo', 'error')
            return redirect(url_for('frontend.client_pets'))

        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Cliente',
            'user_initial': user.get('first_name', 'C')[0].upper() if user.get('first_name') else 'C',
            'pet_id': pet_id
        }

        return render_template('client/sections/edit-pet.html', **template_data)

    except Exception as e:
        print(f"❌ Error en client_pets_edit: {e}")
        flash('Error al cargar la página de edición', 'error')
        return redirect(url_for('frontend.client_pets'))


@frontend_bp.route('/api/client/pets/<pet_id>', methods=['PUT'])
@role_required(['client'])
def api_client_update_pet(pet_id):
    """API para actualizar mascota del cliente"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"📝 Cliente {user['id']} actualizando mascota {pet_id}")

        # PASO 1: Verificar que la mascota pertenece al usuario
        verify_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}"
        verify_response = requests.get(verify_url, headers=headers, timeout=10)

        if verify_response.status_code != 200:
            return jsonify({
                'success': False,
                'message': 'Mascota no encontrada'
            }), 404

        verify_data = verify_response.json()
        if not verify_data.get('success'):
            return jsonify({
                'success': False,
                'message': 'Error verificando mascota'
            }), 400

        pet_data = verify_data.get('pet', {})
        if pet_data.get('owner_id') != user['id']:
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para editar esta mascota'
            }), 403

        # PASO 2: Preparar datos de actualización
        if request.content_type and 'multipart/form-data' in request.content_type:
            # FormData con posible foto
            data = {}
            for key in request.form:
                value = request.form[key]
                if key == 'weight' and value:
                    try:
                        data[key] = float(value)
                    except ValueError:
                        data[key] = value
                else:
                    data[key] = value

            # Mantener el owner_id original
            data['owner_id'] = pet_data['owner_id']

            # PASO 3: Actualizar datos básicos primero
            medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}"
            response = requests.put(medical_url, json=data, headers=headers, timeout=15)

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    updated_pet = result.get('pet', {})

                    # PASO 4: Manejar foto si existe
                    if 'photo' in request.files:
                        photo = request.files['photo']
                        if photo and photo.filename:
                            try:
                                print(f"📸 Subiendo nueva foto para mascota {pet_id}")

                                # Subir nueva foto
                                files = {'photo': photo}
                                photo_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}/photo"
                                photo_response = requests.post(
                                    photo_url,
                                    files=files,
                                    headers={'Authorization': headers['Authorization']},
                                    timeout=15
                                )

                                if photo_response.status_code == 200:
                                    photo_result = photo_response.json()
                                    if photo_result.get('success'):
                                        updated_pet['photo_url'] = photo_result.get('photo_url')
                                        print(f"✅ Foto actualizada: {updated_pet['photo_url']}")
                                else:
                                    print(f"⚠️ Error subiendo foto: {photo_response.status_code}")

                            except Exception as photo_error:
                                print(f"⚠️ Error procesando foto: {photo_error}")
                                # No fallar la actualización por la foto

                    print(f"✅ Mascota {pet_id} actualizada exitosamente")

                    return jsonify({
                        'success': True,
                        'message': 'Mascota actualizada exitosamente',
                        'pet': updated_pet
                    })

        else:
            # JSON directo
            data = request.get_json()
            data['owner_id'] = pet_data['owner_id']

            medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}"
            response = requests.put(medical_url, json=data, headers=headers, timeout=15)

        # Manejar errores del Medical Service
        if response.status_code != 200:
            try:
                error_data = response.json()
                error_message = error_data.get('message', f'Error del Medical Service: {response.status_code}')
            except:
                error_message = f'Error del Medical Service: {response.status_code}'

            print(f"❌ Error Medical Service: {response.status_code} - {error_message}")
            return jsonify({
                'success': False,
                'message': error_message
            }), 400

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_client_update_pet: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500



@frontend_bp.route('/api/client/pets/<pet_id>', methods=['DELETE'])
@role_required(['client'])
def api_client_delete_pet(pet_id):
    """API para eliminar mascota del cliente"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"🗑️ Cliente {user['id']} eliminando mascota {pet_id}")

        # PASO 1: Verificar que la mascota pertenece al usuario
        verify_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}"
        verify_response = requests.get(verify_url, headers=headers, timeout=10)

        if verify_response.status_code != 200:
            return jsonify({
                'success': False,
                'message': 'Mascota no encontrada'
            }), 404

        verify_data = verify_response.json()
        if not verify_data.get('success'):
            return jsonify({
                'success': False,
                'message': 'Error verificando mascota'
            }), 400

        pet_data = verify_data.get('pet', {})
        if pet_data.get('owner_id') != user['id']:
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para eliminar esta mascota'
            }), 403

        # PASO 2: Verificar si hay citas futuras
        try:
            appointments_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/pet/{pet_id}/upcoming"
            appointments_response = requests.get(appointments_url, headers=headers, timeout=5)

            if appointments_response.status_code == 200:
                apt_data = appointments_response.json()
                if apt_data.get('success'):
                    upcoming_appointments = apt_data.get('appointments', [])
                    if upcoming_appointments:
                        return jsonify({
                            'success': False,
                            'message': f'No se puede eliminar la mascota porque tiene {len(upcoming_appointments)} cita(s) programada(s). Cancela las citas primero.'
                        }), 400
        except Exception as e:
            print(f"⚠️ Error verificando citas: {e}")
            # Continuar con la eliminación aunque no se puedan verificar las citas

        # PASO 3: Eliminar la mascota
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}"
        response = requests.delete(medical_url, headers=headers, timeout=15)

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ Mascota {pet_id} ({pet_data.get('name')}) eliminada exitosamente")

                return jsonify({
                    'success': True,
                    'message': f'Mascota {pet_data.get("name")} eliminada exitosamente'
                })

        # Manejar errores del Medical Service
        try:
            error_data = response.json()
            error_message = error_data.get('message', f'Error del Medical Service: {response.status_code}')
        except:
            error_message = f'Error del Medical Service: {response.status_code}'

        return jsonify({
            'success': False,
            'message': error_message
        }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_client_delete_pet: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500

@frontend_bp.route('/api/client/pets/<pet_id>/photo', methods=['POST'])
@role_required(['client'])
def api_client_update_pet_photo(pet_id):
    """API para actualizar solo la foto de una mascota del cliente"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"📸 Cliente {user['id']} actualizando foto de mascota {pet_id}")

        # Verificar que la mascota pertenece al usuario
        verify_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}"
        verify_response = requests.get(verify_url, headers=headers, timeout=10)

        if verify_response.status_code != 200:
            return jsonify({
                'success': False,
                'message': 'Mascota no encontrada'
            }), 404

        verify_data = verify_response.json()
        if not verify_data.get('success'):
            return jsonify({
                'success': False,
                'message': 'Error verificando mascota'
            }), 400

        pet_data = verify_data.get('pet', {})
        if pet_data.get('owner_id') != user['id']:
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para actualizar esta mascota'
            }), 403

        # Verificar que hay un archivo
        if 'photo' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No se encontró archivo'
            }), 400

        photo = request.files['photo']
        if photo.filename == '':
            return jsonify({
                'success': False,
                'message': 'No se seleccionó archivo'
            }), 400

        # Validaciones
        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
        file_extension = photo.filename.lower().split('.')[-1]

        if file_extension not in allowed_extensions:
            return jsonify({
                'success': False,
                'message': 'Tipo de archivo no permitido. Use JPG, PNG o GIF'
            }), 400

        # Validar tamaño del archivo
        photo.seek(0, 2)  # Ir al final
        file_size = photo.tell()
        photo.seek(0)  # Volver al inicio

        if file_size > 5 * 1024 * 1024:  # 5MB
            return jsonify({
                'success': False,
                'message': 'El archivo es demasiado grande. Máximo 5MB'
            }), 400

        # Subir foto al Medical Service
        try:
            files = {'photo': photo}
            photo_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}/photo"
            photo_response = requests.post(
                photo_url,
                files=files,
                headers={'Authorization': headers['Authorization']},
                timeout=15
            )

            if photo_response.status_code == 200:
                photo_result = photo_response.json()
                if photo_result.get('success'):
                    print(f"✅ Foto actualizada exitosamente para mascota {pet_id}")

                    return jsonify({
                        'success': True,
                        'message': 'Foto actualizada exitosamente',
                        'photo_url': photo_result.get('photo_url')
                    })

            # Error del Medical Service
            try:
                error_data = photo_response.json()
                error_message = error_data.get('message', f'Error subiendo foto: {photo_response.status_code}')
            except:
                error_message = f'Error subiendo foto: {photo_response.status_code}'

            return jsonify({
                'success': False,
                'message': error_message
            }), photo_response.status_code

        except requests.RequestException as e:
            print(f"❌ Error subiendo foto: {e}")
            return jsonify({
                'success': False,
                'message': 'Error de conexión subiendo la foto'
            }), 500

    except Exception as e:
        print(f"❌ Error en api_client_update_pet_photo: {e}")
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


@frontend_bp.route('/api/client/pets/<pet_id>/validate-owner')
@role_required(['client'])
def api_validate_pet_owner(pet_id):
    """Validar que una mascota pertenece al cliente actual"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}"
        response = requests.get(medical_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                pet = data.get('pet', {})

                if pet.get('owner_id') == user['id']:
                    return jsonify({
                        'success': True,
                        'valid': True,
                        'pet_name': pet.get('name'),
                        'message': 'Acceso autorizado'
                    })
                else:
                    return jsonify({
                        'success': True,
                        'valid': False,
                        'message': 'No tienes permisos para acceder a esta mascota'
                    }), 403
            else:
                return jsonify({
                    'success': False,
                    'valid': False,
                    'message': 'Mascota no encontrada'
                }), 404
        else:
            return jsonify({
                'success': False,
                'valid': False,
                'message': 'Error verificando mascota'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'valid': False,
            'message': 'Error de conexión'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_validate_pet_owner: {e}")
        return jsonify({
            'success': False,
            'valid': False,
            'message': 'Error interno'
        }), 500


# =============== RUTAS API PARA CLIENTES - VETERINARIOS Y CITAS ===============


@frontend_bp.route('/api/client/pets')
@role_required(['client'])
def api_client_pets():
    """API para obtener mascotas del cliente - CORREGIDA"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"🐾 Obteniendo mascotas para cliente: {user['id']}")

        # CORRECCIÓN: Usar la ruta correcta del Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/owner/{user['id']}"
        response = requests.get(medical_url, headers=headers, timeout=10)

        print(f"📡 Respuesta Medical Service: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                pets = data.get('pets', [])

                # Enriquecer datos con información adicional
                for pet in pets:
                    # Calcular edad si tiene fecha de nacimiento
                    if pet.get('birth_date'):
                        try:
                            from datetime import datetime, date
                            birth = datetime.strptime(pet['birth_date'], '%Y-%m-%d').date()
                            today = date.today()
                            age_years = (today - birth).days / 365.25
                            pet['calculated_age'] = age_years
                        except:
                            pet['calculated_age'] = None

                    # Asegurar que tenga estado de vacunación
                    if not pet.get('vaccination_status'):
                        pet['vaccination_status'] = 'pendiente'

                print(f"✅ {len(pets)} mascotas encontradas")

                return jsonify({
                    'success': True,
                    'pets': pets,
                    'total': len(pets)
                })
            else:
                return jsonify({
                    'success': True,
                    'pets': [],
                    'total': 0
                })
        else:
            print(f"❌ Error Medical Service: {response.status_code}")
            return jsonify({
                'success': False,
                'message': f'Error del Medical Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_client_pets: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/public/veterinarians')
def api_public_veterinarians():
    """API PÚBLICA para obtener veterinarios - VERSIÓN CORREGIDA"""
    try:
        print("👨‍⚕️ Obteniendo veterinarios públicos...")

        headers = {}

        # Intentar obtener token si existe (opcional para esta ruta pública)
        token = session.get('token')
        if token:
            headers['Authorization'] = f"Bearer {token}"

        veterinarians = []

        # MÉTODO 1: Obtener desde Auth Service
        try:
            print("📡 Llamando al Auth Service...")
            auth_url = f"{current_app.config.get('AUTH_SERVICE_URL', 'http://localhost:5001')}/auth/users"
            response = requests.get(auth_url, headers=headers, timeout=10)

            print(f"📡 Respuesta Auth Service: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('users'):
                    # Filtrar solo veterinarios activos
                    all_users = data.get('users', [])
                    vets = [user for user in all_users if user.get('role') == 'veterinarian' and user.get('is_active')]

                    print(f"✅ {len(vets)} veterinarios encontrados en Auth Service")
                    veterinarians = vets

        except Exception as auth_error:
            print(f"⚠️ Error Auth Service: {auth_error}")

        # MÉTODO 2: Si no hay veterinarios, obtener desde endpoint específico
        if not veterinarians:
            try:
                print("📡 Intentando endpoint específico de veterinarios...")
                auth_url = f"{current_app.config.get('AUTH_SERVICE_URL', 'http://localhost:5001')}/auth/users/veterinarians"
                response = requests.get(auth_url, headers=headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and data.get('veterinarians'):
                        veterinarians = data.get('veterinarians', [])
                        print(f"✅ {len(veterinarians)} veterinarios desde endpoint específico")

            except Exception as vet_error:
                print(f"⚠️ Error endpoint veterinarios: {vet_error}")

        # MÉTODO 3: Si aún no hay veterinarios, usar datos de ejemplo
        if not veterinarians:
            print("🔄 Usando veterinarios de ejemplo...")
            veterinarians = get_fallback_veterinarians()

        # Enriquecer con horarios desde Appointment Service
        try:
            print("📡 Obteniendo horarios desde Appointment Service...")
            appointment_url = f"{current_app.config.get('APPOINTMENT_SERVICE_URL', 'http://localhost:5002')}/appointments/schedules/veterinarians-v2"
            schedules_response = requests.get(appointment_url, headers=headers, timeout=10)

            vet_schedules = {}
            if schedules_response.status_code == 200:
                schedules_data = schedules_response.json()
                if schedules_data.get('success'):
                    vet_schedules = schedules_data.get('veterinarian_schedules', {})
                    print(f"✅ Horarios obtenidos para {len(vet_schedules)} veterinarios")

            # Enriquecer cada veterinario con sus horarios
            for vet in veterinarians:
                vet_id = vet['id']
                schedule_data = vet_schedules.get(vet_id, [])

                # Convertir horarios al formato esperado
                vet['schedule'] = convert_schedule_to_client_format(schedule_data)
                vet['has_schedule'] = len(schedule_data) > 0
                vet['schedule_text'] = generate_schedule_text(schedule_data)

        except Exception as schedule_error:
            print(f"⚠️ Error obteniendo horarios: {schedule_error}")
            # Asignar horarios por defecto
            for vet in veterinarians:
                vet['schedule'] = {}
                vet['has_schedule'] = False
                vet['schedule_text'] = 'Horario por confirmar'

        print(f"✅ Retornando {len(veterinarians)} veterinarios procesados")

        return jsonify({
            'success': True,
            'veterinarians': veterinarians,
            'total': len(veterinarians)
        })

    except Exception as e:
        print(f"❌ Error en api_public_veterinarians: {e}")
        import traceback
        traceback.print_exc()

        # Fallback con veterinarios de ejemplo
        fallback_vets = get_fallback_veterinarians()
        return jsonify({
            'success': True,
            'veterinarians': fallback_vets,
            'total': len(fallback_vets),
            'message': 'Usando datos de ejemplo - Servicios no disponibles'
        })


def convert_schedule_to_client_format(schedule_list):
    """Convertir horarios del backend al formato esperado por el cliente"""
    day_names = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
    result = {}

    for schedule_item in schedule_list:
        if schedule_item.get('is_available'):
            day_num = schedule_item.get('day_of_week')
            if 0 <= day_num <= 6:
                day_name = day_names[day_num]
                result[day_name] = {
                    'active': True,
                    'start': schedule_item.get('start_time', '08:00'),
                    'end': schedule_item.get('end_time', '17:00')
                }

    return result


def generate_schedule_text(schedule_list):
    """Generar texto descriptivo del horario"""
    if not schedule_list:
        return 'Horario por confirmar'

    day_names = {
        0: 'Dom', 1: 'Lun', 2: 'Mar', 3: 'Mié',
        4: 'Jue', 5: 'Vie', 6: 'Sáb'
    }

    active_days = []
    for schedule_item in schedule_list:
        if schedule_item.get('is_available'):
            day_num = schedule_item.get('day_of_week')
            if day_num in day_names:
                active_days.append(day_names[day_num])

    if not active_days:
        return 'Sin disponibilidad'

    return f"Disponible: {', '.join(active_days)}"


def enrich_veterinarians_with_schedules(veterinarians, headers):
    """Enriquecer veterinarios con sus horarios desde Appointment Service"""
    try:
        schedules_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/schedules/veterinarians-v2"
        schedules_response = requests.get(schedules_url, headers=headers, timeout=10)

        vet_schedules = {}
        if schedules_response.status_code == 200:
            schedules_data = schedules_response.json()
            if schedules_data.get('success'):
                vet_schedules = schedules_data.get('veterinarian_schedules', {})

        # Enriquecer cada veterinario
        enriched_veterinarians = []
        for vet in veterinarians:
            vet_id = vet['id']
            schedule_data = vet_schedules.get(vet_id, [])

            # Convertir horarios al formato esperado
            schedule_by_days = convert_schedule_to_days_format(schedule_data)

            enriched_vet = {
                **vet,
                'schedule': schedule_by_days,
                'has_schedule': len(schedule_data) > 0
            }
            enriched_veterinarians.append(enriched_vet)

        return enriched_veterinarians

    except Exception as e:
        print(f"⚠️ Error enriqueciendo horarios: {e}")
        return veterinarians


def create_veterinarians_from_schedules(vet_schedules):
    """Crear lista de veterinarios desde horarios disponibles"""
    veterinarians = []

    # Nombres predefinidos para veterinarios (hasta obtener acceso real)
    vet_names = [
        {"first_name": "Dr. Juan", "last_name": "Pérez", "specialty": "Medicina General"},
        {"first_name": "Dra. María", "last_name": "González", "specialty": "Cirugía Veterinaria"},
        {"first_name": "Dr. Carlos", "last_name": "Rodríguez", "specialty": "Medicina Interna"},
        {"first_name": "Dra. Ana", "last_name": "Martínez", "specialty": "Dermatología Veterinaria"},
        {"first_name": "Dr. Luis", "last_name": "García", "specialty": "Medicina de Emergencias"}
    ]

    for index, (vet_id, schedule_list) in enumerate(vet_schedules.items()):
        try:
            # Usar nombre predefinido o genérico
            vet_info = vet_names[index] if index < len(vet_names) else {
                "first_name": f"Dr. Veterinario",
                "last_name": f"{index + 1}",
                "specialty": "Medicina General"
            }

            # Convertir horarios
            schedule_by_days = convert_schedule_to_days_format(schedule_list)

            veterinarian = {
                'id': vet_id,
                'first_name': vet_info['first_name'],
                'last_name': vet_info['last_name'],
                'specialty': vet_info['specialty'],
                'email': f"vet{index + 1}@clinica.com",
                'is_active': True,
                'role': 'veterinarian',
                'schedule': schedule_by_days,
                'has_schedule': len(schedule_list) > 0
            }

            veterinarians.append(veterinarian)

        except Exception as e:
            print(f"⚠️ Error procesando veterinario {vet_id}: {e}")
            continue

    return veterinarians


# =============== 4. FUNCIÓN PARA CONVERTIR FORMATO DE HORARIOS ===============

def convert_schedule_to_days_format(schedule_list):
    """Convertir horarios de backend al formato esperado por frontend"""
    day_names = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
    schedule_by_days = {}

    for schedule_item in schedule_list:
        if schedule_item.get('is_available'):
            day_num = schedule_item.get('day_of_week')
            if 0 <= day_num <= 6:
                day_name = day_names[day_num]
                schedule_by_days[day_name] = {
                    'active': True,
                    'start': schedule_item.get('start_time', '08:00'),
                    'end': schedule_item.get('end_time', '18:00'),
                    'break_start': '12:00',
                    'break_end': '13:00'
                }

    return schedule_by_days


# =============== 5. VETERINARIOS DE FALLBACK ===============

def get_fallback_veterinarians():
    """Veterinarios de ejemplo para cuando no hay conexión con servicios"""
    return [
        {
            'id': 'vet_fallback_001',
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'email': 'juan.perez@clinica.com',
            'specialty': 'Medicina General',
            'is_active': True,
            'role': 'veterinarian',
            'schedule': {
                'monday': {'active': True, 'start': '08:00', 'end': '17:00'},
                'tuesday': {'active': True, 'start': '08:00', 'end': '17:00'},
                'wednesday': {'active': True, 'start': '08:00', 'end': '17:00'},
                'thursday': {'active': True, 'start': '08:00', 'end': '17:00'},
                'friday': {'active': True, 'start': '08:00', 'end': '16:00'},
                'saturday': {'active': True, 'start': '08:00', 'end': '12:00'}
            },
            'has_schedule': True,
            'schedule_text': 'Lun-Vie: 8:00-17:00, Sáb: 8:00-12:00'
        },
        {
            'id': 'vet_fallback_002',
            'first_name': 'María',
            'last_name': 'González',
            'email': 'maria.gonzalez@clinica.com',
            'specialty': 'Cirugía Veterinaria',
            'is_active': True,
            'role': 'veterinarian',
            'schedule': {
                'monday': {'active': True, 'start': '09:00', 'end': '17:00'},
                'wednesday': {'active': True, 'start': '09:00', 'end': '17:00'},
                'friday': {'active': True, 'start': '09:00', 'end': '17:00'},
                'saturday': {'active': True, 'start': '08:00', 'end': '14:00'}
            },
            'has_schedule': True,
            'schedule_text': 'Lun, Mié, Vie: 9:00-17:00, Sáb: 8:00-14:00'
        },
        {
            'id': 'vet_fallback_003',
            'first_name': 'Carlos',
            'last_name': 'Rodríguez',
            'email': 'carlos.rodriguez@clinica.com',
            'specialty': 'Medicina Interna',
            'is_active': True,
            'role': 'veterinarian',
            'schedule': {
                'tuesday': {'active': True, 'start': '08:00', 'end': '17:00'},
                'thursday': {'active': True, 'start': '08:00', 'end': '17:00'},
                'saturday': {'active': True, 'start': '08:00', 'end': '12:00'}
            },
            'has_schedule': True,
            'schedule_text': 'Mar, Jue: 8:00-17:00, Sáb: 8:00-12:00'
        }
    ]


@frontend_bp.route('/api/public/availability/<vet_id>/<date>')
def api_public_availability(vet_id, date):
    """API PÚBLICA para disponibilidad de veterinario - VERSIÓN CORREGIDA"""
    try:
        print(f"🔍 Buscando disponibilidad para veterinario {vet_id} en {date}")

        headers = {}
        token = session.get('token')
        if token:
            headers['Authorization'] = f"Bearer {token}"

        # MÉTODO 1: Obtener disponibilidad desde Appointment Service
        try:
            appointment_url = f"{current_app.config.get('APPOINTMENT_SERVICE_URL', 'http://localhost:5002')}/appointments/available-slots"
            params = {
                'veterinarian_id': vet_id,
                'date': date
            }

            response = requests.get(appointment_url, headers=headers, params=params, timeout=10)
            print(f"📡 Respuesta Appointment Service: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    available_slots = data.get('available_slots', [])

                    print(f"✅ {len(available_slots)} slots disponibles encontrados")

                    return jsonify({
                        'success': True,
                        'available_slots': available_slots,
                        'date': date,
                        'veterinarian_id': vet_id
                    })

        except Exception as appointment_error:
            print(f"⚠️ Error Appointment Service: {appointment_error}")

        # MÉTODO 2: Generar disponibilidad desde horarios del veterinario
        try:
            print("🔄 Generando disponibilidad desde horarios...")

            # Obtener horarios del veterinario
            schedules_url = f"{current_app.config.get('APPOINTMENT_SERVICE_URL', 'http://localhost:5002')}/appointments/schedules/veterinarians-v2-v2"
            schedules_response = requests.get(schedules_url, headers=headers, timeout=10)

            if schedules_response.status_code == 200:
                schedules_data = schedules_response.json()
                if schedules_data.get('success'):
                    vet_schedules = schedules_data.get('veterinarian_schedules', {})

                    if vet_id in vet_schedules:
                        schedule_list = vet_schedules[vet_id]

                        # Convertir fecha a día de la semana
                        from datetime import datetime
                        date_obj = datetime.strptime(date, '%Y-%m-%d')
                        day_of_week = (date_obj.weekday() + 1) % 7  # Convertir a formato backend

                        # Buscar horario para ese día
                        day_schedule = None
                        for schedule_item in schedule_list:
                            if schedule_item.get('day_of_week') == day_of_week and schedule_item.get('is_available'):
                                day_schedule = schedule_item
                                break

                        if day_schedule:
                            # Generar slots de tiempo
                            available_slots = generate_time_slots_for_date(
                                day_schedule.get('start_time', '08:00'),
                                day_schedule.get('end_time', '17:00'),
                                vet_id,
                                date,
                                headers
                            )

                            print(f"✅ {len(available_slots)} slots generados desde horario")

                            return jsonify({
                                'success': True,
                                'available_slots': available_slots,
                                'date': date,
                                'veterinarian_id': vet_id,
                                'source': 'generated'
                            })
                        else:
                            return jsonify({
                                'success': False,
                                'message': 'El veterinario no atiende este día',
                                'available_slots': [],
                                'date': date,
                                'veterinarian_id': vet_id
                            })

        except Exception as schedule_error:
            print(f"⚠️ Error generando desde horarios: {schedule_error}")

        # MÉTODO 3: Fallback con horarios básicos
        print("🔄 Usando horarios de fallback...")
        fallback_slots = generate_fallback_slots()

        return jsonify({
            'success': True,
            'available_slots': fallback_slots,
            'date': date,
            'veterinarian_id': vet_id,
            'source': 'fallback',
            'message': 'Horarios generados automáticamente'
        })

    except Exception as e:
        print(f"❌ Error en api_public_availability: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'message': f'Error obteniendo disponibilidad: {str(e)}',
            'available_slots': []
        }), 500


def generate_time_slots_for_date(start_time, end_time, vet_id, date, headers):
    """Generar slots de tiempo para una fecha específica"""
    try:
        from datetime import datetime, timedelta

        # Convertir horarios a datetime
        start_dt = datetime.strptime(start_time, '%H:%M')
        end_dt = datetime.strptime(end_time, '%H:%M')

        # Generar slots cada 30 minutos
        slots = []
        current = start_dt

        while current < end_dt:
            time_str = current.strftime('%H:%M')

            # Excluir hora de almuerzo (12:00-13:00)
            if not ('12:00' <= time_str < '13:00'):
                slots.append(time_str)

            current += timedelta(minutes=30)

        # Obtener citas existentes para filtrar slots ocupados
        try:
            appointments_url = f"{current_app.config.get('APPOINTMENT_SERVICE_URL', 'http://localhost:5002')}/appointments/veterinarian/{vet_id}/date/{date}"
            apt_response = requests.get(appointments_url, headers=headers, timeout=5)

            occupied_times = []
            if apt_response.status_code == 200:
                apt_data = apt_response.json()
                if apt_data.get('success'):
                    appointments = apt_data.get('appointments', [])
                    occupied_times = [apt.get('appointment_time') for apt in appointments if
                                      apt.get('appointment_time')]

            # Filtrar slots ocupados
            available_slots = [slot for slot in slots if slot not in occupied_times]

            print(f"⏰ {len(slots)} slots generados, {len(occupied_times)} ocupados, {len(available_slots)} disponibles")

            return available_slots

        except Exception as apt_error:
            print(f"⚠️ Error obteniendo citas existentes: {apt_error}")
            return slots  # Retornar todos los slots si no se pueden verificar las citas

    except Exception as e:
        print(f"❌ Error generando slots: {e}")
        return generate_fallback_slots()


def generate_fallback_slots():
    """Generar slots de tiempo básicos como fallback"""
    return [
        '08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
        '14:00', '14:30', '15:00', '15:30', '16:00', '16:30', '17:00'
    ]


def generate_time_slots_with_exclusions(start_time, end_time, occupied_slots):
    """Generar slots de tiempo excluyendo ocupados y hora de almuerzo"""
    try:
        from datetime import datetime, timedelta

        start_dt = datetime.strptime(start_time, '%H:%M')
        end_dt = datetime.strptime(end_time, '%H:%M')

        all_slots = []
        current = start_dt

        while current < end_dt:
            time_str = current.strftime('%H:%M')

            # Excluir hora de almuerzo (12:00-13:00) y slots ocupados
            if not ('12:00' <= time_str < '13:00') and time_str not in occupied_slots:
                all_slots.append(time_str)

            current += timedelta(minutes=30)

        return all_slots

    except Exception as e:
        print(f"❌ Error generando slots: {e}")
        return []

def generate_time_slots_public(start_time, end_time, vet_id, date, headers):
    """Generar slots disponibles considerando citas existentes"""
    try:
        from datetime import datetime, timedelta

        # Generar todos los slots posibles
        start_dt = datetime.strptime(start_time, '%H:%M')
        end_dt = datetime.strptime(end_time, '%H:%M')

        all_slots = []
        current = start_dt

        while current < end_dt:
            time_str = current.strftime('%H:%M')

            # Excluir hora de almuerzo (12:00-13:00)
            if not ('12:00' <= time_str < '13:00'):
                all_slots.append(time_str)

            current += timedelta(minutes=30)

        # Obtener citas existentes para filtrar slots ocupados
        try:
            appointments_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/veterinarian/{vet_id}/date/{date}"
            apt_response = requests.get(appointments_url, headers=headers, timeout=5)

            occupied_times = []
            if apt_response.status_code == 200:
                apt_data = apt_response.json()
                if apt_data.get('success'):
                    appointments = apt_data.get('appointments', [])
                    occupied_times = [apt.get('appointment_time') for apt in appointments]
        except:
            occupied_times = []

        # Filtrar slots disponibles
        available_slots = [slot for slot in all_slots if slot not in occupied_times]

        print(f"⏰ Slots: {len(all_slots)} total, {len(occupied_times)} ocupados, {len(available_slots)} disponibles")

        return available_slots

    except Exception as e:
        print(f"❌ Error generando slots: {e}")
        return []


@frontend_bp.route('/api/public/appointments', methods=['POST'])
def api_public_create_appointment():
    """API PÚBLICA para crear citas - VERSIÓN CORREGIDA"""
    try:
        data = request.get_json()

        # Verificar autenticación
        token = session.get('token')
        user = session.get('user')

        if not token or not user:
            return jsonify({
                'success': False,
                'message': 'Debe estar logueado para agendar citas'
            }), 401

        headers = {'Authorization': f"Bearer {token}"}

        # Preparar datos de la cita
        appointment_data = {
            'pet_id': data.get('pet_id'),
            'veterinarian_id': data.get('veterinarian_id'),
            'client_id': user['id'],
            'appointment_date': data.get('appointment_date'),
            'appointment_time': data.get('appointment_time'),
            'consultation_type': data.get('consultation_type', 'general'),
            'reason': data.get('reason', ''),
            'status': 'scheduled',
            'priority': 'normal'
        }

        print(f"📝 Creando cita: {appointment_data}")

        # Validar datos requeridos
        required_fields = ['pet_id', 'veterinarian_id', 'appointment_date', 'appointment_time']
        for field in required_fields:
            if not appointment_data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        # MÉTODO 1: Crear cita en Appointment Service
        try:
            appointment_url = f"{current_app.config.get('APPOINTMENT_SERVICE_URL', 'http://localhost:5002')}/appointments/create"
            response = requests.post(appointment_url, json=appointment_data, headers=headers, timeout=15)

            print(f"📡 Respuesta Appointment Service: {response.status_code}")

            if response.status_code in [200, 201]:
                result = response.json()
                if result.get('success'):
                    print(f"✅ Cita creada exitosamente: {result.get('appointment_id')}")

                    return jsonify({
                        'success': True,
                        'message': 'Cita agendada exitosamente',
                        'appointment': result.get('appointment', {}),
                        'appointment_id': result.get('appointment_id')
                    })
            else:
                # Manejar errores específicos del servicio
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', 'Error del servidor')
                except:
                    error_message = f'Error HTTP {response.status_code}'

                return jsonify({
                    'success': False,
                    'message': error_message
                }), response.status_code

        except requests.RequestException as req_error:
            print(f"❌ Error de conexión con Appointment Service: {req_error}")
            return jsonify({
                'success': False,
                'message': 'Error de conexión con el servicio de citas. Intente nuevamente.'
            }), 500

        # MÉTODO 2: Intentar endpoint alternativo
        try:
            alt_url = f"{current_app.config.get('APPOINTMENT_SERVICE_URL', 'http://localhost:5002')}/appointments/appointments"
            response = requests.post(alt_url, json=appointment_data, headers=headers, timeout=15)

            if response.status_code in [200, 201]:
                result = response.json()
                if result.get('success'):
                    return jsonify(result)

        except Exception as alt_error:
            print(f"⚠️ Error endpoint alternativo: {alt_error}")

        # Si llegamos aquí, no se pudo crear la cita
        return jsonify({
            'success': False,
            'message': 'No se pudo agendar la cita. El servicio no está disponible temporalmente.'
        }), 503

    except Exception as e:
        print(f"❌ Error en api_public_create_appointment: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


@frontend_bp.route('/api/client/appointments')
@role_required(['client'])
def api_client_appointments_get():
    """API para obtener citas del cliente - evita redirección 302"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"📅 Obteniendo citas para cliente: {user['id']}")

        # Obtener citas del cliente desde Appointment Service
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/client/{user['id']}"
        response = requests.get(appointment_url, headers=headers, timeout=10)

        print(f"📡 Appointments response: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('success'):
                    appointments = data.get('appointments', [])

                    # Enriquecer con datos de mascotas
                    try:
                        pets_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/owner/{user['id']}"
                        pets_response = requests.get(pets_url, headers=headers, timeout=5)

                        pets_map = {}
                        if pets_response.status_code == 200:
                            pets_data = pets_response.json()
                            if pets_data.get('success'):
                                pets_map = {pet['id']: pet for pet in pets_data.get('pets', [])}

                        # Enriquecer citas
                        for appointment in appointments:
                            pet_id = appointment.get('pet_id')
                            if pet_id and pet_id in pets_map:
                                pet = pets_map[pet_id]
                                appointment['pet_name'] = pet['name']
                                appointment['pet_species'] = pet['species']

                    except Exception as e:
                        print(f"⚠️ Error enriqueciendo citas: {e}")

                    print(f"✅ {len(appointments)} citas obtenidas para cliente")

                    return jsonify({
                        'success': True,
                        'appointments': appointments,
                        'total': len(appointments)
                    })
                else:
                    return jsonify({
                        'success': True,
                        'appointments': [],
                        'total': 0
                    })
            except ValueError as e:
                print(f"⚠️ Error obteniendo citas: {e}")
                return jsonify({
                    'success': True,
                    'appointments': [],
                    'total': 0,
                    'message': 'Error procesando respuesta del servidor'
                })
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Appointment Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_client_appointments_get: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
# =============== 11. ENDPOINT PARA VERIFICAR SESIÓN ===============

@frontend_bp.route('/api/client/session/check')
def api_check_client_session():
    """Verificar si el cliente tiene sesión válida"""
    try:
        user = session.get('user')
        token = session.get('token')

        if not user or not token:
            return jsonify({
                'success': False,
                'authenticated': False,
                'message': 'No hay sesión activa'
            }), 401

        if user.get('role') != 'client':
            return jsonify({
                'success': False,
                'authenticated': False,
                'message': 'Sesión no es de cliente'
            }), 403

        return jsonify({
            'success': True,
            'authenticated': True,
            'user': {
                'id': user['id'],
                'name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                'email': user.get('email'),
                'role': user['role']
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'authenticated': False,
            'message': str(e)
        }), 500

# =============== 12. MANEJO DE ERRORES DE CONEXIÓN ===============

def handle_service_error(service_name, response_code, fallback_data=None):
    """Manejar errores de conexión con microservicios"""
    if response_code == 403:
        return {
            'success': False,
            'message': f'Sin permisos para acceder a {service_name}',
            'error_code': 'FORBIDDEN'
        }
    elif response_code == 404:
        return {
            'success': False,
            'message': f'Recurso no encontrado en {service_name}',
            'error_code': 'NOT_FOUND'
        }
    elif response_code >= 500:
        return {
            'success': False,
            'message': f'{service_name} no disponible temporalmente',
            'error_code': 'SERVICE_UNAVAILABLE'
        }
    else:
        return {
            'success': False,
            'message': f'Error en {service_name}: {response_code}',
            'error_code': 'UNKNOWN_ERROR'
        }

def process_appointments_response(appointments, headers):
    """Procesar y enriquecer respuesta de citas"""
    try:
        enriched_appointments = []

        for appointment in appointments:
            try:
                # Obtener datos de la mascota
                if appointment.get('pet_id'):
                    try:
                        pet_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{appointment['pet_id']}"
                        pet_response = requests.get(pet_url, headers=headers, timeout=3)

                        if pet_response.status_code == 200:
                            pet_data = pet_response.json()
                            if pet_data.get('success'):
                                pet = pet_data['pet']
                                appointment['pet_name'] = pet['name']
                                appointment['pet_species'] = pet['species']
                    except:
                        appointment['pet_name'] = 'Mascota'
                        appointment['pet_species'] = 'unknown'

                # Obtener datos del veterinario usando endpoint interno
                if appointment.get('veterinarian_id'):
                    try:
                        # Usar endpoint interno que ya funciona
                        users_response = requests.get(
                            'http://localhost:3000/api/admin/users',
                            headers=headers,
                            timeout=3
                        )

                        if users_response.status_code == 200:
                            users_data = users_response.json()
                            if users_data.get('success'):
                                vet = next((u for u in users_data['users']
                                            if u['id'] == appointment['veterinarian_id']), None)
                                if vet:
                                    appointment['veterinarian_name'] = f"Dr. {vet['first_name']} {vet['last_name']}"
                    except:
                        appointment['veterinarian_name'] = 'Dr. Veterinario'

                enriched_appointments.append(appointment)

            except Exception as e:
                print(f"⚠️ Error enriqueciendo cita {appointment.get('id')}: {e}")
                enriched_appointments.append(appointment)

        print(f"✅ {len(enriched_appointments)} citas procesadas y enriquecidas")

        return jsonify({
            'success': True,
            'appointments': enriched_appointments,
            'total': len(enriched_appointments)
        })

    except Exception as e:
        print(f"❌ Error procesando citas: {e}")
        return jsonify({
            'success': True,
            'appointments': appointments,
            'total': len(appointments)
        })


def generate_time_slots_from_schedule(day_schedule):
    """Generar slots de tiempo desde horario del día - CORRECCIÓN FINAL"""
    from datetime import datetime, timedelta

    try:
        start_time = day_schedule.get('start', '08:00')
        end_time = day_schedule.get('end', '17:00')
        break_start = day_schedule.get('break_start', '12:00')
        break_end = day_schedule.get('break_end', '13:00')

        slots = []

        # Convertir a datetime
        start_dt = datetime.strptime(start_time, '%H:%M')
        end_dt = datetime.strptime(end_time, '%H:%M')
        break_start_dt = datetime.strptime(break_start, '%H:%M')
        break_end_dt = datetime.strptime(break_end, '%H:%M')

        current = start_dt
        slot_duration = timedelta(minutes=30)

        while current < end_dt:
            # Saltar horario de almuerzo
            if not (break_start_dt <= current < break_end_dt):
                slots.append(current.strftime('%H:%M'))

            current += slot_duration

        print(f"✅ Generados {len(slots)} slots desde {start_time} hasta {end_time}")
        return slots

    except Exception as e:
        print(f"❌ Error generando slots: {e}")
        # Fallback con horarios básicos
        return ['08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
                '14:00', '14:30', '15:00', '15:30', '16:00', '16:30']


def generate_availability_fallback(vet_id, date, headers):
    """Generar disponibilidad desde horarios del veterinario como fallback"""
    try:
        print(f"🔄 Generando disponibilidad desde horarios del veterinario...")

        # Obtener horarios del veterinario
        schedules_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/schedules"
        schedules_response = requests.get(schedules_url, headers=headers, timeout=5)

        if schedules_response.status_code == 200:
            schedules_data = schedules_response.json()
            if schedules_data.get('success'):
                schedules = schedules_data.get('schedules', [])
                vet_schedule = next((s for s in schedules if s.get('user_id') == vet_id), None)

                if vet_schedule:
                    weekly_schedule = vet_schedule.get('weekly_schedule', {})

                    # Convertir fecha a día de la semana
                    from datetime import datetime
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                    day_name = day_names[date_obj.weekday()]

                    day_schedule = weekly_schedule.get(day_name)

                    if day_schedule and day_schedule.get('active'):
                        # Generar slots de tiempo
                        available_slots = generate_time_slots_from_schedule(day_schedule)

                        print(f"✅ Fallback exitoso: {len(available_slots)} slots generados")

                        return jsonify({
                            'success': True,
                            'available_slots': available_slots,
                            'date': date,
                            'veterinarian_id': vet_id,
                            'source': 'fallback'
                        })

        return jsonify({
            'success': False,
            'message': 'El veterinario no atiende este día'
        })

    except Exception as e:
        print(f"❌ Error en fallback: {e}")
        raise


@frontend_bp.route('/api/client/notifications/count')
@role_required(['client'])
def api_client_notifications_count():
    """API para contar notificaciones del cliente - CORRECCIÓN FINAL"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"🔔 Obteniendo conteo de notificaciones para cliente: {user['id']}")

        data = {
            'unread_notifications': 0,
            'pending_appointments': 0
        }

        # Intentar obtener notificaciones no leídas
        try:
            # CORRECCIÓN: Usar endpoint correcto
            notif_url = f"{current_app.config['NOTIFICATION_SERVICE_URL']}/notifications/user/{user['id']}/unread/count"
            notif_response = requests.get(notif_url, headers=headers, timeout=5)

            print(f"📡 Notificaciones response: {notif_response.status_code}")

            if notif_response.status_code == 200:
                notif_data = notif_response.json()
                if notif_data.get('success'):
                    data['unread_notifications'] = notif_data.get('count', 0)
            elif notif_response.status_code == 404:
                # Endpoint no existe, usar valor por defecto
                data['unread_notifications'] = 0
        except Exception as e:
            print(f"⚠️ Error obteniendo notificaciones: {e}")
            data['unread_notifications'] = 0

        # Intentar obtener citas pendientes
        try:
            # Usar nuestro propio endpoint que ya funciona
            appointments_response = requests.get(
                'http://localhost:3000/api/client/appointments',
                headers=headers,
                timeout=5
            )

            print(f"📡 Appointments response: {appointments_response.status_code}")

            if appointments_response.status_code == 200:
                apt_data = appointments_response.json()
                if apt_data.get('success'):
                    appointments = apt_data.get('appointments', [])
                    pending_count = len([a for a in appointments if a.get('status') == 'scheduled'])
                    data['pending_appointments'] = pending_count
        except Exception as e:
            print(f"⚠️ Error obteniendo citas: {e}")
            data['pending_appointments'] = 0

        print(f"✅ Conteo de notificaciones: {data}")

        return jsonify({
            'success': True,
            'data': data
        })

    except Exception as e:
        print(f"❌ Error en api_client_notifications_count: {e}")
        # Retornar datos seguros en caso de error
        return jsonify({
            'success': True,
            'data': {
                'unread_notifications': 0,
                'pending_appointments': 0
            }
        })

# =============== PANEL DE FACTURACIÓN ===============

@frontend_bp.route('/admin/billing')
@role_required(['admin', 'receptionist'])
def admin_billing():
    """Panel principal de facturación"""
    try:
        return render_template('admin/sections/billing-management.html')
    except Exception as e:
        print(f"❌ Error en admin_billing: {e}")
        flash('Error al cargar el panel de facturación', 'error')
        return redirect(url_for('frontend.admin_dashboard'))


# =============== API ENDPOINTS PARA FACTURACIÓN ===============

@frontend_bp.route('/api/admin/billing/owners')
@role_required(['admin', 'receptionist'])
def api_get_owners():
    """API endpoint para obtener todos los propietarios"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        response = requests.get(
            f"{current_app.config['AUTH_SERVICE_URL']}/auth/users/role/client",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'success': True,
                'owners': data.get('users', [])
            })
        else:
            return jsonify({'success': False, 'message': 'Error obteniendo propietarios'}), 400

    except Exception as e:
        print(f"❌ Error en api_get_owners: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@frontend_bp.route('/api/admin/billing/pets/<int:owner_id>')
@role_required(['admin', 'receptionist'])
def api_get_owner_pets(owner_id):
    """API endpoint para obtener mascotas de un propietario"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        response = requests.get(
            f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/owner/{owner_id}",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'success': True,
                'pets': data.get('pets', [])
            })
        else:
            return jsonify({'success': False, 'message': 'Error obteniendo mascotas'}), 400

    except Exception as e:
        print(f"❌ Error en api_get_owner_pets: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@frontend_bp.route('/api/admin/billing/medications')
@role_required(['admin', 'receptionist'])
def api_get_billing_medications():
    """API endpoint para obtener todos los medicamentos disponibles"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        response = requests.get(
            f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/medications",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'success': True,
                'medications': data.get('medications', [])
            })
        else:
            return jsonify({'success': False, 'message': 'Error obteniendo medicamentos'}), 400

    except Exception as e:
        print(f"❌ Error en api_get_medications: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@frontend_bp.route('/api/admin/billing/medical-history/<int:pet_id>')
@role_required(['admin', 'receptionist'])
def api_get_pet_medical_history(pet_id):
    """API endpoint para obtener historia médica de una mascota"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        response = requests.get(
            f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/records/pet/{pet_id}",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'success': True,
                'medical_records': data.get('medical_records', [])
            })
        else:
            return jsonify({'success': False, 'message': 'Error obteniendo historia médica'}), 400

    except Exception as e:
        print(f"❌ Error en api_get_pet_medical_history: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@frontend_bp.route('/api/admin/billing/create-invoice', methods=['POST'])
@role_required(['admin', 'receptionist'])
def api_create_invoice():
    """API endpoint para crear una nueva factura"""
    try:
        data = request.get_json()
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Aquí enviarías los datos al microservicio correspondiente
        # Por ejemplo, a un servicio de facturación o al inventario para actualizar stock

        # Datos de la factura
        invoice_data = {
            'owner_id': data.get('owner_id'),
            'pet_id': data.get('pet_id'),
            'medications': data.get('medications', []),
            'total': data.get('total'),
            'created_by': session.get('user_id'),
            'created_at': datetime.now().isoformat()
        }

        # Simular creación exitosa
        return jsonify({
            'success': True,
            'message': 'Factura creada exitosamente',
            'invoice_id': f"INV-{int(time.time())}"
        })

    except Exception as e:
        print(f"❌ Error en api_create_invoice: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@frontend_bp.route('/api/admin/billing/statistics')
@role_required(['admin', 'receptionist'])
def api_get_billing_statistics():
    """API endpoint para obtener estadísticas de facturación"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Aquí harías las consultas reales a tus microservicios
        # para obtener estadísticas reales

        stats = {
            'total_revenue': 15750.50,
            'total_invoices': 125,
            'avg_invoice': 126.00,
            'total_medications': 347,
            'monthly_revenue': [
                {'month': 'Enero', 'revenue': 2500},
                {'month': 'Febrero', 'revenue': 2800},
                {'month': 'Marzo', 'revenue': 3200},
                {'month': 'Abril', 'revenue': 2900},
                {'month': 'Mayo', 'revenue': 3300},
                {'month': 'Junio', 'revenue': 1000}  # Mes actual parcial
            ]
        }

        return jsonify({
            'success': True,
            'statistics': stats
        })

    except Exception as e:
        print(f"❌ Error en api_get_billing_statistics: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@frontend_bp.route('/api/admin/billing/history')
@role_required(['admin', 'receptionist'])
def api_get_billing_history():
    """API endpoint para obtener historial de facturación"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Parámetros de búsqueda y paginación
        search = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        # Aquí harías la consulta real a tu microservicio
        # Por ahora simularemos datos

        history = [
            {
                'id': 'INV-001',
                'date': '2024-06-10',
                'owner_name': 'Juan Pérez',
                'pet_name': 'Max',
                'total': 125.50,
                'status': 'paid'
            },
            {
                'id': 'INV-002',
                'date': '2024-06-11',
                'owner_name': 'María García',
                'pet_name': 'Luna',
                'total': 87.25,
                'status': 'paid'
            }
            # ... más datos
        ]

        return jsonify({
            'success': True,
            'invoices': history,
            'total': len(history),
            'page': page,
            'per_page': per_page
        })

    except Exception as e:
        print(f"❌ Error en api_get_billing_history: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# =============== FUNCIÓN DE CONEXIÓN ===============
def get_db():
    """Conexión a PostgreSQL - VERSIÓN MEJORADA"""
    try:
        # Obtener configuración de la base de datos
        host = os.environ.get('POSTGRES_HOST', 'localhost')
        port = os.environ.get('POSTGRES_PORT', '5432')
        database = os.environ.get('POSTGRES_DB', 'veterinary-system')
        user = os.environ.get('POSTGRES_USER', 'postgres')
        password = os.environ.get('POSTGRES_PASSWORD', 'bocato0731')

        print(f"🔌 Intentando conectar a PostgreSQL: {user}@{host}:{port}/{database}")

        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=10
        )

        print("✅ Conexión a PostgreSQL exitosa")
        return conn

    except psycopg2.OperationalError as e:
        print(f"❌ Error operacional PostgreSQL: {e}")
        return None
    except Exception as e:
        print(f"❌ Error general conectando BD: {e}")
        return None


# =============== CREAR TABLAS SI NO EXISTEN ===============
def ensure_billing_tables():
    """Las tablas ya existen - solo verificar conexión"""
    try:
        conn = get_db()
        if not conn:
            return False

        cur = conn.cursor()

        # Solo verificar que las tablas existen (no crearlas)
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('invoices', 'invoice_items')
        """)

        tables = [row[0] for row in cur.fetchall()]

        cur.close()
        conn.close()

        if 'invoices' in tables and 'invoice_items' in tables:
            print("✅ Tablas de facturación existen en la base de datos")
            return True
        else:
            print(f"❌ Faltan tablas. Encontradas: {tables}")
            return False

    except Exception as e:
        print(f"❌ Error verificando tablas: {e}")
        return False


# =============== OBTENER FACTURAS ===============
@frontend_bp.route('/api/admin/billing/invoices')
@role_required(['admin'])
def api_billing_get_invoices():
    """Obtener facturas desde la base de datos - VERSIÓN CORREGIDA"""
    try:
        print("📊 Obteniendo facturas desde la base de datos...")

        conn = get_db()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Error conectando a la base de datos'
            }), 500

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Consulta usando SOLO las columnas que existen
        query = """
            SELECT i.id, i.client_id, i.pet_id, i.appointment_id,
                   i.total_amount, i.subtotal, i.tax_amount, i.medications_cost,
                   i.payment_method, i.status, i.observations, 
                   i.invoice_date, i.created_at, i.payment_date,
                   COALESCE(u.first_name || ' ' || u.last_name, 'Cliente desconocido') as client_name,
                   COALESCE(u.email, '') as client_email,
                   COALESCE(p.name, 'Mascota desconocida') as pet_name,
                   COALESCE(p.species, '') as pet_species
            FROM invoices i
            LEFT JOIN users u ON i.client_id = u.id
            LEFT JOIN pets p ON i.pet_id = p.id
            ORDER BY i.invoice_date DESC
            LIMIT 100
        """

        cur.execute(query)
        rows = cur.fetchall()

        invoices = []
        for row in rows:
            invoice = dict(row)
            # Convertir Decimal a float para JSON
            for key, value in invoice.items():
                if isinstance(value, Decimal):
                    invoice[key] = float(value)
                elif isinstance(value, datetime):
                    invoice[key] = value.isoformat()
            invoices.append(invoice)

        cur.close()
        conn.close()

        print(f"✅ {len(invoices)} facturas obtenidas desde la base de datos")

        return jsonify({
            'success': True,
            'invoices': invoices,
            'total': len(invoices)
        })

    except Exception as e:
        print(f"❌ Error obteniendo facturas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


# =============== CREAR FACTURA ===============
@frontend_bp.route('/api/admin/billing/invoices', methods=['POST'])
@role_required(['admin'])
def api_billing_create_invoice():
    """Crear factura en la base de datos - VERSIÓN CORREGIDA PARA TU ESQUEMA"""
    try:
        data = request.get_json()
        print(f"📝 Creando factura con datos: {data}")

        # Validar datos requeridos
        if not data.get('client_id'):
            return jsonify({
                'success': False,
                'message': 'client_id es requerido'
            }), 400

        if not data.get('medications') or len(data.get('medications', [])) == 0:
            return jsonify({
                'success': False,
                'message': 'Debe incluir al menos un medicamento'
            }), 400

        conn = get_db()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Error conectando a la base de datos'
            }), 500

        cur = conn.cursor()

        # Calcular totales
        medications = data.get('medications', [])
        subtotal = sum(float(med.get('unit_price', 0)) * int(med.get('quantity', 1)) for med in medications)
        tax_rate = 0.19  # 19% IVA
        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount

        print(f"💰 Subtotal: {subtotal}, Impuesto: {tax_amount}, Total: {total_amount}")

        # Crear factura usando SOLO las columnas que existen en tu base de datos
        invoice_id = str(uuid.uuid4())
        invoice_date = datetime.now()

        # COLUMNAS CORRECTAS según tu esquema:
        # id, appointment_id, client_id, total_amount, consultation_fee, medications_cost,
        # exams_cost, payment_status, payment_date, created_at, pet_id, payment_method,
        # subtotal, tax_amount, status, observations, invoice_date

        cur.execute("""
            INSERT INTO invoices (
                id, client_id, pet_id, appointment_id, total_amount, 
                subtotal, tax_amount, medications_cost, payment_method, 
                status, observations, invoice_date, created_at, payment_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            invoice_id,
            data['client_id'],
            data.get('pet_id'),
            data.get('appointment_id'),
            total_amount,
            subtotal,
            tax_amount,
            subtotal,  # medications_cost = subtotal
            data.get('payment_method', 'cash'),
            data.get('status', 'paid'),
            data.get('observations', ''),
            invoice_date,
            invoice_date,
            invoice_date  # payment_date = now for paid invoices
        ))

        # Crear items de factura usando las columnas correctas
        for med in medications:
            item_id = str(uuid.uuid4())
            quantity = int(med.get('quantity', 1))
            unit_price = float(med.get('unit_price', 0))
            total_price = quantity * unit_price

            # COLUMNAS CORRECTAS para invoice_items:
            # id, invoice_id, medication_id, item_name, item_description,
            # presentation, concentration, quantity, unit_price, total_price, created_at

            cur.execute("""
                INSERT INTO invoice_items (
                    id, invoice_id, medication_id, item_name, item_description,
                    presentation, concentration, quantity, unit_price, total_price, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                item_id,
                invoice_id,
                med.get('id'),
                med.get('name', 'Medicamento'),
                med.get('description', ''),
                med.get('presentation', ''),
                med.get('concentration', ''),
                quantity,
                unit_price,
                total_price,
                invoice_date
            ))

        conn.commit()
        cur.close()
        conn.close()

        print(f"✅ Factura creada exitosamente: {invoice_id}")

        # Retornar datos de la factura creada
        invoice_data = {
            'id': invoice_id,
            'client_id': data['client_id'],
            'pet_id': data.get('pet_id'),
            'total_amount': total_amount,
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'payment_method': data.get('payment_method', 'cash'),
            'status': data.get('status', 'paid'),
            'observations': data.get('observations', ''),
            'invoice_date': invoice_date.isoformat(),
            'medications': medications
        }

        return jsonify({
            'success': True,
            'message': 'Factura creada exitosamente',
            'invoice': invoice_data
        })

    except Exception as e:
        print(f"❌ Error creando factura: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


# =============== GENERAR PDF ===============
@frontend_bp.route('/api/admin/billing/invoices/<invoice_id>/pdf')
@role_required(['admin'])
def api_billing_generate_pdf(invoice_id):
    """Generar PDF de factura"""
    try:
        print(f"📄 Generando PDF para factura: {invoice_id}")

        conn = get_db()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Error conectando a la base de datos'
            }), 500

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Obtener datos de la factura
        cur.execute("""
            SELECT i.*, 
                   COALESCE(u.first_name || ' ' || u.last_name, 'Cliente desconocido') as client_name,
                   COALESCE(u.email, '') as client_email,
                   COALESCE(u.phone, '') as client_phone,
                   COALESCE(p.name, 'Mascota desconocida') as pet_name,
                   COALESCE(p.species, '') as pet_species
            FROM invoices i
            LEFT JOIN users u ON i.client_id::UUID = u.id
            LEFT JOIN pets p ON i.pet_id::UUID = p.id
            WHERE i.id = %s
        """, (invoice_id,))

        invoice = cur.fetchone()
        if not invoice:
            return jsonify({
                'success': False,
                'message': 'Factura no encontrada'
            }), 404

        # Obtener items de la factura
        cur.execute("""
            SELECT * FROM invoice_items 
            WHERE invoice_id = %s 
            ORDER BY created_at
        """, (invoice_id,))
        items = cur.fetchall()

        cur.close()
        conn.close()

        # Generar contenido HTML para PDF
        html_content = generate_invoice_pdf_content(dict(invoice), [dict(item) for item in items])

        # Retornar como HTML para que el navegador lo convierta a PDF
        return Response(
            html_content,
            mimetype='text/html',
            headers={
                'Content-Disposition': f'inline; filename=factura_{invoice_id}.html'
            }
        )

    except Exception as e:
        print(f"❌ Error generando PDF: {e}")
        return jsonify({
            'success': False,
            'message': f'Error generando PDF: {str(e)}'
        }), 500


def generate_invoice_pdf_content(invoice, items):
    """Generar contenido HTML para PDF de factura"""

    # Calcular totales
    subtotal = sum(float(item.get('total_price', 0)) for item in items)
    tax_amount = float(invoice.get('tax_amount', 0))
    total = float(invoice.get('total_amount', 0))

    items_html = ""
    for item in items:
        items_html += f"""
        <tr>
            <td>{item.get('item_name', 'Medicamento')}</td>
            <td style="text-align: center;">{item.get('quantity', 1)}</td>
            <td style="text-align: right;">${float(item.get('unit_price', 0)):,.2f}</td>
            <td style="text-align: right;"><strong>${float(item.get('total_price', 0)):,.2f}</strong></td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Factura #{invoice.get('id', 'N/A')}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                color: #2D6A4F;
                line-height: 1.6;
                background: white;
            }}
            .invoice-container {{
                max-width: 800px;
                margin: 0 auto;
                padding: 40px;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                border-bottom: 3px solid #52B788;
                padding-bottom: 30px;
                margin-bottom: 40px;
            }}
            .logo {{
                font-size: 48px;
                margin-bottom: 10px;
            }}
            .clinic-name {{
                color: #2D6A4F;
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .clinic-info {{
                color: #52B788;
                font-size: 14px;
                margin-bottom: 20px;
            }}
            .invoice-title {{
                font-size: 24px;
                font-weight: bold;
                color: #38A3A5;
                margin-bottom: 10px;
            }}
            .invoice-number {{
                font-size: 18px;
                color: #2D6A4F;
            }}
            .invoice-details {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 40px;
                gap: 40px;
            }}
            .client-info, .invoice-info {{
                flex: 1;
            }}
            .section-title {{
                font-size: 16px;
                font-weight: bold;
                color: #52B788;
                margin-bottom: 15px;
                border-bottom: 1px solid #B7E4C7;
                padding-bottom: 5px;
            }}
            .info-row {{
                margin-bottom: 8px;
                display: flex;
            }}
            .info-label {{
                font-weight: bold;
                color: #2D6A4F;
                min-width: 100px;
            }}
            .info-value {{
                color: #2D6A4F;
            }}
            .items-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 30px 0;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            .items-table th {{
                background: #52B788;
                color: white;
                padding: 15px 10px;
                text-align: left;
                font-weight: bold;
                border-bottom: 2px solid #2D6A4F;
            }}
            .items-table td {{
                padding: 12px 10px;
                border-bottom: 1px solid #B7E4C7;
                color: #2D6A4F;
            }}
            .items-table tr:nth-child(even) {{
                background: #F8FDF9;
            }}
            .items-table tr:hover {{
                background: #D8F3DC;
            }}
            .totals-section {{
                margin-top: 40px;
                border-top: 2px solid #52B788;
                padding-top: 20px;
            }}
            .totals-table {{
                width: 300px;
                margin-left: auto;
                border-collapse: collapse;
            }}
            .totals-table td {{
                padding: 8px 15px;
                color: #2D6A4F;
            }}
            .totals-table .label {{
                font-weight: bold;
                text-align: right;
                border-right: 1px solid #B7E4C7;
            }}
            .totals-table .amount {{
                text-align: right;
                font-weight: bold;
            }}
            .total-row {{
                background: #52B788;
                color: white !important;
                font-size: 18px;
            }}
            .total-row td {{
                color: white !important;
                padding: 12px 15px;
            }}
            .observations {{
                margin-top: 30px;
                padding: 20px;
                background: #D8F3DC;
                border-radius: 10px;
                border-left: 5px solid #52B788;
            }}
            .observations-title {{
                font-weight: bold;
                color: #2D6A4F;
                margin-bottom: 10px;
            }}
            .footer {{
                margin-top: 50px;
                text-align: center;
                color: #52B788;
                font-size: 12px;
                border-top: 1px solid #B7E4C7;
                padding-top: 20px;
            }}
            @media print {{
                body {{ margin: 0; padding: 0; }}
                .invoice-container {{ box-shadow: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="invoice-container">
            <!-- HEADER -->
            <div class="header">
                <div class="logo">🏥</div>
                <div class="clinic-name">CLÍNICA VETERINARIA</div>
                <div class="clinic-info">
                    NIT: 123.456.789-0 | Tel: (601) 234-5678<br>
                    Dirección: Calle 123 #45-67, Bogotá, Colombia<br>
                    Email: info@clinicaveterinaria.com
                </div>
                <div class="invoice-title">FACTURA DE VENTA</div>
                <div class="invoice-number">No. {invoice.get('id', 'N/A')}</div>
            </div>

            <!-- DETALLES DE FACTURA -->
            <div class="invoice-details">
                <div class="client-info">
                    <div class="section-title">👤 INFORMACIÓN DEL CLIENTE</div>
                    <div class="info-row">
                        <span class="info-label">Nombre:</span>
                        <span class="info-value">{invoice.get('client_name', 'Cliente desconocido')}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Email:</span>
                        <span class="info-value">{invoice.get('client_email', 'N/A')}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Teléfono:</span>
                        <span class="info-value">{invoice.get('client_phone', 'N/A')}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Mascota:</span>
                        <span class="info-value">{invoice.get('pet_name', 'N/A')} ({invoice.get('pet_species', '')})</span>
                    </div>
                </div>

                <div class="invoice-info">
                    <div class="section-title">📋 INFORMACIÓN DE FACTURA</div>
                    <div class="info-row">
                        <span class="info-label">Fecha:</span>
                        <span class="info-value">{invoice.get('invoice_date', '')[:10] if invoice.get('invoice_date') else 'N/A'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Hora:</span>
                        <span class="info-value">{invoice.get('invoice_date', '')[-8:-3] if invoice.get('invoice_date') else 'N/A'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Método Pago:</span>
                        <span class="info-value">{invoice.get('payment_method', 'N/A').title()}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Estado:</span>
                        <span class="info-value">{invoice.get('status', 'N/A').title()}</span>
                    </div>
                </div>
            </div>

            <!-- TABLA DE MEDICAMENTOS -->
            <table class="items-table">
                <thead>
                    <tr>
                        <th>💊 Medicamento/Servicio</th>
                        <th style="text-align: center;">Cantidad</th>
                        <th style="text-align: right;">Precio Unitario</th>
                        <th style="text-align: right;">Total</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html if items_html else '<tr><td colspan="4" style="text-align: center;">No hay medicamentos registrados</td></tr>'}
                </tbody>
            </table>

            <!-- TOTALES -->
            <div class="totals-section">
                <table class="totals-table">
                    <tr>
                        <td class="label">Subtotal:</td>
                        <td class="amount">${subtotal:,.2f}</td>
                    </tr>
                    <tr>
                        <td class="label">IVA (19%):</td>
                        <td class="amount">${tax_amount:,.2f}</td>
                    </tr>
                    <tr class="total-row">
                        <td class="label">TOTAL:</td>
                        <td class="amount">${total:,.2f}</td>
                    </tr>
                </table>
            </div>

            <!-- OBSERVACIONES -->
            {f'''
            <div class="observations">
                <div class="observations-title">📝 Observaciones:</div>
                <div>{invoice.get("observations", "")}</div>
            </div>
            ''' if invoice.get('observations') else ''}

            <!-- PIE DE PÁGINA -->
            <div class="footer">
                <p><strong>¡Gracias por confiar en nosotros para el cuidado de tu mascota!</strong></p>
                <p>Esta factura fue generada el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                <p>Para consultas sobre esta factura, contáctanos al (601) 234-5678</p>
            </div>
        </div>
    </body>
    </html>
    """

# =============== EXPORTAR CSV ===============
@frontend_bp.route('/api/admin/billing/export/excel')
@role_required(['admin'])
def api_billing_export_csv():
    """Exportar facturas a CSV"""
    try:
        print("📊 Exportando facturas a CSV...")

        conn = get_db()
        if not conn:
            return jsonify({
                'success': False,
                'message': 'Error conectando a la base de datos'
            }), 500

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("""
            SELECT i.id, i.invoice_date, 
                   COALESCE(u.first_name || ' ' || u.last_name, 'Cliente desconocido') as cliente,
                   COALESCE(p.name, 'Mascota desconocida') as mascota, 
                   i.total_amount, i.payment_method, i.status
            FROM invoices i
            LEFT JOIN users u ON i.client_id::UUID = u.id
            LEFT JOIN pets p ON i.pet_id::UUID = p.id
            ORDER BY i.invoice_date DESC
        """)

        output = io.StringIO()
        import csv
        writer = csv.writer(output)

        # Escribir encabezados
        writer.writerow(['ID', 'Fecha', 'Cliente', 'Mascota', 'Total', 'Método de Pago', 'Estado'])

        # Escribir datos
        for row in cur.fetchall():
            writer.writerow([
                row['id'],
                row['invoice_date'].strftime('%Y-%m-%d %H:%M:%S') if row['invoice_date'] else '',
                row['cliente'],
                row['mascota'],
                float(row['total_amount']) if row['total_amount'] else 0,
                row['payment_method'],
                row['status']
            ])

        cur.close()
        conn.close()

        output.seek(0)

        print("✅ CSV generado exitosamente")

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=facturas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )

    except Exception as e:
        print(f"❌ Error exportando CSV: {e}")
        return jsonify({
             'success': False,
            'message': f'Error exportando CSV: {str(e)}'
        }), 500


# =============== FUNCIÓN PARA INICIALIZAR SISTEMA DE FACTURACIÓN ===============
def initialize_billing_system():
    """Inicializar sistema de facturación al arrancar la aplicación"""
    print("🚀 Inicializando sistema de facturación...")

    # Verificar conexión a base de datos
    conn = get_db()
    if conn:
        print("✅ Conexión a base de datos exitosa")
        conn.close()

        # Crear tablas si no existen
        if ensure_billing_tables():
            print("✅ Tablas de facturación verificadas")
        else:
            print("❌ Error creando tablas de facturación")
    else:
        print("❌ No se pudo conectar a la base de datos")

# =============== HISTORIA CLINICA CLIENTE ===============
@frontend_bp.route('/client/medical-history')
@role_required(['client'])
def client_medical_history():
    """Página de historial médico"""
    user = session.get('user', {})
    template_data = {
        'user': user,
        'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Cliente',
        'user_initial': user.get('first_name', 'C')[0].upper() if user.get('first_name') else 'C'
    }
    return render_template('client/sections/medical-history.html', **template_data)

@frontend_bp.route('/api/client/pets/<pet_id>/medical-history')
@role_required(['client'])
def api_client_pet_medical_history(pet_id):
    """API para obtener historia clínica de una mascota del cliente - VERSIÓN COMPLETA"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"📋 Cliente {user['id']} solicitando historia de mascota: {pet_id}")

        # PASO 1: Verificar que la mascota pertenece al cliente
        verify_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}"
        verify_response = requests.get(verify_url, headers=headers, timeout=10)

        if verify_response.status_code != 200:
            return jsonify({
                'success': False,
                'message': 'Mascota no encontrada'
            }), 404

        verify_data = verify_response.json()
        if not verify_data.get('success'):
            return jsonify({
                'success': False,
                'message': 'Error verificando mascota'
            }), 400

        pet_data = verify_data.get('pet', {})
        if pet_data.get('owner_id') != user['id']:
            return jsonify({
                'success': False,
                'message': 'No tienes acceso a la historia clínica de esta mascota'
            }), 403

        print(f"✅ Mascota verificada: {pet_data.get('name')} pertenece al cliente")

        # PASO 2: Obtener historia clínica desde Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/records/pet/{pet_id}"
        response = requests.get(medical_url, headers=headers, timeout=10)

        print(f"📡 Respuesta Medical Service: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                medical_records = data.get('medical_records', [])

                # PASO 3: Enriquecer registros con información adicional
                enriched_records = []
                for record in medical_records:
                    try:
                        # Enriquecer con información del veterinario
                        vet_id = record.get('veterinarian_id')
                        if vet_id:
                            try:
                                # Obtener información del veterinario
                                users_response = requests.get(
                                    f"{current_app.config['AUTH_SERVICE_URL']}/auth/users",
                                    headers=headers,
                                    timeout=5
                                )

                                if users_response.status_code == 200:
                                    users_data = users_response.json()
                                    if users_data.get('success'):
                                        vet = next(
                                            (u for u in users_data['users'] if u['id'] == vet_id),
                                            None
                                        )
                                        if vet:
                                            record['veterinarian_name'] = f"Dr. {vet['first_name']} {vet['last_name']}"
                                        else:
                                            record['veterinarian_name'] = 'Dr. Veterinario'
                                    else:
                                        record['veterinarian_name'] = 'Dr. Veterinario'
                                else:
                                    record['veterinarian_name'] = 'Dr. Veterinario'
                            except Exception as e:
                                print(f"⚠️ Error obteniendo veterinario: {e}")
                                record['veterinarian_name'] = 'Dr. Veterinario'
                        else:
                            record['veterinarian_name'] = 'Dr. Veterinario'

                        # Obtener prescripciones/medicamentos del registro si existen
                        record_id = record.get('id')
                        if record_id:
                            try:
                                prescriptions_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/prescriptions/record/{record_id}"
                                prescriptions_response = requests.get(prescriptions_url, headers=headers, timeout=5)

                                if prescriptions_response.status_code == 200:
                                    prescriptions_data = prescriptions_response.json()
                                    if prescriptions_data.get('success'):
                                        record['medications'] = prescriptions_data.get('prescriptions', [])
                                    else:
                                        record['medications'] = []
                                else:
                                    record['medications'] = []
                            except Exception as e:
                                print(f"⚠️ Error obteniendo prescripciones: {e}")
                                record['medications'] = []
                        else:
                            record['medications'] = []

                        # Asegurar formato de fecha
                        if record.get('created_at'):
                            try:
                                # Verificar si la fecha está en formato correcto
                                datetime.strptime(record['created_at'][:19], '%Y-%m-%dT%H:%M:%S')
                            except:
                                # Si no es válida, usar fecha actual
                                record['created_at'] = datetime.now().isoformat()

                        enriched_records.append(record)

                    except Exception as e:
                        print(f"⚠️ Error enriqueciendo registro {record.get('id')}: {e}")
                        # Agregar registro básico sin enriquecimiento
                        if not record.get('veterinarian_name'):
                            record['veterinarian_name'] = 'Dr. Veterinario'
                        if not record.get('medications'):
                            record['medications'] = []
                        enriched_records.append(record)

                print(f"✅ {len(enriched_records)} registros médicos obtenidos y enriquecidos")

                return jsonify({
                    'success': True,
                    'medical_records': enriched_records,
                    'pet_info': {
                        'id': pet_data['id'],
                        'name': pet_data['name'],
                        'species': pet_data['species'],
                        'breed': pet_data.get('breed', ''),
                        'birth_date': pet_data.get('birth_date'),
                        'weight': pet_data.get('weight')
                    },
                    'total_records': len(enriched_records)
                })
            else:
                return jsonify({
                    'success': True,
                    'medical_records': [],
                    'pet_info': {
                        'id': pet_data['id'],
                        'name': pet_data['name'],
                        'species': pet_data['species']
                    },
                    'total_records': 0
                })
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Medical Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio médico'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_client_pet_medical_history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


@frontend_bp.route('/api/client/medical-history/summary')
@role_required(['client'])
def api_client_medical_history_summary():
    """API para obtener resumen de historia clínica de todas las mascotas del cliente"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"📊 Generando resumen médico para cliente: {user['id']}")

        # Obtener todas las mascotas del cliente
        pets_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/owner/{user['id']}"
        pets_response = requests.get(pets_url, headers=headers, timeout=10)

        if pets_response.status_code != 200:
            return jsonify({
                'success': False,
                'message': 'Error obteniendo mascotas'
            }), pets_response.status_code

        pets_data = pets_response.json()
        if not pets_data.get('success'):
            return jsonify({
                'success': True,
                'summary': {
                    'total_pets': 0,
                    'total_records': 0,
                    'recent_visits': 0,
                    'pets_with_records': []
                }
            })

        pets = pets_data.get('pets', [])
        total_records = 0
        recent_visits = 0
        pets_with_records = []

        # Obtener registros para cada mascota
        for pet in pets:
            try:
                records_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/records/pet/{pet['id']}"
                records_response = requests.get(records_url, headers=headers, timeout=5)

                pet_records_count = 0
                last_visit = None

                if records_response.status_code == 200:
                    records_data = records_response.json()
                    if records_data.get('success'):
                        records = records_data.get('medical_records', [])
                        pet_records_count = len(records)
                        total_records += pet_records_count

                        # Contar visitas recientes (últimos 30 días)
                        from datetime import datetime, timedelta
                        thirty_days_ago = datetime.now() - timedelta(days=30)

                        recent_count = 0
                        for record in records:
                            try:
                                record_date = datetime.fromisoformat(record['created_at'].replace('Z', '+00:00'))
                                if record_date >= thirty_days_ago:
                                    recent_count += 1

                                # Encontrar última visita
                                if not last_visit or record_date > datetime.fromisoformat(
                                        last_visit.replace('Z', '+00:00')):
                                    last_visit = record['created_at']
                            except:
                                continue

                        recent_visits += recent_count

                if pet_records_count > 0:
                    pets_with_records.append({
                        'id': pet['id'],
                        'name': pet['name'],
                        'species': pet['species'],
                        'records_count': pet_records_count,
                        'last_visit': last_visit
                    })

            except Exception as e:
                print(f"⚠️ Error obteniendo registros para mascota {pet['id']}: {e}")
                continue

        summary = {
            'total_pets': len(pets),
            'total_records': total_records,
            'recent_visits': recent_visits,
            'pets_with_records': pets_with_records,
            'pets_without_records': len(pets) - len(pets_with_records)
        }

        print(f"✅ Resumen generado: {total_records} registros para {len(pets)} mascotas")

        return jsonify({
            'success': True,
            'summary': summary
        })

    except Exception as e:
        print(f"❌ Error en api_client_medical_history_summary: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/client/pets/<pet_id>/medical-history/export')
@role_required(['client'])
def api_client_export_medical_history(pet_id):
    """API para exportar historia clínica de una mascota en formato PDF"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"📄 Exportando historia clínica de mascota: {pet_id}")

        # Verificar que la mascota pertenece al cliente
        verify_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}"
        verify_response = requests.get(verify_url, headers=headers, timeout=10)

        if verify_response.status_code != 200:
            return jsonify({
                'success': False,
                'message': 'Mascota no encontrada'
            }), 404

        verify_data = verify_response.json()
        pet_data = verify_data.get('pet', {})

        if pet_data.get('owner_id') != user['id']:
            return jsonify({
                'success': False,
                'message': 'No tienes acceso a esta mascota'
            }), 403

        # Obtener historia clínica completa
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/records/pet/{pet_id}"
        response = requests.get(medical_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                medical_records = data.get('medical_records', [])

                # Generar contenido HTML para PDF
                html_content = generate_medical_history_pdf_content(pet_data, medical_records, user)

                return Response(
                    html_content,
                    mimetype='text/html',
                    headers={
                        'Content-Disposition': f'inline; filename=historia_clinica_{pet_data["name"]}_{datetime.now().strftime("%Y%m%d")}.html'
                    }
                )
            else:
                return jsonify({
                    'success': False,
                    'message': 'No se pudieron obtener los registros médicos'
                }), 404
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Medical Service: {response.status_code}'
            }), response.status_code

    except Exception as e:
        print(f"❌ Error exportando historia clínica: {e}")
        return jsonify({
            'success': False,
            'message': f'Error generando PDF: {str(e)}'
        }), 500


def generate_medical_history_pdf_content(pet, medical_records, owner):
    """Generar contenido HTML para PDF de historia clínica"""
    from datetime import datetime

    # Calcular edad de la mascota
    age = 'N/A'
    if pet.get('birth_date'):
        try:
            birth_date = datetime.strptime(pet['birth_date'], '%Y-%m-%d')
            today = datetime.now()
            age_years = (today - birth_date).days / 365.25

            if age_years < 1:
                age = f"{int(age_years * 12)} meses"
            else:
                age = f"{int(age_years)} años"
        except:
            age = 'N/A'

    # Ordenar registros por fecha
    sorted_records = sorted(medical_records, key=lambda x: x.get('created_at', ''), reverse=True)

    # Generar HTML de registros
    records_html = ""
    for record in sorted_records:
        record_date = 'Fecha no disponible'
        try:
            date_obj = datetime.fromisoformat(record['created_at'].replace('Z', '+00:00'))
            record_date = date_obj.strftime('%d/%m/%Y')
        except:
            pass

        records_html += f"""
        <div class="record-item">
            <div class="record-header">
                <h3>{record.get('reason', 'Consulta médica')}</h3>
                <span class="record-date">{record_date}</span>
            </div>
            <div class="record-content">
                <p><strong>Veterinario:</strong> {record.get('veterinarian_name', 'Dr. Veterinario')}</p>
                {f'<p><strong>Diagnóstico:</strong> {record["diagnosis"]}</p>' if record.get('diagnosis') else ''}
                {f'<p><strong>Tratamiento:</strong> {record["treatment"]}</p>' if record.get('treatment') else ''}
                {f'<p><strong>Síntomas:</strong> {record["symptoms"]}</p>' if record.get('symptoms') else ''}
                {f'<p><strong>Observaciones:</strong> {record["observations"]}</p>' if record.get('observations') else ''}
            </div>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Historia Clínica - {pet.get('name', 'Mascota')}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                color: #2D6A4F;
                line-height: 1.6;
                background: white;
            }}
            .header {{
                text-align: center;
                border-bottom: 3px solid #52B788;
                padding-bottom: 30px;
                margin-bottom: 40px;
            }}
            .clinic-name {{
                color: #2D6A4F;
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .document-title {{
                font-size: 24px;
                font-weight: bold;
                color: #38A3A5;
                margin-bottom: 20px;
            }}
            .pet-info {{
                background: #D8F3DC;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 30px;
            }}
            .pet-info h2 {{
                color: #2D6A4F;
                margin-bottom: 15px;
            }}
            .pet-details {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
            }}
            .detail-item {{
                display: flex;
                justify-content: space-between;
            }}
            .detail-label {{
                font-weight: bold;
                color: #52B788;
            }}
            .records-section {{
                margin-top: 30px;
            }}
            .section-title {{
                font-size: 20px;
                font-weight: bold;
                color: #2D6A4F;
                margin-bottom: 20px;
                border-bottom: 2px solid #B7E4C7;
                padding-bottom: 10px;
            }}
            .record-item {{
                background: #f8fff9;
                border: 1px solid #B7E4C7;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
            }}
            .record-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }}
            .record-header h3 {{
                color: #2D6A4F;
                margin: 0;
            }}
            .record-date {{
                background: #52B788;
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-size: 0.9rem;
            }}
            .record-content p {{
                margin-bottom: 10px;
            }}
            .footer {{
                margin-top: 50px;
                text-align: center;
                color: #52B788;
                font-size: 12px;
                border-top: 1px solid #B7E4C7;
                padding-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="clinic-name">🏥 CLÍNICA VETERINARIA</div>
            <div class="document-title">HISTORIA CLÍNICA</div>
        </div>

        <div class="pet-info">
            <h2>📋 Información de la Mascota</h2>
            <div class="pet-details">
                <div class="detail-item">
                    <span class="detail-label">Peso:</span>
                    <span>{pet.get('weight', 'N/A')} kg</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Propietario:</span>
                    <span>{owner.get('first_name', '')} {owner.get('last_name', '')}</span>
                </div>
            </div>
        </div>

        <div class="records-section">
            <div class="section-title">📋 Registros Médicos ({len(medical_records)} consultas)</div>
            {records_html if records_html else '<p style="text-align: center; color: #666; font-style: italic;">No hay registros médicos disponibles.</p>'}
        </div>

        <div class="footer">
            <p><strong>Historia clínica generada el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</strong></p>
            <p>Este documento contiene información médica confidencial</p>
        </div>
    </body>
    </html>
    """


# =============== ENDPOINT PARA DESCARGAR REGISTRO MÉDICO INDIVIDUAL ===============

@frontend_bp.route('/api/client/pets/<pet_id>/medical-records/<record_id>/pdf')
@role_required(['client'])
def api_client_download_medical_record_pdf(pet_id, record_id):
    """API para descargar un registro médico específico en formato PDF"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"📄 Cliente {user['id']} descargando PDF de registro {record_id} de mascota {pet_id}")

        # PASO 1: Verificar que la mascota pertenece al cliente
        verify_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}"
        verify_response = requests.get(verify_url, headers=headers, timeout=10)

        if verify_response.status_code != 200:
            return jsonify({
                'success': False,
                'message': 'Mascota no encontrada'
            }), 404

        verify_data = verify_response.json()
        if not verify_data.get('success'):
            return jsonify({
                'success': False,
                'message': 'Error verificando mascota'
            }), 400

        pet_data = verify_data.get('pet', {})
        if pet_data.get('owner_id') != user['id']:
            return jsonify({
                'success': False,
                'message': 'No tienes acceso a esta mascota'
            }), 403

        # PASO 2: Obtener el registro médico específico
        record_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/records/{record_id}"
        record_response = requests.get(record_url, headers=headers, timeout=10)

        if record_response.status_code != 200:
            return jsonify({
                'success': False,
                'message': 'Registro médico no encontrado'
            }), 404

        record_data = record_response.json()
        if not record_data.get('success'):
            return jsonify({
                'success': False,
                'message': 'Error obteniendo registro médico'
            }), 400

        medical_record = record_data.get('medical_record', {})

        # Verificar que el registro pertenece a la mascota correcta
        if medical_record.get('pet_id') != pet_id:
            return jsonify({
                'success': False,
                'message': 'El registro no pertenece a esta mascota'
            }), 403

        # PASO 3: Enriquecer el registro con información adicional
        try:
            # Obtener información del veterinario
            vet_id = medical_record.get('veterinarian_id')
            if vet_id:
                users_response = requests.get(
                    f"{current_app.config['AUTH_SERVICE_URL']}/auth/users",
                    headers=headers,
                    timeout=5
                )
                if users_response.status_code == 200:
                    users_data = users_response.json()
                    if users_data.get('success'):
                        vet = next(
                            (u for u in users_data['users'] if u['id'] == vet_id),
                            None
                        )
                        if vet:
                            medical_record['veterinarian_name'] = f"Dr. {vet['first_name']} {vet['last_name']}"

            # Obtener medicamentos prescritos
            try:
                prescriptions_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/prescriptions/record/{record_id}"
                prescriptions_response = requests.get(prescriptions_url, headers=headers, timeout=5)
                if prescriptions_response.status_code == 200:
                    prescriptions_data = prescriptions_response.json()
                    if prescriptions_data.get('success'):
                        medical_record['medications'] = prescriptions_data.get('prescriptions', [])
            except:
                medical_record['medications'] = []

        except Exception as e:
            print(f"⚠️ Error enriqueciendo datos: {e}")

        # PASO 4: Generar contenido HTML para PDF
        html_content = generate_individual_record_pdf_content(medical_record, pet_data, user)

        # PASO 5: Retornar como HTML para conversión a PDF
        return Response(
            html_content,
            mimetype='text/html',
            headers={
                'Content-Disposition': f'inline; filename=registro_medico_{pet_data["name"]}_{record_id}_{datetime.now().strftime("%Y%m%d")}.html'
            }
        )

    except requests.RequestException as e:
        print(f"❌ Error conectando con servicios: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con los servicios médicos'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_client_download_medical_record_pdf: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


def generate_individual_record_pdf_content(medical_record, pet_data, owner_data):
    """Generar contenido HTML para PDF de un registro médico individual"""
    from datetime import datetime

    # Calcular edad de la mascota
    age = 'N/A'
    if pet_data.get('birth_date'):
        try:
            birth_date = datetime.strptime(pet_data['birth_date'], '%Y-%m-%d')
            today = datetime.now()
            age_years = (today - birth_date).days / 365.25

            if age_years < 1:
                age = f"{int(age_years * 12)} meses"
            else:
                age = f"{int(age_years)} años"
        except:
            age = 'N/A'

    # Formatear fecha del registro
    record_date = 'Fecha no disponible'
    try:
        if medical_record.get('created_at'):
            date_obj = datetime.fromisoformat(medical_record['created_at'].replace('Z', '+00:00'))
            record_date = date_obj.strftime('%d de %B de %Y')
    except:
        pass

    # Determinar tipo de consulta
    reason = medical_record.get('reason', 'Consulta médica')
    record_type = 'Consulta General'

    reason_lower = reason.lower()
    if 'vacun' in reason_lower:
        record_type = 'Vacunación'
    elif 'emergencia' in reason_lower or medical_record.get('is_emergency'):
        record_type = 'Emergencia'
    elif 'cirugía' in reason_lower or 'operación' in reason_lower:
        record_type = 'Cirugía'

    # Generar tabla de medicamentos si existen
    medications_html = ""
    if medical_record.get('medications') and len(medical_record['medications']) > 0:
        medications_html = """
        <div class="field-group">
            <div class="field-label">
                💉 Medicamentos Prescritos
            </div>
            <table class="medications-table">
                <thead>
                    <tr>
                        <th>Medicamento</th>
                        <th>Dosis</th>
                        <th>Instrucciones</th>
                    </tr>
                </thead>
                <tbody>
        """

        for med in medical_record['medications']:
            med_name = med.get('name') or med.get('medication_name', 'Medicamento')
            med_dose = med.get('dosage') or med.get('dose', 'Según indicación médica')
            med_instructions = med.get('instructions', 'Seguir indicaciones del veterinario')

            medications_html += f"""
                    <tr>
                        <td><strong>{med_name}</strong></td>
                        <td>{med_dose}</td>
                        <td>{med_instructions}</td>
                    </tr>
            """

        medications_html += """
                </tbody>
            </table>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Registro Médico - {pet_data.get('name', 'Mascota')}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Arial', sans-serif;
                line-height: 1.6;
                color: #2D6A4F;
                background: white;
                padding: 20px;
            }}

            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: white;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
                border-radius: 10px;
                overflow: hidden;
            }}

            .header {{
                background: linear-gradient(135deg, #2D6A4F 0%, #52B788 100%);
                color: white;
                padding: 30px;
                text-align: center;
                position: relative;
            }}

            .header::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="2" fill="rgba(255,255,255,0.1)"/></svg>') repeat;
                opacity: 0.3;
            }}

            .logo {{
                font-size: 3rem;
                margin-bottom: 10px;
                position: relative;
                z-index: 1;
            }}

            .clinic-name {{
                font-size: 2rem;
                font-weight: bold;
                margin-bottom: 5px;
                position: relative;
                z-index: 1;
            }}

            .clinic-info {{
                font-size: 0.9rem;
                opacity: 0.9;
                margin-bottom: 20px;
                position: relative;
                z-index: 1;
            }}

            .document-title {{
                font-size: 1.5rem;
                font-weight: bold;
                background: rgba(255,255,255,0.2);
                padding: 10px 20px;
                border-radius: 25px;
                display: inline-block;
                position: relative;
                z-index: 1;
            }}

            .content {{
                padding: 30px;
            }}

            .info-section {{
                background: linear-gradient(135deg, #D8F3DC 0%, #B7E4C7 100%);
                padding: 25px;
                border-radius: 15px;
                margin-bottom: 25px;
                border: 1px solid #95D5B2;
                box-shadow: 0 5px 15px rgba(45, 106, 79, 0.1);
            }}

            .section-title {{
                font-size: 1.3rem;
                font-weight: bold;
                color: #2D6A4F;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 10px;
                border-bottom: 2px solid rgba(45, 106, 79, 0.2);
                padding-bottom: 10px;
            }}

            .info-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin-bottom: 15px;
            }}

            .info-item {{
                background: white;
                padding: 12px;
                border-radius: 8px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                border-left: 4px solid #52B788;
            }}

            .info-label {{
                font-weight: bold;
                color: #52B788;
            }}

            .info-value {{
                color: #2D6A4F;
                font-weight: 600;
            }}

            .record-section {{
                background: linear-gradient(to bottom, #f8fff9 0%, #ffffff 100%);
                padding: 30px;
                border-radius: 15px;
                margin-bottom: 20px;
                border: 1px solid #B7E4C7;
                box-shadow: 0 8px 25px rgba(45, 106, 79, 0.1);
            }}

            .record-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 25px;
                padding-bottom: 20px;
                border-bottom: 3px solid #B7E4C7;
            }}

            .record-title {{
                font-size: 1.8rem;
                color: #2D6A4F;
                font-weight: bold;
                margin: 0;
            }}

            .record-meta {{
                text-align: right;
            }}

            .record-date {{
                background: linear-gradient(135deg, #2D6A4F 0%, #40916C 100%);
                color: white;
                padding: 8px 16px;
                border-radius: 25px;
                font-size: 0.9rem;
                margin-bottom: 8px;
                display: inline-block;
                font-weight: 600;
                box-shadow: 0 3px 10px rgba(45, 106, 79, 0.3);
            }}

            .record-type {{
                background: linear-gradient(135deg, #52B788 0%, #74C69D 100%);
                color: white;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 0.8rem;
                display: inline-block;
                font-weight: 600;
                box-shadow: 0 2px 8px rgba(82, 183, 136, 0.3);
            }}

            .field-group {{
                margin-bottom: 25px;
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 3px 12px rgba(0,0,0,0.1);
            }}

            .field-label {{
                font-weight: bold;
                color: white;
                background: linear-gradient(135deg, #2D6A4F 0%, #52B788 100%);
                padding: 12px 20px;
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 1.1rem;
            }}

            .field-value {{
                padding: 20px;
                color: #333;
                line-height: 1.6;
                font-size: 1rem;
                border-left: 4px solid #52B788;
            }}

            .medications-table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                margin-top: 15px;
            }}

            .medications-table th {{
                background: linear-gradient(135deg, #52B788 0%, #2D6A4F 100%);
                color: white;
                padding: 15px;
                text-align: left;
                font-weight: bold;
                font-size: 1rem;
            }}

            .medications-table td {{
                padding: 15px;
                border-bottom: 1px solid #B7E4C7;
                color: #2D6A4F;
                vertical-align: top;
            }}

            .medications-table tr:nth-child(even) {{
                background: #f8fff9;
            }}

            .medications-table tr:hover {{
                background: #D8F3DC;
            }}

            .footer {{
                background: linear-gradient(135deg, #f8fff9 0%, #D8F3DC 100%);
                padding: 25px;
                text-align: center;
                color: #52B788;
                font-size: 0.9rem;
                border-top: 3px solid #B7E4C7;
            }}

            .footer-title {{
                font-weight: bold;
                color: #2D6A4F;
                font-size: 1.1rem;
                margin-bottom: 10px;
            }}

            .footer-info {{
                margin: 5px 0;
                opacity: 0.8;
            }}

            .watermark {{
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) rotate(-45deg);
                font-size: 8rem;
                color: rgba(82, 183, 136, 0.03);
                z-index: -1;
                pointer-events: none;
                font-weight: bold;
            }}

            .no-data {{
                text-align: center;
                color: #666;
                font-style: italic;
                padding: 20px;
                background: #f9f9f9;
                border-radius: 8px;
                border: 2px dashed #ccc;
            }}

            @media print {{
                body {{
                    padding: 0;
                    -webkit-print-color-adjust: exact;
                    color-adjust: exact;
                }}
                .container {{
                    box-shadow: none;
                    border-radius: 0;
                }}
                .watermark {{
                    display: none;
                }}
                .field-group {{
                    break-inside: avoid;
                }}
                .record-section {{
                    break-inside: avoid;
                }}
            }}

            @page {{
                margin: 20mm;
                size: A4;
            }}
        </style>
    </head>
    <body>
        <div class="watermark">🏥 VETERINARIA</div>

        <div class="container">
            <!-- HEADER -->
            <div class="header">
                <div class="logo">🏥</div>
                <div class="clinic-name">CLÍNICA VETERINARIA</div>
                <div class="clinic-info">
                    📍 Calle 123 #45-67, Bogotá, Colombia<br>
                    📞 (601) 234-5678 | 📧 info@clinicaveterinaria.com<br>
                    🌐 www.clinicaveterinaria.com
                </div>
                <div class="document-title">REGISTRO MÉDICO INDIVIDUAL</div>
            </div>

            <div class="content">
                <!-- INFORMACIÓN DE LA MASCOTA -->
                <div class="info-section">
                    <div class="section-title">
                        🐾 Información de la Mascota
                    </div>
                    <div class="info-grid">
                        <div class="info-item">
                            <span class="info-label">Nombre:</span>
                            <span class="info-value">{pet_data.get('name', 'N/A')}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Especie:</span>
                            <span class="info-value">{pet_data.get('species', 'N/A')}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Raza:</span>
                            <span class="info-value">{pet_data.get('breed') or 'No especificada'}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Edad:</span>
                            <span class="info-value">{age}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Peso:</span>
                            <span class="info-value">{pet_data.get('weight') or 'N/A'} kg</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Propietario:</span>
                            <span class="info-value">{owner_data.get('first_name', '')} {owner_data.get('last_name', '')}</span>
                        </div>
                    </div>
                </div>

                <!-- INFORMACIÓN DEL REGISTRO MÉDICO -->
                <div class="record-section">
                    <div class="record-header">
                        <div class="record-title">
                            {reason}
                        </div>
                        <div class="record-meta">
                            <div class="record-date">{record_date}</div>
                            <div class="record-type">{record_type}</div>
                        </div>
                    </div>

                    <div class="field-group">
                        <div class="field-label">
                            👨‍⚕️ Veterinario Responsable
                        </div>
                        <div class="field-value">
                            {medical_record.get('veterinarian_name') or 'Dr. Veterinario'}
                        </div>
                    </div>

                    {f'''
                    <div class="field-group">
                        <div class="field-label">
                            🔍 Diagnóstico Médico
                        </div>
                        <div class="field-value">
                            {medical_record['diagnosis']}
                        </div>
                    </div>
                    ''' if medical_record.get('diagnosis') else ''}

                    {f'''
                    <div class="field-group">
                        <div class="field-label">
                            📋 Síntomas Observados
                        </div>
                        <div class="field-value">
                            {medical_record['symptoms']}
                        </div>
                    </div>
                    ''' if medical_record.get('symptoms') else ''}

                    {f'''
                    <div class="field-group">
                        <div class="field-label">
                            🏥 Examen Físico
                        </div>
                        <div class="field-value">
                            {medical_record['physical_exam']}
                        </div>
                    </div>
                    ''' if medical_record.get('physical_exam') else ''}

                    {f'''
                    <div class="field-group">
                        <div class="field-label">
                            💊 Tratamiento Prescrito
                        </div>
                        <div class="field-value">
                            {medical_record['treatment']}
                        </div>
                    </div>
                    ''' if medical_record.get('treatment') else ''}

                    {medications_html}

                    {f'''
                    <div class="field-group">
                        <div class="field-label">
                            📝 Observaciones y Recomendaciones
                        </div>
                        <div class="field-value">
                            {medical_record['observations']}
                        </div>
                    </div>
                    ''' if medical_record.get('observations') else ''}

                    {f'''
                    <div class="field-group">
                        <div class="field-label">
                            📅 Próxima Cita Programada
                        </div>
                        <div class="field-value">
                            {datetime.strptime(medical_record['next_appointment'], '%Y-%m-%d').strftime('%d de %B de %Y') if medical_record.get('next_appointment') else 'No programada'}
                        </div>
                    </div>
                    ''' if medical_record.get('next_appointment') else ''}

                    {'''
                    <div class="field-group">
                        <div class="field-label">
                            ⚠️ Consulta de Emergencia
                        </div>
                        <div class="field-value">
                            ⚠️ Esta fue una consulta de emergencia que requirió atención inmediata.
                        </div>
                    </div>
                    ''' if medical_record.get('is_emergency') else ''}
                </div>
            </div>

            <!-- FOOTER -->
            <div class="footer">
                <div class="footer-title">🏥 CLÍNICA VETERINARIA - REGISTRO MÉDICO OFICIAL</div>
                <div class="footer-info">📄 Documento generado el {datetime.now().strftime('%d de %B de %Y a las %H:%M:%S')}</div>
                <div class="footer-info">⚕️ Este documento contiene información médica confidencial</div>
                <div class="footer-info">🔒 Para uso exclusivo del propietario y personal médico autorizado</div>
                <div class="footer-info">📞 Para consultas: (601) 234-5678 | 📧 info@clinicaveterinaria.com</div>
            </div>
        </div>

        <script>
            // Auto-focus para impresión cuando se carga la página
            window.addEventListener('load', function() {{
                setTimeout(function() {{
                    window.focus();
                    // Si es una petición de descarga automática, abrir diálogo de impresión
                    if (window.location.search.includes('autoprint=true')) {{
                        window.print();
                    }}
                }}, 800);
            }});

            // Detectar cuando se cierra el diálogo de impresión
            window.addEventListener('afterprint', function() {{
                // Opcionalmente cerrar la ventana después de imprimir
                setTimeout(function() {{
                    window.close();
                }}, 1000);
            }});
        </script>
    </body>
    </html>
    """

def validate_profile_data(data, current_user):
    """Validar datos del perfil antes de enviar al backend"""
    errors = []

    # Validar campos requeridos
    if not data.get('first_name', '').strip():
        errors.append('El nombre es requerido')

    if not data.get('last_name', '').strip():
        errors.append('El apellido es requerido')

    if not data.get('email', '').strip():
        errors.append('El correo electrónico es requerido')

    # Validar formato de email
    if data.get('email'):
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            errors.append('El formato del correo electrónico no es válido')

    # Validar teléfono (opcional pero si existe debe ser válido)
    if data.get('phone', '').strip():
        phone = data['phone'].strip()
        # Permitir formatos: +57 300 123 4567, 300 123 4567, 3001234567
        phone_pattern = r'^(\+\d{1,3}\s?)?\d{3}\s?\d{3}\s?\d{4}$'
        if not re.match(phone_pattern, phone.replace('-', ' ')):
            errors.append('El formato del teléfono no es válido (ej: +57 300 123 4567)')

    # Validar longitud de campos
    if len(data.get('first_name', '')) > 50:
        errors.append('El nombre no puede tener más de 50 caracteres')

    if len(data.get('last_name', '')) > 50:
        errors.append('El apellido no puede tener más de 50 caracteres')

    if len(data.get('address', '')) > 255:
        errors.append('La dirección no puede tener más de 255 caracteres')

    return errors

@frontend_bp.route('/client/profile')
@role_required(['client'])
def client_profile():
    """Página de perfil del cliente - VERSIÓN CORREGIDA PARA USAR ENDPOINT CORRECTO"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"🔍 Usuario en sesión: {user}")

        # PASO 1: Obtener datos actualizados usando el endpoint /auth/profile (no /auth/users/{id})
        fresh_user_data = user.copy()  # Usar datos de sesión como fallback

        try:
            # CAMBIO PRINCIPAL: Usar /auth/profile en lugar de /auth/users/{id}
            auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/profile"
            response = requests.get(auth_url, headers=headers, timeout=10)

            print(f"📡 Respuesta Auth Service /profile: {response.status_code}")

            if response.status_code == 200:
                auth_data = response.json()
                if auth_data.get('success'):
                    fresh_user_data = auth_data.get('user', {})
                    print(f"✅ Datos actualizados obtenidos desde BD usando /auth/profile")

                    # Actualizar la sesión con datos frescos
                    session['user'] = fresh_user_data
                    session.permanent = True
                else:
                    print(f"⚠️ Auth Service error: {auth_data.get('message')}")
            else:
                print(f"⚠️ Auth Service HTTP error: {response.status_code}")

        except requests.RequestException as e:
            print(f"⚠️ Error conectando con Auth Service: {e}")
        except Exception as e:
            print(f"⚠️ Error general obteniendo datos: {e}")

        # PASO 2: Obtener estadísticas del perfil
        profile_stats = get_client_profile_stats(user['id'], headers)

        # PASO 3: Preparar datos para el template
        user_data = {
            'id': fresh_user_data.get('id', ''),
            'email': fresh_user_data.get('email', ''),
            'first_name': fresh_user_data.get('first_name', ''),
            'last_name': fresh_user_data.get('last_name', ''),
            'phone': fresh_user_data.get('phone', ''),
            'address': fresh_user_data.get('address', ''),
            'role': fresh_user_data.get('role', 'client'),
            'is_active': fresh_user_data.get('is_active', True),
            'created_at': fresh_user_data.get('created_at', ''),
            'updated_at': fresh_user_data.get('updated_at', '')
        }

        print(f"📋 Datos finales para template: {user_data}")

        # PASO 4: Calcular valores derivados
        first_name = user_data.get('first_name', '').strip()
        last_name = user_data.get('last_name', '').strip()
        user_name = f"{first_name} {last_name}".strip() or 'Cliente'
        user_initial = first_name[0].upper() if first_name else 'C'

        template_data = {
            'user': user_data,
            'user_name': user_name,
            'user_initial': user_initial,
            'profile_stats': profile_stats
        }

        print(f"✅ Template data preparado: {template_data}")

        return render_template('client/sections/profile.html', **template_data)

    except Exception as e:
        print(f"❌ Error en client_profile: {e}")
        import traceback
        traceback.print_exc()

        # Fallback con datos mínimos
        user = session.get('user', {})
        fallback_data = {
            'user': {
                'id': user.get('id', ''),
                'email': user.get('email', ''),
                'first_name': '',
                'last_name': '',
                'phone': '',
                'address': '',
                'role': 'client',
                'is_active': True,
                'created_at': '',
                'updated_at': ''
            },
            'user_name': 'Cliente',
            'user_initial': 'C',
            'profile_stats': {
                'pets_count': 0,
                'appointments_count': 0,
                'days_as_client': 0
            }
        }

        flash('Error cargando datos del perfil. Mostrando datos básicos.', 'warning')
        return render_template('client/sections/profile.html', **fallback_data)

# AGREGAR TAMBIÉN esta función de soporte si no existe:
def get_client_profile_stats(user_id, headers):
    """Obtener estadísticas del cliente desde los microservicios"""
    stats = {
        'pets_count': 0,
        'appointments_count': 0,
        'days_as_client': 0,
        'last_appointment': None,
        'next_appointment': None
    }

    try:
        # Obtener mascotas del cliente
        pets_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/owner/{user_id}"
        pets_response = requests.get(pets_url, headers=headers, timeout=5)

        if pets_response.status_code == 200:
            pets_data = pets_response.json()
            if pets_data.get('success'):
                stats['pets_count'] = len(pets_data.get('pets', []))
                print(f"✅ Mascotas encontradas: {stats['pets_count']}")

    except Exception as e:
        print(f"⚠️ Error obteniendo mascotas: {e}")

    try:
        # Obtener citas del cliente
        appointments_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/client/{user_id}"
        appointments_response = requests.get(appointments_url, headers=headers, timeout=5)

        if appointments_response.status_code == 200:
            appointments_data = appointments_response.json()
            if appointments_data.get('success'):
                appointments = appointments_data.get('appointments', [])
                stats['appointments_count'] = len(appointments)

                # Buscar última y próxima cita
                from datetime import datetime
                today = datetime.now()

                past_appointments = []
                future_appointments = []

                for apt in appointments:
                    try:
                        apt_date = datetime.strptime(apt['appointment_date'], '%Y-%m-%d')
                        if apt_date < today:
                            past_appointments.append(apt)
                        else:
                            future_appointments.append(apt)
                    except:
                        continue

                # Última cita (más reciente del pasado)
                if past_appointments:
                    last_apt = max(past_appointments, key=lambda x: x['appointment_date'])
                    stats['last_appointment'] = last_apt['appointment_date']

                # Próxima cita (más próxima del futuro)
                if future_appointments:
                    next_apt = min(future_appointments, key=lambda x: x['appointment_date'])
                    stats['next_appointment'] = next_apt['appointment_date']

                print(f"✅ Citas encontradas: {stats['appointments_count']}")

    except Exception as e:
        print(f"⚠️ Error obteniendo citas: {e}")

    try:
        # Calcular días como cliente
        user_response = requests.get(
            f"{current_app.config['AUTH_SERVICE_URL']}/auth/profile",
            headers=headers,
            timeout=5
        )

        if user_response.status_code == 200:
            user_data = user_response.json()
            if user_data.get('success'):
                user_info = user_data.get('user', {})
                if user_info.get('created_at'):
                    from datetime import datetime
                    created_date = datetime.fromisoformat(user_info['created_at'].replace('Z', '+00:00'))
                    today = datetime.now()
                    days_diff = (today - created_date).days
                    stats['days_as_client'] = max(0, days_diff)
                    print(f"✅ Días como cliente: {stats['days_as_client']}")

    except Exception as e:
        print(f"⚠️ Error calculando días: {e}")

    return stats

# También agregar este endpoint para obtener el perfil actual
@frontend_bp.route('/api/client/profile', methods=['GET'])
@role_required(['client'])
def api_client_update_profile():
    """API para actualizar perfil del cliente - VERSIÓN CORREGIDA"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        print(f"📝 Cliente {user['id']} actualizando perfil")
        print(f"📝 Datos recibidos: {data}")

        # VALIDACIONES DEL LADO DEL FRONTEND
        errors = validate_profile_data(data, user)
        if errors:
            return jsonify({
                'success': False,
                'message': 'Datos inválidos',
                'errors': errors
            }), 400

        # Preparar datos para actualización
        update_data = {
            'first_name': data['first_name'].strip(),
            'last_name': data['last_name'].strip(),
            'email': data['email'].strip().lower(),
            'phone': data.get('phone', '').strip(),
            'address': data.get('address', '').strip()
        }

        print(f"📡 Enviando datos al Auth Service: {update_data}")

        # USAR ENDPOINT CORRECTO: /auth/profile
        auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/profile"
        response = requests.put(auth_url, json=update_data, headers=headers, timeout=15)

        print(f"📡 Respuesta Auth Service: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                updated_user = result.get('user', {})

                # Actualizar la sesión con los nuevos datos
                session['user'] = {**session['user'], **updated_user}
                session.permanent = True

                print(f"✅ Perfil actualizado exitosamente para usuario {user['id']}")

                return jsonify({
                    'success': True,
                    'message': 'Perfil actualizado exitosamente',
                    'user': updated_user
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result.get('message', 'Error actualizando perfil')
                }), 400
        else:
            # Manejar errores del Auth Service
            try:
                error_data = response.json()
                error_message = error_data.get('message', f'Error del Auth Service: {response.status_code}')
            except:
                error_message = f'Error del Auth Service: {response.status_code}'

            print(f"❌ Error Auth Service: {response.status_code} - {error_message}")
            return jsonify({
                'success': False,
                'message': error_message
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Auth Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de autenticación'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_client_update_profile: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500

def validate_profile_data(data, current_user):
    """Validar datos del perfil antes de enviar al backend"""
    errors = []

    # Validar campos requeridos
    if not data.get('first_name', '').strip():
        errors.append('El nombre es requerido')

    if not data.get('last_name', '').strip():
        errors.append('El apellido es requerido')

    if not data.get('email', '').strip():
        errors.append('El correo electrónico es requerido')

    # Validar formato de email
    if data.get('email'):
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            errors.append('El formato del correo electrónico no es válido')

    # Validar teléfono (opcional pero si existe debe ser válido)
    if data.get('phone', '').strip():
        phone = data['phone'].strip()
        phone_pattern = r'^(\+\d{1,3}\s?)?\d{3}\s?\d{3}\s?\d{4}$'
        if not re.match(phone_pattern, phone.replace('-', ' ')):
            errors.append('El formato del teléfono no es válido (ej: +57 300 123 4567)')

    # Validar longitud de campos
    if len(data.get('first_name', '')) > 50:
        errors.append('El nombre no puede tener más de 50 caracteres')

    if len(data.get('last_name', '')) > 50:
        errors.append('El apellido no puede tener más de 50 caracteres')

    if len(data.get('address', '')) > 255:
        errors.append('La dirección no puede tener más de 255 caracteres')

    return errors


@frontend_bp.route('/api/client/profile/stats')
@role_required(['client'])
def api_client_profile_stats():
    """API para obtener estadísticas del perfil del cliente - VERSIÓN MEJORADA"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"📊 Obteniendo estadísticas para cliente: {user['id']}")

        # Inicializar estadísticas
        stats = {
            'pets_count': 0,
            'appointments_count': 0,
            'days_as_client': 0,
            'last_appointment': None,
            'next_appointment': None
        }

        # PASO 1: Obtener mascotas del cliente
        try:
            print("🐾 Obteniendo mascotas...")
            pets_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/owner/{user['id']}"
            pets_response = requests.get(pets_url, headers=headers, timeout=10)

            print(f"📡 Respuesta mascotas: {pets_response.status_code}")

            if pets_response.status_code == 200:
                pets_data = pets_response.json()
                print(f"🐾 Datos mascotas: {pets_data}")

                if pets_data.get('success'):
                    pets = pets_data.get('pets', [])
                    stats['pets_count'] = len(pets)
                    print(f"✅ Mascotas encontradas: {stats['pets_count']}")
                else:
                    print(f"⚠️ Medical Service error: {pets_data.get('message')}")
            else:
                print(f"⚠️ Medical Service HTTP error: {pets_response.status_code}")

        except requests.RequestException as e:
            print(f"❌ Error conectando con Medical Service: {e}")
        except Exception as e:
            print(f"❌ Error general obteniendo mascotas: {e}")

        # PASO 2: Obtener citas del cliente
        try:
            print("📅 Obteniendo citas...")
            appointments_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/client/{user['id']}"
            appointments_response = requests.get(appointments_url, headers=headers, timeout=10)

            print(f"📡 Respuesta citas: {appointments_response.status_code}")

            if appointments_response.status_code == 200:
                appointments_data = appointments_response.json()
                print(f"📅 Datos citas: {appointments_data}")

                if appointments_data.get('success'):
                    appointments = appointments_data.get('appointments', [])
                    stats['appointments_count'] = len(appointments)
                    print(f"✅ Citas encontradas: {stats['appointments_count']}")

                    # Buscar última y próxima cita
                    from datetime import datetime
                    today = datetime.now()
                    past_appointments = []
                    future_appointments = []

                    for apt in appointments:
                        try:
                            apt_date = datetime.strptime(apt['appointment_date'], '%Y-%m-%d')
                            if apt_date < today:
                                past_appointments.append(apt)
                            else:
                                future_appointments.append(apt)
                        except:
                            continue

                    # Última cita
                    if past_appointments:
                        last_apt = max(past_appointments, key=lambda x: x['appointment_date'])
                        stats['last_appointment'] = last_apt['appointment_date']

                    # Próxima cita
                    if future_appointments:
                        next_apt = min(future_appointments, key=lambda x: x['appointment_date'])
                        stats['next_appointment'] = next_apt['appointment_date']

                else:
                    print(f"⚠️ Appointment Service error: {appointments_data.get('message')}")
            else:
                print(f"⚠️ Appointment Service HTTP error: {appointments_response.status_code}")

        except requests.RequestException as e:
            print(f"❌ Error conectando con Appointment Service: {e}")
        except Exception as e:
            print(f"❌ Error general obteniendo citas: {e}")

        # PASO 3: Calcular días como cliente
        try:
            print("📅 Calculando días como cliente...")
            if user.get('created_at'):
                from datetime import datetime
                created_date = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
                today = datetime.now()
                days_diff = (today - created_date).days
                stats['days_as_client'] = max(0, days_diff)
                print(f"✅ Días como cliente: {stats['days_as_client']}")
            else:
                print("⚠️ No hay fecha de creación en la sesión")
        except Exception as e:
            print(f"❌ Error calculando días: {e}")

        print(f"📊 Estadísticas finales: {stats}")

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        print(f"❌ Error en api_client_profile_stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/client/profile', methods=['GET'])
@role_required(['client'])
def api_client_validate_profile():
    """API para validar datos del perfil antes de actualizar"""
    try:
        data = request.get_json()
        current_user = session.get('user', {})

        errors = validate_profile_data(data, current_user)

        # Verificar si el email ya existe (si es diferente al actual)
        if data.get('email') and data['email'].lower() != current_user.get('email', '').lower():
            try:
                headers = {'Authorization': f"Bearer {session.get('token')}"}
                check_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/users/check-email"
                check_response = requests.post(check_url,
                                               json={'email': data['email']},
                                               headers=headers,
                                               timeout=5)

                if check_response.status_code == 200:
                    check_data = check_response.json()
                    if check_data.get('exists'):
                        errors.append('Este correo electrónico ya está registrado')
            except:
                # Si no se puede verificar, continuar (la validación se hará en el servidor)
                pass

        if errors:
            return jsonify({
                'success': False,
                'message': 'Datos inválidos',
                'errors': errors
            }), 400
        else:
            return jsonify({
                'success': True,
                'message': 'Datos válidos'
            })

    except Exception as e:
        print(f"❌ Error en api_client_validate_profile: {e}")
        return jsonify({
            'success': False,
            'message': 'Error validando datos'
        }), 500


@frontend_bp.route('/veterinarian/dashboard')
@role_required(['veterinarian'])
def veterinarian_dashboard():
    """Dashboard principal para veterinarios"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener estadísticas básicas
        dashboard_stats = {
            'today_appointments_count': 0,
            'total_patients': 0,
            'pending_records': 0,
            'completed_today': 0
        }

        # Intentar obtener datos reales
        try:
            # Citas de hoy
            appointments_response = requests.get(
                f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/veterinarian/{user['id']}/today",
                headers=headers, timeout=5
            )
            if appointments_response.status_code == 200:
                apt_data = appointments_response.json()
                if apt_data.get('success'):
                    dashboard_stats['today_appointments_count'] = len(apt_data.get('appointments', []))

            # Pacientes totales
            patients_response = requests.get(
                f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/veterinarian/{user['id']}/patients",
                headers=headers, timeout=5
            )
            if patients_response.status_code == 200:
                patients_data = patients_response.json()
                if patients_data.get('success'):
                    dashboard_stats['total_patients'] = len(patients_data.get('patients', []))

        except Exception as e:
            print(f"⚠️ Error obteniendo estadísticas del veterinario: {e}")

        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Dr. Veterinario',
            'user_role': 'Veterinario',
            'user_initial': user.get('first_name', 'V')[0].upper() if user.get('first_name') else 'V',
            **dashboard_stats
        }

        return render_template('veterinarian/dashboard.html', **template_data)

    except Exception as e:
        print(f"❌ Error en veterinarian dashboard: {e}")
        flash('Error al cargar el dashboard', 'error')
        return redirect(url_for('frontend.login'))

@frontend_bp.route('/veterinarian/schedule')
@role_required(['veterinarian'])
def veterinarian_schedule():
    """Página de horario del veterinario"""
    try:
        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Dr. Veterinario',
            'user_role': 'Veterinario',
            'user_initial': user.get('first_name', 'V')[0].upper() if user.get('first_name') else 'V'
        }

        return render_template('veterinarian/schedule.html', **template_data)

    except Exception as e:
        print(f"❌ Error en veterinarian schedule: {e}")
        flash('Error al cargar el horario', 'error')
        return redirect(url_for('frontend.veterinarian_dashboard'))


@frontend_bp.route('/veterinarian/calendar')
@role_required(['veterinarian'])
def veterinarian_calendar():
    """Página de calendario del veterinario"""
    try:
        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Dr. Veterinario',
            'user_role': 'Veterinario',
            'user_initial': user.get('first_name', 'V')[0].upper() if user.get('first_name') else 'V'
        }

        return render_template('veterinarian/calendar.html', **template_data)

    except Exception as e:
        print(f"❌ Error en veterinarian calendar: {e}")
        flash('Error al cargar el calendario', 'error')
        return redirect(url_for('frontend.veterinarian_dashboard'))


@frontend_bp.route('/veterinarian/appointments')
@role_required(['veterinarian'])
def veterinarian_appointments():
    """Página de citas del veterinario"""
    try:
        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Dr. Veterinario',
            'user_role': 'Veterinario',
            'user_initial': user.get('first_name', 'V')[0].upper() if user.get('first_name') else 'V'
        }

        return render_template('veterinarian/appointments.html', **template_data)

    except Exception as e:
        print(f"❌ Error en veterinarian appointments: {e}")
        flash('Error al cargar las citas', 'error')
        return redirect(url_for('frontend.veterinarian_dashboard'))


@frontend_bp.route('/veterinarian/emergency')
@role_required(['veterinarian'])
def veterinarian_emergency():
    """Página de emergencias del veterinario"""
    try:
        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Dr. Veterinario',
            'user_role': 'Veterinario',
            'user_initial': user.get('first_name', 'V')[0].upper() if user.get('first_name') else 'V'
        }

        return render_template('veterinarian/emergency.html', **template_data)

    except Exception as e:
        print(f"❌ Error en veterinarian emergency: {e}")
        flash('Error al cargar emergencias', 'error')
        return redirect(url_for('frontend.veterinarian_dashboard'))


@frontend_bp.route('/veterinarian/patients')
@role_required(['veterinarian'])
def veterinarian_patients():
    """Página de pacientes del veterinario"""
    try:
        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Dr. Veterinario',
            'user_role': 'Veterinario',
            'user_initial': user.get('first_name', 'V')[0].upper() if user.get('first_name') else 'V'
        }

        return render_template('veterinarian/patients.html', **template_data)

    except Exception as e:
        print(f"❌ Error en veterinarian patients: {e}")
        flash('Error al cargar pacientes', 'error')
        return redirect(url_for('frontend.veterinarian_dashboard'))


@frontend_bp.route('/veterinarian/search-patients')
@role_required(['veterinarian'])
def veterinarian_search_patients():
    """Página de búsqueda de pacientes"""
    try:
        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Dr. Veterinario',
            'user_role': 'Veterinario',
            'user_initial': user.get('first_name', 'V')[0].upper() if user.get('first_name') else 'V'
        }

        return render_template('veterinarian/search-patients.html', **template_data)

    except Exception as e:
        print(f"❌ Error en veterinarian search patients: {e}")
        flash('Error al cargar búsqueda de pacientes', 'error')
        return redirect(url_for('frontend.veterinarian_dashboard'))


@frontend_bp.route('/veterinarian/medical-records')
@role_required(['veterinarian'])
def veterinarian_medical_records():
    """Página de historias clínicas del veterinario"""
    try:
        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Dr. Veterinario',
            'user_role': 'Veterinario',
            'user_initial': user.get('first_name', 'V')[0].upper() if user.get('first_name') else 'V'
        }

        return render_template('veterinarian/medical-records.html', **template_data)

    except Exception as e:
        print(f"❌ Error en veterinarian medical records: {e}")
        flash('Error al cargar historias clínicas', 'error')
        return redirect(url_for('frontend.veterinarian_dashboard'))


@frontend_bp.route('/veterinarian/records-history')
@role_required(['veterinarian'])
def veterinarian_records_history():
    """Página de historial de registros del veterinario"""
    try:
        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Dr. Veterinario',
            'user_role': 'Veterinario',
            'user_initial': user.get('first_name', 'V')[0].upper() if user.get('first_name') else 'V'
        }

        return render_template('veterinarian/records-history.html', **template_data)

    except Exception as e:
        print(f"❌ Error en veterinarian records history: {e}")
        flash('Error al cargar historial de registros', 'error')
        return redirect(url_for('frontend.veterinarian_dashboard'))


@frontend_bp.route('/veterinarian/prescriptions')
@role_required(['veterinarian'])
def veterinarian_prescriptions():
    """Página de prescripciones del veterinario"""
    try:
        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Dr. Veterinario',
            'user_role': 'Veterinario',
            'user_initial': user.get('first_name', 'V')[0].upper() if user.get('first_name') else 'V'
        }

        return render_template('veterinarian/prescriptions.html', **template_data)

    except Exception as e:
        print(f"❌ Error en veterinarian prescriptions: {e}")
        flash('Error al cargar prescripciones', 'error')
        return redirect(url_for('frontend.veterinarian_dashboard'))


@frontend_bp.route('/veterinarian/inventory')
@role_required(['veterinarian'])
def veterinarian_inventory():
    """Página de inventario del veterinario"""
    try:
        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Dr. Veterinario',
            'user_role': 'Veterinario',
            'user_initial': user.get('first_name', 'V')[0].upper() if user.get('first_name') else 'V'
        }

        return render_template('veterinarian/inventory.html', **template_data)

    except Exception as e:
        print(f"❌ Error en veterinarian inventory: {e}")
        flash('Error al cargar inventario', 'error')
        return redirect(url_for('frontend.veterinarian_dashboard'))
    
    
@frontend_bp.route('/veterinarian/exams')
@role_required(['veterinarian'])
def veterinarian_exams():
    """Página de exámenes del veterinario"""
    try:
        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Dr. Veterinario',
            'user_role': 'Veterinario',
            'user_initial': user.get('first_name', 'V')[0].upper() if user.get('first_name') else 'V'
        }

        return render_template('veterinarian/exams.html', **template_data)

    except Exception as e:
        print(f"❌ Error en veterinarian exams: {e}")
        flash('Error al cargar exámenes', 'error')
        return redirect(url_for('frontend.veterinarian_dashboard'))

@frontend_bp.route('/veterinarian/references')
@role_required(['veterinarian'])
def veterinarian_references():
    """Página de referencias médicas del veterinario"""
    try:
        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Dr. Veterinario',
            'user_role': 'Veterinario',
            'user_initial': user.get('first_name', 'V')[0].upper() if user.get('first_name') else 'V'
        }

        return render_template('veterinarian/references.html', **template_data)

    except Exception as e:
        print(f"❌ Error en veterinarian references: {e}")
        flash('Error al cargar referencias', 'error')
        return redirect(url_for('frontend.veterinarian_dashboard'))


@frontend_bp.route('/veterinarian/profile')
@role_required(['veterinarian'])
def veterinarian_profile():
    """Página de perfil del veterinario"""
    try:
        user = session.get('user', {})
        template_data = {
            'user': user,
            'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Dr. Veterinario',
            'user_role': 'Veterinario',
            'user_initial': user.get('first_name', 'V')[0].upper() if user.get('first_name') else 'V'
        }

        return render_template('veterinarian/profile.html', **template_data)

    except Exception as e:
        print(f"❌ Error en veterinarian profile: {e}")
        flash('Error al cargar perfil', 'error')
        return redirect(url_for('frontend.veterinarian_dashboard'))


@frontend_bp.route('/api/veterinarian/schedule')
@role_required(['veterinarian'])
def api_veterinarian_schedule():
    """API para obtener horario del veterinario"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"📅 Obteniendo horario para veterinario: {user['id']}")

        # Obtener horario desde Auth Service
        auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/schedules"
        response = requests.get(auth_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                schedules = data.get('schedules', [])

                # Buscar horario del veterinario actual
                vet_schedule = next((s for s in schedules if s.get('user_id') == user['id']), None)

                if vet_schedule:
                    weekly_schedule = vet_schedule.get('weekly_schedule', {})
                    working_hours = {}

                    # Calcular horas de trabajo
                    for day, schedule in weekly_schedule.items():
                        if schedule and schedule.get('active'):
                            working_hours[day] = {
                                'start': schedule.get('start', '08:00'),
                                'end': schedule.get('end', '17:00'),
                                'break_start': schedule.get('break_start', '12:00'),
                                'break_end': schedule.get('break_end', '13:00')
                            }

                    return jsonify({
                        'success': True,
                        'schedule': weekly_schedule,
                        'working_hours': working_hours
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'No se encontró horario configurado',
                        'schedule': {},
                        'working_hours': {}
                    })
            else:
                return jsonify({
                    'success': False,
                    'message': data.get('message', 'Error obteniendo horarios')
                })
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Auth Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Auth Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de autenticación'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_veterinarian_schedule: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/veterinarian/appointments')
@role_required(['veterinarian'])
def api_veterinarian_appointments():
    """API para obtener citas del veterinario"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Parámetros de filtro
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        print(f"📋 Obteniendo citas para veterinario: {user['id']}")

        # Construir URL con parámetros
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/veterinarian/{user['id']}"
        params = {}

        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date

        response = requests.get(appointment_url, headers=headers, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                appointments = data.get('appointments', [])

                # Enriquecer con datos de mascotas y clientes
                try:
                    # Obtener información de mascotas
                    for appointment in appointments:
                        pet_id = appointment.get('pet_id')
                        client_id = appointment.get('client_id')

                        # Obtener datos de la mascota
                        if pet_id:
                            try:
                                pet_response = requests.get(
                                    f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/pets/{pet_id}",
                                    headers=headers, timeout=3
                                )
                                if pet_response.status_code == 200:
                                    pet_data = pet_response.json()
                                    if pet_data.get('success'):
                                        pet = pet_data['pet']
                                        appointment['pet_name'] = pet['name']
                                        appointment['pet_species'] = pet['species']
                            except:
                                appointment['pet_name'] = 'Mascota'
                                appointment['pet_species'] = 'unknown'

                        # Obtener datos del cliente
                        if client_id:
                            try:
                                client_response = requests.get(
                                    f"{current_app.config['AUTH_SERVICE_URL']}/auth/users/{client_id}",
                                    headers=headers, timeout=3
                                )
                                if client_response.status_code == 200:
                                    client_data = client_response.json()
                                    if client_data.get('success'):
                                        client = client_data['user']
                                        appointment['client_name'] = f"{client['first_name']} {client['last_name']}"
                            except:
                                appointment['client_name'] = 'Cliente'

                except Exception as e:
                    print(f"⚠️ Error enriqueciendo datos de citas: {e}")

                return jsonify({
                    'success': True,
                    'appointments': appointments,
                    'total': len(appointments)
                })
            else:
                return jsonify({
                    'success': True,
                    'appointments': [],
                    'total': 0
                })
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Appointment Service: {response.status_code}'
            }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_veterinarian_appointments: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/veterinarian/appointments/today')
@role_required(['veterinarian'])
def api_veterinarian_appointments_today():
    """API para obtener citas de hoy del veterinario"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"📅 Obteniendo citas de hoy para veterinario: {user['id']}")

        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/veterinarian/{user['id']}/today"
        response = requests.get(appointment_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                appointments = data.get('appointments', [])

                # Enriquecer con datos básicos
                for appointment in appointments:
                    # Agregar valores por defecto si faltan
                    appointment.setdefault('pet_name', 'Mascota')
                    appointment.setdefault('pet_species', 'unknown')
                    appointment.setdefault('client_name', 'Cliente')
                    appointment.setdefault('reason', 'Consulta general')

                return jsonify({
                    'success': True,
                    'appointments': appointments,
                    'total': len(appointments)
                })
            else:
                return jsonify({
                    'success': True,
                    'appointments': [],
                    'total': 0
                })
        else:
            # Fallback con datos de ejemplo
            example_appointments = get_example_vet_appointments_today()
            return jsonify({
                'success': True,
                'appointments': example_appointments,
                'total': len(example_appointments),
                'message': 'Usando datos de ejemplo'
            })

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        # Fallback con datos de ejemplo
        example_appointments = get_example_vet_appointments_today()
        return jsonify({
            'success': True,
            'appointments': example_appointments,
            'total': len(example_appointments),
            'message': 'Sin conexión - datos de ejemplo'
        })
    except Exception as e:
        print(f"❌ Error en api_veterinarian_appointments_today: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/veterinarian/patients/recent')
@role_required(['veterinarian'])
def api_veterinarian_patients_recent():
    """API para obtener pacientes recientes del veterinario"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"🐕 Obteniendo pacientes recientes para veterinario: {user['id']}")

        # Obtener pacientes desde Medical Service
        medical_url = f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/veterinarian/{user['id']}/patients/recent"
        response = requests.get(medical_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                patients = data.get('patients', [])

                return jsonify({
                    'success': True,
                    'patients': patients,
                    'total_patients': data.get('total_patients', len(patients))
                })
            else:
                return jsonify({
                    'success': True,
                    'patients': [],
                    'total_patients': 0
                })
        else:
            # Fallback con datos de ejemplo
            example_patients = get_example_vet_patients()
            return jsonify({
                'success': True,
                'patients': example_patients,
                'total_patients': len(example_patients),
                'message': 'Usando datos de ejemplo'
            })

    except requests.RequestException as e:
        print(f"❌ Error conectando con Medical Service: {e}")
        # Fallback con datos de ejemplo
        example_patients = get_example_vet_patients()
        return jsonify({
            'success': True,
            'patients': example_patients,
            'total_patients': len(example_patients),
            'message': 'Sin conexión - datos de ejemplo'
        })
    except Exception as e:
        print(f"❌ Error en api_veterinarian_patients_recent: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/veterinarian/dashboard/stats')
@role_required(['veterinarian'])
def api_veterinarian_dashboard_stats():
    """API para obtener estadísticas del dashboard del veterinario"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        stats = {
            'pending_records': 0,
            'completed_today': 0,
            'total_patients': 0,
            'emergency_count': 0
        }

        # Intentar obtener estadísticas reales
        try:
            # Registros médicos pendientes
            records_response = requests.get(
                f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/veterinarian/{user['id']}/records/pending",
                headers=headers, timeout=5
            )
            if records_response.status_code == 200:
                records_data = records_response.json()
                if records_data.get('success'):
                    stats['pending_records'] = records_data.get('count', 0)

            # Completadas hoy
            today_response = requests.get(
                f"{current_app.config['MEDICAL_SERVICE_URL']}/medical/veterinarian/{user['id']}/records/completed/today",
                headers=headers, timeout=5
            )
            if today_response.status_code == 200:
                today_data = today_response.json()
                if today_data.get('success'):
                    stats['completed_today'] = today_data.get('count', 0)

        except Exception as e:
            print(f"⚠️ Error obteniendo estadísticas: {e}")

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        print(f"❌ Error en api_veterinarian_dashboard_stats: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/veterinarian/schedule/stats')
@role_required(['veterinarian'])
def api_veterinarian_schedule_stats():
    """API para obtener estadísticas del horario del veterinario"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        stats = {
            'today_appointments': 0,
            'week_appointments': 0,
            'working_days': 0,
            'total_hours': 0
        }

        # Citas de hoy
        try:
            today_response = requests.get(
                f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/veterinarian/{user['id']}/today",
                headers=headers, timeout=5
            )
            if today_response.status_code == 200:
                today_data = today_response.json()
                if today_data.get('success'):
                    stats['today_appointments'] = len(today_data.get('appointments', []))
        except:
            pass

        # Citas de la semana
        try:
            from datetime import datetime, timedelta
            start_week = datetime.now() - timedelta(days=datetime.now().weekday())
            end_week = start_week + timedelta(days=6)

            week_response = requests.get(
                f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/veterinarian/{user['id']}",
                headers=headers,
                params={
                    'start_date': start_week.strftime('%Y-%m-%d'),
                    'end_date': end_week.strftime('%Y-%m-%d')
                },
                timeout=5
            )
            if week_response.status_code == 200:
                week_data = week_response.json()
                if week_data.get('success'):
                    stats['week_appointments'] = len(week_data.get('appointments', []))
        except:
            pass

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        print(f"❌ Error en api_veterinarian_schedule_stats: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/veterinarian/notifications/count')
@role_required(['veterinarian'])
def api_veterinarian_notifications_count():
    """API para contar notificaciones del veterinario"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        data = {
            'unread_notifications': 0,
            'today_appointments': 0,
            'pending_records': 0,
            'emergency_alerts': 0
        }

        # Intentar obtener notificaciones
        try:
            notif_response = requests.get(
                f"{current_app.config['NOTIFICATION_SERVICE_URL']}/notifications/user/{user['id']}/unread/count",
                headers=headers, timeout=5
            )
            if notif_response.status_code == 200:
                notif_data = notif_response.json()
                if notif_data.get('success'):
                    data['unread_notifications'] = notif_data.get('count', 0)
        except:
            pass

        # Citas de hoy
        try:
            today_response = requests.get(
                f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/veterinarian/{user['id']}/today",
                headers=headers, timeout=5
            )
            if today_response.status_code == 200:
                today_data = today_response.json()
                if today_data.get('success'):
                    data['today_appointments'] = len(today_data.get('appointments', []))
        except:
            pass

        return jsonify({
            'success': True,
            'data': data
        })

    except Exception as e:
        print(f"❌ Error en api_veterinarian_notifications_count: {e}")
        return jsonify({
            'success': True,
            'data': {
                'unread_notifications': 0,
                'today_appointments': 0,
                'pending_records': 0,
                'emergency_alerts': 0
            }
        })


@frontend_bp.route('/api/veterinarian/emergencies/check')
@role_required(['veterinarian'])
def api_veterinarian_emergencies_check():
    """API para verificar emergencias del veterinario"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Verificar si hay citas de emergencia pendientes
        try:
            emergency_response = requests.get(
                f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/veterinarian/{user['id']}/emergency",
                headers=headers, timeout=5
            )

            if emergency_response.status_code == 200:
                emergency_data = emergency_response.json()
                if emergency_data.get('success'):
                    emergency_appointments = emergency_data.get('appointments', [])

                    return jsonify({
                        'success': True,
                        'has_emergencies': len(emergency_appointments) > 0,
                        'emergency_count': len(emergency_appointments),
                        'emergencies': emergency_appointments
                    })
        except:
            pass

        return jsonify({
            'success': True,
            'has_emergencies': False,
            'emergency_count': 0,
            'emergencies': []
        })

    except Exception as e:
        print(f"❌ Error en api_veterinarian_emergencies_check: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/veterinarian/appointments/<appointment_id>/start', methods=['PUT'])
@role_required(['veterinarian'])
def api_veterinarian_start_appointment(appointment_id):
    """API para iniciar una cita"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"🩺 Veterinario {user['id']} iniciando cita: {appointment_id}")

        # Marcar cita como en progreso
        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/{appointment_id}/start"
        response = requests.put(appointment_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Cita iniciada correctamente',
                    'appointment': data.get('appointment', {})
                })

        return jsonify({
            'success': False,
            'message': f'Error del Appointment Service: {response.status_code}'
        }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_veterinarian_start_appointment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/veterinarian/appointments/<appointment_id>/complete', methods=['PUT'])
@role_required(['veterinarian'])
def api_veterinarian_complete_appointment(appointment_id):
    """API para completar una cita"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        print(f"✅ Veterinario {user['id']} completando cita: {appointment_id}")

        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/{appointment_id}/complete"
        response = requests.put(appointment_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Cita completada correctamente',
                    'appointment': data.get('appointment', {})
                })

        return jsonify({
            'success': False,
            'message': f'Error del Appointment Service: {response.status_code}'
        }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_veterinarian_complete_appointment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@frontend_bp.route('/api/veterinarian/appointments/<appointment_id>/cancel', methods=['PUT'])
@role_required(['veterinarian'])
def api_veterinarian_cancel_appointment(appointment_id):
    """API para cancelar una cita"""
    try:
        user = session.get('user', {})
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json() or {}

        print(f"❌ Veterinario {user['id']} cancelando cita: {appointment_id}")

        appointment_url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/{appointment_id}/cancel"
        response = requests.put(appointment_url, json=data, headers=headers, timeout=10)

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('success'):
                return jsonify({
                    'success': True,
                    'message': 'Cita cancelada correctamente',
                    'appointment': response_data.get('appointment', {})
                })

        return jsonify({
            'success': False,
            'message': f'Error del Appointment Service: {response.status_code}'
        }), response.status_code

    except requests.RequestException as e:
        print(f"❌ Error conectando con Appointment Service: {e}")
        return jsonify({
            'success': False,
            'message': 'Error de conexión con el servicio de citas'
        }), 500
    except Exception as e:
        print(f"❌ Error en api_veterinarian_cancel_appointment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== FUNCIONES DE DATOS DE EJEMPLO PARA VETERINARIO ===============

def get_example_vet_appointments_today():
    """Datos de ejemplo para citas de hoy del veterinario"""
    from datetime import datetime, timedelta

    now = datetime.now()

    return [
        {
            'id': 'apt_vet_001',
            'pet_id': 'pet_001',
            'pet_name': 'Max',
            'pet_species': 'perro',
            'client_id': 'client_001',
            'client_name': 'Carlos López',
            'appointment_date': now.strftime('%Y-%m-%d'),
            'appointment_time': '09:00',
            'status': 'confirmed',
            'priority': 'normal',
            'reason': 'Consulta de rutina',
            'notes': 'Control mensual'
        },
        {
            'id': 'apt_vet_002',
            'pet_id': 'pet_002',
            'pet_name': 'Luna',
            'pet_species': 'gato',
            'client_id': 'client_002',
            'client_name': 'María González',
            'appointment_date': now.strftime('%Y-%m-%d'),
            'appointment_time': '10:30',
            'status': 'scheduled',
            'priority': 'high',
            'reason': 'Control post-operatorio',
            'notes': 'Revisar cicatrización'
        },
        {
            'id': 'apt_vet_003',
            'pet_id': 'pet_003',
            'pet_name': 'Rocky',
            'pet_species': 'perro',
            'client_id': 'client_003',
            'client_name': 'Ana Martínez',
            'appointment_date': now.strftime('%Y-%m-%d'),
            'appointment_time': '14:00',
            'status': 'scheduled',
            'priority': 'emergency',
            'reason': 'Emergencia respiratoria',
            'notes': 'Dificultad para respirar'
        }
    ]


def get_example_vet_patients():
    """Datos de ejemplo para pacientes del veterinario"""
    from datetime import datetime, timedelta

    recent_date = datetime.now() - timedelta(days=3)

    return [
        {
            'id': 'pet_001',
            'name': 'Max',
            'species': 'perro',
            'breed': 'Golden Retriever',
            'age': '3 años',
            'owner_id': 'client_001',
            'owner_name': 'Carlos López',
            'last_visit': recent_date.strftime('%Y-%m-%d'),
            'visits_count': 8
        },
        {
            'id': 'pet_002',
            'name': 'Luna',
            'species': 'gato',
            'breed': 'Persa',
            'age': '2 años',
            'owner_id': 'client_002',
            'owner_name': 'María González',
            'last_visit': (recent_date - timedelta(days=1)).strftime('%Y-%m-%d'),
            'visits_count': 5
        },
        {
            'id': 'pet_003',
            'name': 'Rocky',
            'species': 'perro',
            'breed': 'Pastor Alemán',
            'age': '5 años',
            'owner_id': 'client_003',
            'owner_name': 'Ana Martínez',
            'last_visit': (recent_date - timedelta(days=2)).strftime('%Y-%m-%d'),
            'visits_count': 12
        }]

@frontend_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'frontend_service'
    }), 200



