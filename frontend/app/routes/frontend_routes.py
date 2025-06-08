# frontend/app/routes/frontend_routes.py - VERSIÓN CORREGIDA
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from functools import wraps
import requests
from flask import send_from_directory
import os

from frontend.config import role_required

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


@frontend_bp.route('/admin/inventory')
@role_required(['admin'])
def admin_inventory():
    """Página de gestión de inventario"""
    user = session.get('user', {})
    template_data = {
        'user': user,
        'user_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or 'Administrador',
        'user_role': user.get('role', 'admin').title(),
        'user_initial': user.get('first_name', 'A')[0].upper() if user.get('first_name') else 'A'
    }
    return render_template('admin/sections/inventory-management.html', **template_data)


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

@frontend_bp.route('/client/dashboard')
@role_required(['client'])
def client_dashboard():
    """Dashboard para clientes"""
    return render_template('client/dashboard.html')


@frontend_bp.route('/veterinarian/dashboard')
@role_required(['veterinarian'])
def veterinarian_dashboard():
    """Dashboard para veterinarios"""
    return render_template('veterinarian/dashboard.html')


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
    """Actualizar horario de un usuario específico"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}
        data = request.get_json()

        # Actualizar horario en Auth Service
        auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/schedules/{user_id}"
        response = requests.put(auth_url, json=data, headers=headers, timeout=10)

        if response.status_code == 200:
            return jsonify(response.json())
        elif response.status_code == 404:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404
        elif response.status_code == 400:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            return jsonify({
                'success': False,
                'message': error_data.get('message', 'Datos de horario inválidos')
            }), 400
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
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
        print(f"❌ Error en api_update_user_schedule: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


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


@frontend_bp.route('/api/admin/inventory/medications')
@role_required(['admin'])
def api_get_medications_for_prescriptions():
    """Obtener medicamentos disponibles para prescripciones"""
    try:
        headers = {'Authorization': f"Bearer {session.get('token')}"}

        # Obtener medicamentos del Inventory Service
        inventory_url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/medications"
        response = requests.get(inventory_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                # Filtrar solo medicamentos activos con stock
                medications = [
                    med for med in data.get('medications', [])
                    if med.get('is_active', True) and med.get('stock_quantity', 0) > 0
                ]

                return jsonify({
                    'success': True,
                    'medications': medications,
                    'total': len(medications)
                })

        # Si falla, retornar array vacío
        return jsonify({
            'success': True,
            'medications': [],
            'total': 0
        })

    except Exception as e:
        print(f"❌ Error en api_get_medications_for_prescriptions: {e}")
        return jsonify({
            'success': True,
            'medications': [],
            'total': 0
        })


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


@frontend_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'frontend_service'
    }), 200

