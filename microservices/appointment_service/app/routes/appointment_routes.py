# microservices/appointment_service/app/routes/appointment_routes.py
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from ..models.appointment import Appointment, db
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
            'appointment_id': appointment.id,
            'message': 'Cita creada exitosamente',
            'appointment': appointment.to_dict()
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
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