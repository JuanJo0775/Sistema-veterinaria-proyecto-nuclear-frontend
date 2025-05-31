# microservices/appointment_service/app/routes/appointment_routes.py
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from ..models.appointment import Appointment
from ..models.schedule import VeterinarianSchedule
from .. import db
from ..services.appointment_service import AppointmentService

appointment_bp = Blueprint('appointments', __name__)
appointment_service = AppointmentService()


@appointment_bp.route('/create', methods=['POST'])
def create_appointment():
    try:
        data = request.get_json()

        # Validaciones básicas
        required_fields = ['pet_id', 'veterinarian_id', 'client_id', 'appointment_date', 'appointment_time']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        # Validar disponibilidad
        if not appointment_service.check_availability(
                data.get('veterinarian_id'),
                data.get('appointment_date'),
                data.get('appointment_time')
        ):
            return jsonify({
                'success': False,
                'message': 'Horario no disponible'
            }), 400

        appointment = appointment_service.create_appointment(data)

        # Notificar al recepcionista (llamada asíncrona)
        appointment_service.notify_new_appointment(appointment.id)

        return jsonify({
            'success': True,
            'appointment_id': str(appointment.id),
            'message': 'Cita creada exitosamente',
            'appointment': appointment.to_dict()
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/schedules', methods=['POST'])
def create_schedule():
    """Crear horario para veterinario"""
    try:
        data = request.get_json()

        # Validaciones básicas
        required_fields = ['veterinarian_id', 'day_of_week', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        # Validar day_of_week
        day_of_week = data.get('day_of_week')
        if not isinstance(day_of_week, int) or day_of_week < 0 or day_of_week > 6:
            return jsonify({
                'success': False,
                'message': 'day_of_week debe ser un entero entre 0 (Lunes) y 6 (Domingo)'
            }), 400

        # Verificar si ya existe un horario para ese día
        existing_schedule = VeterinarianSchedule.query.filter_by(
            veterinarian_id=data.get('veterinarian_id'),
            day_of_week=day_of_week
        ).first()

        if existing_schedule:
            return jsonify({
                'success': False,
                'message': 'Ya existe un horario para ese día'
            }), 400

        # Convertir horarios a objetos time
        try:
            start_time = datetime.strptime(data.get('start_time'), '%H:%M').time()
            end_time = datetime.strptime(data.get('end_time'), '%H:%M').time()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Formato de hora inválido. Use HH:MM'
            }), 400

        # Validar que start_time sea menor que end_time
        if start_time >= end_time:
            return jsonify({
                'success': False,
                'message': 'La hora de inicio debe ser menor que la hora de fin'
            }), 400

        # Crear nuevo horario
        schedule = VeterinarianSchedule(
            veterinarian_id=data.get('veterinarian_id'),
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            is_available=data.get('is_available', True)
        )

        db.session.add(schedule)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Horario creado exitosamente',
            'schedule': schedule.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


@appointment_bp.route('/schedules/<vet_id>', methods=['GET'])
def get_veterinarian_schedules(vet_id):
    """Obtener horarios de un veterinario"""
    try:
        schedules = VeterinarianSchedule.get_by_veterinarian(vet_id)

        return jsonify({
            'success': True,
            'schedules': [schedule.to_dict() for schedule in schedules],
            'veterinarian_id': vet_id
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/schedules', methods=['GET'])
def get_all_schedules():
    """Obtener todos los horarios"""
    try:
        schedules = VeterinarianSchedule.query.filter_by(is_available=True).all()

        return jsonify({
            'success': True,
            'schedules': [schedule.to_dict() for schedule in schedules],
            'total': len(schedules)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/schedules/<schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    """Actualizar horario"""
    try:
        data = request.get_json()

        schedule = VeterinarianSchedule.query.get(schedule_id)
        if not schedule:
            return jsonify({
                'success': False,
                'message': 'Horario no encontrado'
            }), 404

        # Actualizar campos permitidos
        if 'start_time' in data:
            try:
                schedule.start_time = datetime.strptime(data['start_time'], '%H:%M').time()
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Formato de hora inválido para start_time. Use HH:MM'
                }), 400

        if 'end_time' in data:
            try:
                schedule.end_time = datetime.strptime(data['end_time'], '%H:%M').time()
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Formato de hora inválido para end_time. Use HH:MM'
                }), 400

        if 'is_available' in data:
            schedule.is_available = data['is_available']

        # Validar que start_time sea menor que end_time
        if schedule.start_time >= schedule.end_time:
            return jsonify({
                'success': False,
                'message': 'La hora de inicio debe ser menor que la hora de fin'
            }), 400

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Horario actualizado exitosamente',
            'schedule': schedule.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


@appointment_bp.route('/schedules/<schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """Eliminar/desactivar horario"""
    try:
        schedule = VeterinarianSchedule.query.get(schedule_id)
        if not schedule:
            return jsonify({
                'success': False,
                'message': 'Horario no encontrado'
            }), 404

        # En lugar de eliminar, desactivar
        schedule.is_available = False
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Horario desactivado exitosamente'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500



@appointment_bp.route('/available-slots', methods=['GET'])
def get_available_slots():
    try:
        veterinarian_id = request.args.get('veterinarian_id')
        date = request.args.get('date')

        if not veterinarian_id or not date:
            return jsonify({
                'success': False,
                'message': 'Parámetros requeridos: veterinarian_id, date'
            }), 400

        slots = appointment_service.get_available_slots(veterinarian_id, date)

        return jsonify({
            'success': True,
            'available_slots': slots,
            'date': date,
            'veterinarian_id': veterinarian_id
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/by-veterinarian/<vet_id>', methods=['GET'])
def get_appointments_by_vet(vet_id):
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        appointments = appointment_service.get_appointments_by_veterinarian(
            vet_id, start_date, end_date
        )

        return jsonify({
            'success': True,
            'appointments': appointments,
            'veterinarian_id': vet_id
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/by-client/<client_id>', methods=['GET'])
def get_appointments_by_client(client_id):
    try:
        status = request.args.get('status')

        appointments = appointment_service.get_appointments_by_client(client_id, status)

        return jsonify({
            'success': True,
            'appointments': appointments,
            'client_id': client_id
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/update/<appointment_id>', methods=['PUT'])
def update_appointment(appointment_id):
    try:
        data = request.get_json()

        appointment = appointment_service.update_appointment(appointment_id, data)

        if appointment:
            return jsonify({
                'success': True,
                'message': 'Cita actualizada exitosamente',
                'appointment': appointment.to_dict()
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Cita no encontrada'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/cancel/<appointment_id>', methods=['PUT'])
def cancel_appointment(appointment_id):
    try:
        appointment = appointment_service.cancel_appointment(appointment_id)

        if appointment:
            return jsonify({
                'success': True,
                'message': 'Cita cancelada exitosamente',
                'appointment': appointment.to_dict()
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Cita no encontrada'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/confirm/<appointment_id>', methods=['PUT'])
def confirm_appointment(appointment_id):
    try:
        appointment = appointment_service.confirm_appointment(appointment_id)

        if appointment:
            return jsonify({
                'success': True,
                'message': 'Cita confirmada exitosamente',
                'appointment': appointment.to_dict()
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Cita no encontrada'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/complete/<appointment_id>', methods=['PUT'])
def complete_appointment(appointment_id):
    try:
        appointment = appointment_service.complete_appointment(appointment_id)

        if appointment:
            return jsonify({
                'success': True,
                'message': 'Cita marcada como completada',
                'appointment': appointment.to_dict()
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Cita no encontrada'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/today', methods=['GET'])
def get_today_appointments():
    try:
        today = datetime.now().date()
        appointments = Appointment.query.filter(
            Appointment.appointment_date == today,
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).order_by(Appointment.appointment_time).all()

        return jsonify({
            'success': True,
            'appointments': [apt.to_dict() for apt in appointments],
            'date': today.isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'appointment_service'
    }), 200