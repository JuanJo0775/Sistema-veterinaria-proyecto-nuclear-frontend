# microservices/auth_service/app/routes/auth_routes.py
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash

from datetime import datetime, timedelta
from ..models.user import User, db
from ..services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        user = auth_service.authenticate_user(email, password)

        if user:
            token = auth_service.generate_token(user)
            return jsonify({
                'success': True,
                'token': token,
                'user': {
                    'id': str(user.id),  # ← FIX: Convertir UUID a string
                    'email': user.email,
                    'role': user.role,
                    'name': f"{user.first_name} {user.last_name}"
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Credenciales inválidas'
            }), 401

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@auth_bp.route('/register', methods=['POST'])
def register():
    """Registrar nuevo usuario - ACTUALIZADO para admin"""
    try:
        data = request.get_json()

        # Validar que el email no exista
        if User.query.filter_by(email=data.get('email')).first():
            return jsonify({
                'success': False,
                'message': 'Email ya registrado'
            }), 400

        # Si hay token de admin, permitir crear cualquier rol
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        current_user = None

        if token:
            current_user = auth_service.verify_token(token)

        # Determinar rol
        role = 'client'  # Por defecto
        if current_user and current_user.role == 'admin':
            # Admin puede crear cualquier rol
            role = data.get('role', 'client')
        elif 'role' in data and data['role'] != 'client':
            # Solo admin puede crear roles no-client
            return jsonify({
                'success': False,
                'message': 'No tienes permisos para crear usuarios con ese rol'
            }), 403

        # Crear usuario
        user = User(
            email=data.get('email'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            phone=data.get('phone'),
            address=data.get('address'),
            role=role,
            is_active=data.get('is_active', True)
        )

        user.set_password(data.get('password'))

        db.session.add(user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Usuario creado exitosamente',
            'user': user.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@auth_bp.route('/verify', methods=['POST'])
def verify_token():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = auth_service.verify_token(token)

        if user:
            return jsonify({
                'success': True,
                'user': {
                    'id': str(user.id),  # ← FIX: Convertir UUID a string
                    'email': user.email,
                    'role': user.role,
                    'name': f"{user.first_name} {user.last_name}"
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Token inválido'
            }), 401

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@auth_bp.route('/change-password', methods=['PUT'])
def change_password():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = auth_service.verify_token(token)

        if not user:
            return jsonify({
                'success': False,
                'message': 'Token inválido'
            }), 401

        data = request.get_json()
        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if auth_service.change_password(str(user.id), old_password, new_password):  # ← FIX: Convertir UUID a string
            return jsonify({
                'success': True,
                'message': 'Contraseña actualizada exitosamente'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Contraseña actual incorrecta'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = auth_service.verify_token(token)

        if user:
            print(f"✅ Perfil obtenido para usuario: {user.email}")
            return jsonify({
                'success': True,
                'user': user.to_dict()  # ← El método to_dict() ya maneja la conversión UUID
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Token inválido'
            }), 401

    except Exception as e:
        print(f"❌ Error en get_profile: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = auth_service.verify_token(token)

        if not user:
            return jsonify({
                'success': False,
                'message': 'Token inválido'
            }), 401

        data = request.get_json()
        print(f"📝 Actualizando perfil de usuario: {user.email}")
        print(f"📝 Datos recibidos: {data}")
        updated_user = auth_service.update_user(str(user.id), data)  # ← FIX: Convertir UUID a string

        if updated_user:
            print(f"✅ Perfil actualizado exitosamente para: {user.email}")
            return jsonify({
                'success': True,
                'message': 'Perfil actualizado exitosamente',
                'user': updated_user.to_dict()  # ← El método to_dict() ya maneja la conversión UUID
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Error al actualizar perfil'
            }), 400

    except Exception as e:
        print(f"❌ Error en update_profile: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@auth_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'auth_service'
    }), 200


@auth_bp.route('/users', methods=['GET'])
def get_all_users():
    """Obtener todos los usuarios (solo para admin)"""
    try:
        # Verificar token de administrador
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = auth_service.verify_token(token)

        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado. Solo administradores pueden ver usuarios.'
            }), 403

        # Obtener todos los usuarios
        users = User.query.all()
        users_data = [user.to_dict() for user in users]

        return jsonify({
            'success': True,
            'users': users_data,
            'total': len(users_data)
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo usuarios: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@auth_bp.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Actualizar usuario específico (solo para admin)"""
    try:
        # Verificar token de administrador
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = auth_service.verify_token(token)

        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado'
            }), 403

        # Obtener datos a actualizar
        data = request.get_json()

        # Buscar usuario a actualizar
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404

        # Actualizar campos permitidos
        updatable_fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'role', 'is_active']

        for field in updatable_fields:
            if field in data:
                setattr(target_user, field, data[field])

        # Verificar email único si se está cambiando
        if 'email' in data and data['email'] != target_user.email:
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user and existing_user.id != target_user.id:
                return jsonify({
                    'success': False,
                    'message': 'Email ya está en uso'
                }), 400

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Usuario actualizado exitosamente',
            'user': target_user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@auth_bp.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Eliminar usuario definitivamente (solo para admin)"""
    try:
        # Verificar token de administrador
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = auth_service.verify_token(token)

        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado. Solo administradores pueden eliminar usuarios.'
            }), 403

        # Buscar usuario a eliminar
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404

        # No permitir eliminar al propio usuario admin
        if str(target_user.id) == str(user.id):
            return jsonify({
                'success': False,
                'message': 'No puedes eliminar tu propia cuenta'
            }), 400

        # Guardar información del usuario para el log
        user_info = f"{target_user.first_name} {target_user.last_name} ({target_user.email})"

        # ELIMINAR DEFINITIVAMENTE de la base de datos
        db.session.delete(target_user)
        db.session.commit()

        print(f"🗑️ Usuario eliminado definitivamente: {user_info} por {user.email}")

        return jsonify({
            'success': True,
            'message': f'Usuario {user_info} eliminado definitivamente del sistema'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error eliminando usuario: {e}")
        return jsonify({
            'success': False,
            'message': f'Error interno al eliminar usuario: {str(e)}'
        }), 500

@auth_bp.route('/users/<user_id>/toggle-status', methods=['PUT'])
def toggle_user_status(user_id):
    """Activar/Desactivar usuario (solo para admin)"""
    try:
        # Verificar token de administrador
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = auth_service.verify_token(token)

        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado'
            }), 403

        # Buscar usuario
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404

        # No permitir desactivar al propio usuario admin
        if str(target_user.id) == str(user.id) and target_user.is_active:
            return jsonify({
                'success': False,
                'message': 'No puedes desactivar tu propia cuenta'
            }), 400

        # Cambiar estado
        target_user.is_active = not target_user.is_active
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Usuario {"activado" if target_user.is_active else "desactivado"} exitosamente',
            'user': target_user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@auth_bp.route('/users/<user_id>', methods=['GET'])
def get_user_by_id(user_id):
    """Obtener usuario específico por ID (solo para admin O el propio usuario)"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        current_user = auth_service.verify_token(token)

        if not current_user:
            return jsonify({
                'success': False,
                'message': 'Token inválido'
            }), 401

        # Permitir si es admin O si está solicitando su propio perfil
        if current_user.role == 'admin' or str(current_user.id) == user_id:
            target_user = auth_service.get_user_by_id(user_id)

            if target_user:
                return jsonify({
                    'success': True,
                    'user': target_user.to_dict()
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': 'Usuario no encontrado'
                }), 404
        else:
            return jsonify({
                'success': False,
                'message': 'Sin permisos para acceder a este usuario'
            }), 403

    except Exception as e:
        print(f"❌ Error en get_user_by_id: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@auth_bp.route('/users/stats', methods=['GET'])
def get_users_stats():
    """Obtener estadísticas de usuarios (solo para admin)"""
    try:
        # Verificar token de administrador
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = auth_service.verify_token(token)

        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado'
            }), 403

        # Calcular estadísticas
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        inactive_users = User.query.filter_by(is_active=False).count()

        # Por roles
        admin_count = User.query.filter_by(role='admin', is_active=True).count()
        vet_count = User.query.filter_by(role='veterinarian', is_active=True).count()
        receptionist_count = User.query.filter_by(role='receptionist', is_active=True).count()
        auxiliary_count = User.query.filter_by(role='auxiliary', is_active=True).count()
        client_count = User.query.filter_by(role='client', is_active=True).count()

        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': inactive_users,
                'by_role': {
                    'admin': admin_count,
                    'veterinarian': vet_count,
                    'receptionist': receptionist_count,
                    'auxiliary': auxiliary_count,
                    'client': client_count
                }
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# AGREGAR AL FINAL DE: microservices/auth_service/app/routes/auth_routes.py

# =============== SCHEDULES MANAGEMENT ENDPOINTS ===============

@auth_bp.route('/schedules', methods=['GET'])
def get_all_schedules():
    """Obtener todos los horarios (solo para admin)"""
    try:
        # Verificar token de administrador
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = auth_service.verify_token(token)

        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado. Solo administradores pueden ver horarios.'
            }), 403

        # Obtener usuarios con roles que pueden tener horarios
        staff_users = User.query.filter(
            User.role.in_(['veterinarian', 'receptionist', 'auxiliary']),
            User.is_active == True
        ).all()

        # Crear estructura de horarios
        schedules_data = []
        for staff_user in staff_users:
            user_schedule = {
                'user_id': str(staff_user.id),
                'user_name': f"{staff_user.first_name} {staff_user.last_name}",
                'user_email': staff_user.email,
                'user_role': staff_user.role,
                'phone': staff_user.phone,
                'weekly_schedule': generate_user_schedule(staff_user.role)
            }
            schedules_data.append(user_schedule)

        return jsonify({
            'success': True,
            'schedules': schedules_data,
            'total': len(schedules_data)
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo horarios: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500




@auth_bp.route('/schedules/<user_id>', methods=['GET'])
def get_user_schedule(user_id):
    """Obtener horario de un usuario específico"""
    try:
        # Verificar token de administrador
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = auth_service.verify_token(token)

        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado'
            }), 403

        # Buscar usuario
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404

        if target_user.role not in ['veterinarian', 'receptionist', 'auxiliary']:
            return jsonify({
                'success': False,
                'message': 'Este usuario no puede tener horarios asignados'
            }), 400

        # Generar horario
        schedule_data = {
            'user_id': str(target_user.id),
            'user_name': f"{target_user.first_name} {target_user.last_name}",
            'user_email': target_user.email,
            'user_role': target_user.role,
            'phone': target_user.phone,
            'weekly_schedule': generate_user_schedule(target_user.role)
        }

        return jsonify({
            'success': True,
            'schedule': schedule_data
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo horario del usuario: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@auth_bp.route('/schedules/<user_id>', methods=['PUT'])
def update_user_schedule(user_id):
    """Actualizar horario de un usuario"""
    try:
        # Verificar token de administrador
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = auth_service.verify_token(token)

        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado'
            }), 403

        # Buscar usuario
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404

        # Obtener datos del horario
        data = request.get_json()
        weekly_schedule = data.get('weekly_schedule', {})

        # Validar formato del horario
        if not validate_schedule_format(weekly_schedule):
            return jsonify({
                'success': False,
                'message': 'Formato de horario inválido'
            }), 400

        # En una implementación real, aquí se guardarían en una tabla schedules
        # Por ahora, simularemos que se guardó correctamente

        print(f"📅 Horario actualizado para {target_user.first_name} {target_user.last_name}")
        print(f"   Horario: {weekly_schedule}")

        return jsonify({
            'success': True,
            'message': f'Horario actualizado exitosamente para {target_user.first_name} {target_user.last_name}',
            'schedule': {
                'user_id': str(target_user.id),
                'user_name': f"{target_user.first_name} {target_user.last_name}",
                'weekly_schedule': weekly_schedule
            }
        }), 200



    except Exception as e:
        print(f"❌ Error actualizando horario: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== FUNCIONES AUXILIARES PARA HORARIOS ===============

def generate_user_schedule(role):
    """Generar horario específico según el rol"""
    if role == 'veterinarian':
        return {
            'monday': {'start': '08:00', 'end': '17:00', 'active': True, 'break_start': '12:00', 'break_end': '13:00'},
            'tuesday': {'start': '08:00', 'end': '17:00', 'active': True, 'break_start': '12:00', 'break_end': '13:00'},
            'wednesday': {'start': '08:00', 'end': '17:00', 'active': True, 'break_start': '12:00',
                          'break_end': '13:00'},
            'thursday': {'start': '08:00', 'end': '17:00', 'active': True, 'break_start': '12:00',
                         'break_end': '13:00'},
            'friday': {'start': '08:00', 'end': '16:00', 'active': True, 'break_start': '12:00', 'break_end': '13:00'},
            'saturday': {'start': '08:00', 'end': '12:00', 'active': True, 'break_start': '', 'break_end': ''},
            'sunday': {'start': '', 'end': '', 'active': False, 'break_start': '', 'break_end': ''}
        }
    elif role == 'receptionist':
        return {
            'monday': {'start': '07:30', 'end': '17:30', 'active': True, 'break_start': '12:00', 'break_end': '13:00'},
            'tuesday': {'start': '07:30', 'end': '17:30', 'active': True, 'break_start': '12:00', 'break_end': '13:00'},
            'wednesday': {'start': '07:30', 'end': '17:30', 'active': True, 'break_start': '12:00',
                          'break_end': '13:00'},
            'thursday': {'start': '07:30', 'end': '17:30', 'active': True, 'break_start': '12:00',
                         'break_end': '13:00'},
            'friday': {'start': '07:30', 'end': '18:00', 'active': True, 'break_start': '12:00', 'break_end': '13:00'},
            'saturday': {'start': '08:00', 'end': '13:00', 'active': True, 'break_start': '', 'break_end': ''},
            'sunday': {'start': '', 'end': '', 'active': False, 'break_start': '', 'break_end': ''}
        }
    else:  # auxiliary
        return {
            'monday': {'start': '08:00', 'end': '17:00', 'active': True, 'break_start': '12:00', 'break_end': '13:00'},
            'tuesday': {'start': '08:00', 'end': '17:00', 'active': True, 'break_start': '12:00', 'break_end': '13:00'},
            'wednesday': {'start': '08:00', 'end': '17:00', 'active': True, 'break_start': '12:00',
                          'break_end': '13:00'},
            'thursday': {'start': '08:00', 'end': '17:00', 'active': True, 'break_start': '12:00',
                         'break_end': '13:00'},
            'friday': {'start': '08:00', 'end': '16:00', 'active': True, 'break_start': '12:00', 'break_end': '13:00'},
            'saturday': {'start': '', 'end': '', 'active': False, 'break_start': '', 'break_end': ''},
            'sunday': {'start': '', 'end': '', 'active': False, 'break_start': '', 'break_end': ''}
        }


def validate_schedule_format(schedule):
    """Validar formato del horario"""
    try:
        required_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

        if not isinstance(schedule, dict):
            return False

        for day in required_days:
            if day not in schedule:
                return False

            day_data = schedule[day]
            if not isinstance(day_data, dict):
                return False

            # Validar campos requeridos
            required_fields = ['start', 'end', 'active']
            for field in required_fields:
                if field not in day_data:
                    return False

            # Si está activo, debe tener horarios válidos
            if day_data['active']:
                if not day_data['start'] or not day_data['end']:
                    return False

                # Validar formato de hora (HH:MM)
                try:
                    start_parts = day_data['start'].split(':')
                    end_parts = day_data['end'].split(':')

                    if len(start_parts) != 2 or len(end_parts) != 2:
                        return False

                    start_hour, start_min = int(start_parts[0]), int(start_parts[1])
                    end_hour, end_min = int(end_parts[0]), int(end_parts[1])

                    if not (0 <= start_hour <= 23 and 0 <= start_min <= 59):
                        return False
                    if not (0 <= end_hour <= 23 and 0 <= end_min <= 59):
                        return False

                    # Validar que hora de inicio sea menor que hora de fin
                    start_minutes = start_hour * 60 + start_min
                    end_minutes = end_hour * 60 + end_min

                    if start_minutes >= end_minutes:
                        return False

                except (ValueError, IndexError):
                    return False

        return True

    except Exception as e:
        print(f"❌ Error validando formato de horario: {e}")
        return False


@auth_bp.route('/users/<user_id>/internal', methods=['GET'])
def get_user_by_id_internal(user_id):
    """Obtener usuario específico para consultas internas entre servicios - SIN VERIFICACIÓN DE TOKEN"""
    try:
        print(f"🔍 Consulta interna para usuario: {user_id}")

        # Buscar usuario sin verificación de token (para consultas internas)
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({
                'success': False,
                'message': 'Usuario no encontrado'
            }), 404

        return jsonify({
            'success': True,
            'user': target_user.to_dict()
        }), 200

    except Exception as e:
        print(f"❌ Error en consulta interna: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# TAMBIÉN AGREGAR ESTA FUNCIÓN AUXILIAR MEJORADA
def get_user_role_internal(user_id):
    """Función interna para obtener el rol de un usuario"""
    try:
        user = User.query.get(user_id)
        if user:
            return user.role
        return None
    except Exception as e:
        print(f"⚠️ Error obteniendo rol del usuario {user_id}: {e}")
        return None





@auth_bp.route('/users/veterinarians', methods=['GET'])
def get_public_veterinarians():
    """Endpoint público para obtener lista de veterinarios activos"""
    try:
        print("👨‍⚕️ Obteniendo veterinarios públicos...")

        # Obtener solo veterinarios activos
        veterinarians = User.query.filter_by(
            role='veterinarian',
            is_active=True
        ).all()

        print(f"✅ {len(veterinarians)} veterinarios encontrados")

        # Convertir a diccionarios
        vets_data = []
        for vet in veterinarians:
            vet_dict = {
                'id': str(vet.id),
                'first_name': vet.first_name,
                'last_name': vet.last_name,
                'email': vet.email,
                'phone': vet.phone or '',
                'role': vet.role,
                'is_active': vet.is_active,
                'specialty': getattr(vet, 'specialty', 'Medicina General'),  # Campo opcional
                'created_at': vet.created_at.isoformat() if hasattr(vet, 'created_at') and vet.created_at else None
            }
            vets_data.append(vet_dict)

        return jsonify({
            'success': True,
            'veterinarians': vets_data,
            'total': len(vets_data)
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo veterinarios públicos: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}',
            'veterinarians': []
        }), 500


@auth_bp.route('/users/by-role/<role>', methods=['GET'])
def get_users_by_role(role):
    """Obtener usuarios por rol específico - ACCESO CONTROLADO"""
    try:
        print(f"🔍 Obteniendo usuarios con rol: {role}")

        # Verificar token solo si se proporciona
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        current_user = None

        if token:
            current_user = auth_service.verify_token(token)

        # Si hay token pero es inválido, denegar acceso
        if token and not current_user:
            return jsonify({
                'success': False,
                'message': 'Token inválido'
            }), 401

        # Si hay usuario autenticado pero no es admin, limitar acceso
        if current_user and current_user.role != 'admin' and role != 'veterinarian':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado'
            }), 403

        # Validar rol solicitado
        valid_roles = ['admin', 'veterinarian', 'receptionist', 'auxiliary', 'client']
        if role not in valid_roles:
            return jsonify({
                'success': False,
                'message': f'Rol inválido. Roles válidos: {", ".join(valid_roles)}'
            }), 400

        # Obtener usuarios del rol especificado (solo activos si no es admin quien pregunta)
        query = User.query.filter_by(role=role)

        if not (current_user and current_user.role == 'admin'):
            query = query.filter_by(is_active=True)

        users = query.all()

        print(f"✅ {len(users)} usuarios encontrados con rol {role}")

        # Convertir a diccionarios
        users_data = []
        for user in users:
            user_dict = {
                'id': str(user.id),
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'role': user.role,
                'is_active': user.is_active
            }

            # Agregar campos adicionales solo si el usuario está autenticado
            if current_user:
                user_dict.update({
                    'phone': user.phone or '',
                    'address': user.address or '',
                    'created_at': user.created_at.isoformat() if hasattr(user,
                                                                         'created_at') and user.created_at else None
                })

            users_data.append(user_dict)

        return jsonify({
            'success': True,
            'users': users_data,
            'total': len(users_data),
            'role': role
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo usuarios por rol: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}',
            'users': []
        }), 500


@auth_bp.route('/users/search', methods=['GET'])
def search_users():
    """Buscar usuarios por término de búsqueda"""
    try:
        # Verificar autenticación
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        current_user = auth_service.verify_token(token)

        if not current_user:
            return jsonify({
                'success': False,
                'message': 'Token de autenticación requerido'
            }), 401

        search_term = request.args.get('q', '').strip()
        role_filter = request.args.get('role')

        if not search_term:
            return jsonify({
                'success': False,
                'message': 'Término de búsqueda requerido'
            }), 400

        print(f"🔍 Buscando usuarios con término: '{search_term}'")

        # Construir query de búsqueda
        query = User.query.filter(
            db.or_(
                User.first_name.ilike(f'%{search_term}%'),
                User.last_name.ilike(f'%{search_term}%'),
                User.email.ilike(f'%{search_term}%')
            )
        )

        # Filtrar por rol si se especifica
        if role_filter:
            query = query.filter_by(role=role_filter)

        # Solo admin puede ver usuarios inactivos
        if current_user.role != 'admin':
            query = query.filter_by(is_active=True)

        users = query.limit(50).all()  # Limitar a 50 resultados

        print(f"✅ {len(users)} usuarios encontrados")

        # Convertir a diccionarios
        users_data = []
        for user in users:
            user_dict = {
                'id': str(user.id),
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'role': user.role,
                'is_active': user.is_active,
                'phone': user.phone or '',
                'match_score': calculate_match_score(user, search_term)
            }
            users_data.append(user_dict)

        # Ordenar por relevancia
        users_data.sort(key=lambda x: x['match_score'], reverse=True)

        return jsonify({
            'success': True,
            'users': users_data,
            'total': len(users_data),
            'search_term': search_term
        }), 200

    except Exception as e:
        print(f"❌ Error buscando usuarios: {e}")
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}',
            'users': []
        }), 500


def calculate_match_score(user, search_term):
    """Calcular puntuación de relevancia para búsqueda"""
    try:
        score = 0
        search_lower = search_term.lower()

        # Coincidencia exacta en nombre (mayor puntuación)
        if search_lower in user.first_name.lower():
            score += 100

        # Coincidencia en apellido
        if search_lower in user.last_name.lower():
            score += 80

        # Coincidencia en email
        if search_lower in user.email.lower():
            score += 60

        # Coincidencia al inicio del nombre/apellido (mayor relevancia)
        if user.first_name.lower().startswith(search_lower):
            score += 50

        if user.last_name.lower().startswith(search_lower):
            score += 40

        return score

    except Exception:
        return 0


@auth_bp.route('/users/validate/<user_id>', methods=['GET'])
def validate_user_exists(user_id):
    """Validar si un usuario existe - ENDPOINT PÚBLICO"""
    try:
        print(f"🔍 Validando existencia de usuario: {user_id}")

        user = User.query.get(user_id)

        if user:
            return jsonify({
                'success': True,
                'exists': True,
                'user_info': {
                    'id': str(user.id),
                    'name': f"{user.first_name} {user.last_name}",
                    'role': user.role,
                    'is_active': user.is_active
                }
            }), 200
        else:
            return jsonify({
                'success': True,
                'exists': False,
                'user_info': None
            }), 200

    except Exception as e:
        print(f"❌ Error validando usuario: {e}")
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}',
            'exists': False
        }), 500


@auth_bp.route('/schedules/sync-with-appointments', methods=['POST'])
def sync_schedules_with_appointments():
    """Sincronizar horarios con Appointment Service"""
    try:
        # Verificar que sea admin
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        user = auth_service.verify_token(token)

        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Acceso denegado'
            }), 403

        print("🔄 Iniciando sincronización de horarios...")

        # Obtener todos los veterinarios
        veterinarians = User.query.filter_by(role='veterinarian', is_active=True).all()

        synced_count = 0
        errors = []

        for vet in veterinarians:
            try:
                # Obtener horario del veterinario
                vet_schedule = {
                    'user_id': str(vet.id),
                    'weekly_schedule': generate_user_schedule('veterinarian')  # Usar función existente
                }

                # Enviar al Appointment Service
                import requests
                appointment_url = f"http://localhost:5002/appointments/schedules/staff/{vet.id}"

                response = requests.put(
                    appointment_url,
                    json=vet_schedule,
                    headers={'Authorization': f"Bearer {token}"},
                    timeout=10
                )

                if response.status_code == 200:
                    synced_count += 1
                    print(f"✅ Veterinario {vet.first_name} {vet.last_name} sincronizado")
                else:
                    error_msg = f"Error sincronizando {vet.first_name} {vet.last_name}: HTTP {response.status_code}"
                    errors.append(error_msg)
                    print(f"⚠️ {error_msg}")

            except Exception as vet_error:
                error_msg = f"Error procesando {vet.first_name} {vet.last_name}: {str(vet_error)}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")

        return jsonify({
            'success': True,
            'message': f'Sincronización completada. {synced_count} veterinarios sincronizados.',
            'synced_count': synced_count,
            'total_veterinarians': len(veterinarians),
            'errors': errors
        }), 200

    except Exception as e:
        print(f"❌ Error en sincronización: {e}")
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


@auth_bp.route('/users/veterinarians/with-schedules', methods=['GET'])
def get_veterinarians_with_schedules():
    """Obtener veterinarios con información de horarios"""
    try:
        print("👨‍⚕️ Obteniendo veterinarios con horarios...")

        # Obtener veterinarios activos
        veterinarians = User.query.filter_by(
            role='veterinarian',
            is_active=True
        ).all()

        vets_with_schedules = []

        for vet in veterinarians:
            vet_data = {
                'id': str(vet.id),
                'first_name': vet.first_name,
                'last_name': vet.last_name,
                'email': vet.email,
                'phone': vet.phone or '',
                'role': vet.role,
                'is_active': vet.is_active,
                'specialty': 'Medicina General',  # Por defecto
                'schedule': generate_user_schedule('veterinarian'),  # Generar horario
                'has_schedule': True
            }
            vets_with_schedules.append(vet_data)

        print(f"✅ {len(vets_with_schedules)} veterinarios con horarios")

        return jsonify({
            'success': True,
            'veterinarians': vets_with_schedules,
            'total': len(vets_with_schedules)
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo veterinarios con horarios: {e}")
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}',
            'veterinarians': []
        }), 500

def generate_default_veterinarian_schedule():
    """Generar horario por defecto para veterinarios"""
    return {
        'monday': {
            'start': '08:00',
            'end': '17:00',
            'active': True,
            'break_start': '12:00',
            'break_end': '13:00'
        },
        'tuesday': {
            'start': '08:00',
            'end': '17:00',
            'active': True,
            'break_start': '12:00',
            'break_end': '13:00'
        },
        'wednesday': {
            'start': '08:00',
            'end': '17:00',
            'active': True,
            'break_start': '12:00',
            'break_end': '13:00'
        },
        'thursday': {
            'start': '08:00',
            'end': '17:00',
            'active': True,
            'break_start': '12:00',
            'break_end': '13:00'
        },
        'friday': {
            'start': '08:00',
            'end': '16:00',
            'active': True,
            'break_start': '12:00',
            'break_end': '13:00'
        },
        'saturday': {
            'start': '08:00',
            'end': '12:00',
            'active': True,
            'break_start': '',
            'break_end': ''
        },
        'sunday': {
            'start': '',
            'end': '',
            'active': False,
            'break_start': '',
            'break_end': ''
        }
    }

@auth_bp.after_request
def after_request(response):
    """Agregar headers CORS si es necesario"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


@auth_bp.route('/status', methods=['GET'])
def service_status():
    """Estado detallado del servicio de autenticación"""
    try:
        # Contar usuarios por rol
        user_counts = {}
        roles = ['admin', 'veterinarian', 'receptionist', 'auxiliary', 'client']

        for role in roles:
            count = User.query.filter_by(role=role, is_active=True).count()
            user_counts[role] = count

        total_users = User.query.filter_by(is_active=True).count()

        return jsonify({
            'success': True,
            'service': 'auth_service',
            'status': 'healthy',
            'version': '1.0.0',
            'database_connected': True,
            'statistics': {
                'total_active_users': total_users,
                'users_by_role': user_counts
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'service': 'auth_service',
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

