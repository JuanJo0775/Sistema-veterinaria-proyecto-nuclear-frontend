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


@frontend_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'frontend_service'
    }), 200

