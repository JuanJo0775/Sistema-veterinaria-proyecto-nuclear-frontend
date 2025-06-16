# microservices/appointment_service/app/routes/appointment_routes.py
import json
import uuid

from flask import Blueprint, request, jsonify, current_app, Response
from datetime import datetime, timedelta

from flask_jwt_extended import jwt_required, get_jwt_identity

from ..models.appointment import Appointment
from ..models.schedule import VeterinarianSchedule
from .. import db
from ..services.appointment_service import AppointmentService
import requests


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
def create_schedule_fixed():
    """Crear horario para veterinario - VERSIÓN CORREGIDA PARA UUID"""
    try:
        data = request.get_json()
        print(f"📝 Creando horario: {data}")

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
                'message': 'day_of_week debe ser un entero entre 0 (Domingo) y 6 (Sábado)'
            }), 400

        # CONVERSIÓN CORRECTA DE UUID
        veterinarian_id = str(data.get('veterinarian_id'))

        # Verificar si ya existe un horario para ese día
        existing_schedule = VeterinarianSchedule.query.filter_by(
            veterinarian_id=veterinarian_id,
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
            veterinarian_id=veterinarian_id,  # Ya convertido a string
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            is_available=data.get('is_available', True)
        )

        db.session.add(schedule)
        db.session.commit()

        # RESPUESTA CON UUID CONVERTIDOS
        response_data = {
            'id': str(schedule.id),
            'veterinarian_id': str(schedule.veterinarian_id),
            'day_of_week': schedule.day_of_week,
            'start_time': schedule.start_time.strftime('%H:%M'),
            'end_time': schedule.end_time.strftime('%H:%M'),
            'is_available': schedule.is_available,
            'day_name': get_day_name(schedule.day_of_week)
        }

        return jsonify({
            'success': True,
            'message': 'Horario creado exitosamente',
            'schedule': response_data
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creando horario: {e}")
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


# =============== RUTAS FALTANTES PARA APPOINTMENT SERVICE ===============

@appointment_bp.route('/appointments', methods=['GET'])
def get_all_appointments():
    """Obtener todas las citas con filtros opcionales"""
    try:
        # Parámetros de filtro
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        veterinarian_id = request.args.get('veterinarian_id')
        client_id = request.args.get('client_id')
        status = request.args.get('status')
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', type=int, default=0)

        # Construir query base
        query = Appointment.query

        # Aplicar filtros
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(Appointment.appointment_date >= start_date_obj)
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Formato de fecha inválido para start_date. Use YYYY-MM-DD'
                }), 400

        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(Appointment.appointment_date <= end_date_obj)
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Formato de fecha inválido para end_date. Use YYYY-MM-DD'
                }), 400

        if veterinarian_id:
            query = query.filter(Appointment.veterinarian_id == veterinarian_id)

        if client_id:
            query = query.filter(Appointment.client_id == client_id)

        if status:
            query = query.filter(Appointment.status == status)

        # Ordenar por fecha y hora más recientes
        query = query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())

        # Aplicar paginación si se especifica
        if limit:
            query = query.offset(offset).limit(limit)

        appointments = query.all()

        return jsonify({
            'success': True,
            'appointments': [appointment.to_dict() for appointment in appointments],
            'total': len(appointments),
            'filters_applied': {
                'start_date': start_date,
                'end_date': end_date,
                'veterinarian_id': veterinarian_id,
                'client_id': client_id,
                'status': status
            }
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo citas: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/appointments/<appointment_id>', methods=['GET'])
def get_appointment_by_id(appointment_id):
    """Obtener cita específica por ID"""
    try:
        appointment = Appointment.query.get(appointment_id)

        if not appointment:
            return jsonify({
                'success': False,
                'message': 'Cita no encontrada'
            }), 404

        return jsonify({
            'success': True,
            'appointment': appointment.to_dict()
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo cita: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/appointments/<appointment_id>', methods=['DELETE'])
def delete_appointment(appointment_id):
    """Eliminar cita definitivamente"""
    try:
        appointment = Appointment.query.get(appointment_id)

        if not appointment:
            return jsonify({
                'success': False,
                'message': 'Cita no encontrada'
            }), 404

        # Guardar información para el log
        appointment_info = f"Cita de {appointment.appointment_date} a las {appointment.appointment_time}"

        # Eliminar de la base de datos
        db.session.delete(appointment)
        db.session.commit()

        print(f"🗑️ Cita eliminada: {appointment_info}")

        return jsonify({
            'success': True,
            'message': f'Cita eliminada exitosamente: {appointment_info}'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error eliminando cita: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/appointments/search', methods=['GET'])
def search_appointments():
    """Buscar citas por múltiples criterios"""
    try:
        search_term = request.args.get('q', '')

        if not search_term:
            return jsonify({
                'success': False,
                'message': 'Parámetro de búsqueda requerido'
            }), 400

        # Buscar en múltiples campos (esto requiere un JOIN con datos de usuario/mascota)
        # Por ahora buscaremos en los campos disponibles
        appointments = Appointment.query.filter(
            db.or_(
                Appointment.reason.ilike(f'%{search_term}%'),
                Appointment.notes.ilike(f'%{search_term}%'),
                # Aquí se podrían agregar más campos con JOINs
            )
        ).order_by(Appointment.appointment_date.desc()).all()

        return jsonify({
            'success': True,
            'appointments': [appointment.to_dict() for appointment in appointments],
            'total': len(appointments),
            'search_term': search_term
        }), 200

    except Exception as e:
        print(f"❌ Error buscando citas: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/appointments/statistics', methods=['GET'])
def get_appointments_statistics():
    """Obtener estadísticas detalladas de citas"""
    try:
        from datetime import datetime, timedelta

        # Estadísticas básicas
        total_appointments = Appointment.query.count()

        # Citas de hoy
        today = datetime.now().date()
        appointments_today = Appointment.query.filter(
            Appointment.appointment_date == today
        ).count()

        # Citas de esta semana
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        appointments_this_week = Appointment.query.filter(
            Appointment.appointment_date >= week_start,
            Appointment.appointment_date <= week_end
        ).count()

        # Citas de este mes
        month_start = today.replace(day=1)
        appointments_this_month = Appointment.query.filter(
            Appointment.appointment_date >= month_start,
            Appointment.appointment_date <= today
        ).count()

        # Por estado
        scheduled_count = Appointment.query.filter_by(status='scheduled').count()
        confirmed_count = Appointment.query.filter_by(status='confirmed').count()
        completed_count = Appointment.query.filter_by(status='completed').count()
        cancelled_count = Appointment.query.filter_by(status='cancelled').count()

        # Próximas citas (próximos 7 días)
        next_week = today + timedelta(days=7)
        upcoming_appointments = Appointment.query.filter(
            Appointment.appointment_date > today,
            Appointment.appointment_date <= next_week,
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).count()

        return jsonify({
            'success': True,
            'statistics': {
                'total_appointments': total_appointments,
                'appointments_today': appointments_today,
                'appointments_this_week': appointments_this_week,
                'appointments_this_month': appointments_this_month,
                'upcoming_appointments': upcoming_appointments,
                'by_status': {
                    'scheduled': scheduled_count,
                    'confirmed': confirmed_count,
                    'completed': completed_count,
                    'cancelled': cancelled_count
                },
                'completion_rate': (completed_count / total_appointments * 100) if total_appointments > 0 else 0,
                'cancellation_rate': (cancelled_count / total_appointments * 100) if total_appointments > 0 else 0
            }
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/appointments/upcoming', methods=['GET'])
def get_upcoming_appointments():
    """Obtener próximas citas"""
    try:
        days_ahead = request.args.get('days', 7, type=int)
        limit = request.args.get('limit', type=int)

        # Calcular fechas
        today = datetime.now().date()
        end_date = today + timedelta(days=days_ahead)

        # Construir query
        query = Appointment.query.filter(
            Appointment.appointment_date > today,
            Appointment.appointment_date <= end_date,
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).order_by(Appointment.appointment_date, Appointment.appointment_time)

        if limit:
            query = query.limit(limit)

        appointments = query.all()

        return jsonify({
            'success': True,
            'appointments': [appointment.to_dict() for appointment in appointments],
            'total': len(appointments),
            'date_range': {
                'start': today.isoformat(),
                'end': end_date.isoformat(),
                'days_ahead': days_ahead
            }
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo próximas citas: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/appointments/by-date/<date_string>', methods=['GET'])
def get_appointments_by_date(date_string):
    """Obtener citas de una fecha específica"""
    try:
        # Convertir string a fecha
        try:
            appointment_date = datetime.strptime(date_string, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Formato de fecha inválido. Use YYYY-MM-DD'
            }), 400

        # Obtener citas de esa fecha
        appointments = Appointment.query.filter(
            Appointment.appointment_date == appointment_date
        ).order_by(Appointment.appointment_time).all()

        return jsonify({
            'success': True,
            'appointments': [appointment.to_dict() for appointment in appointments],
            'total': len(appointments),
            'date': date_string
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo citas por fecha: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/appointments/by-status/<status>', methods=['GET'])
def get_appointments_by_status(status):
    """Obtener citas por estado"""
    try:
        # Validar estado
        valid_statuses = ['scheduled', 'confirmed', 'completed', 'cancelled']
        if status not in valid_statuses:
            return jsonify({
                'success': False,
                'message': f'Estado inválido. Estados válidos: {", ".join(valid_statuses)}'
            }), 400

        appointments = Appointment.query.filter_by(
            status=status
        ).order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()

        return jsonify({
            'success': True,
            'appointments': [appointment.to_dict() for appointment in appointments],
            'total': len(appointments),
            'status': status
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo citas por estado: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/appointments/weekly-schedule', methods=['GET'])
def get_weekly_schedule():
    """Obtener horario semanal de citas"""
    try:
        # Parámetros opcionales
        week_offset = request.args.get('week_offset', 0, type=int)  # 0 = esta semana, 1 = próxima, -1 = anterior
        veterinarian_id = request.args.get('veterinarian_id')

        # Calcular fechas de la semana
        today = datetime.now().date()
        days_to_monday = today.weekday()
        monday = today - timedelta(days=days_to_monday) + timedelta(weeks=week_offset)
        sunday = monday + timedelta(days=6)

        # Construir query
        query = Appointment.query.filter(
            Appointment.appointment_date >= monday,
            Appointment.appointment_date <= sunday
        )

        if veterinarian_id:
            query = query.filter(Appointment.veterinarian_id == veterinarian_id)

        appointments = query.order_by(
            Appointment.appointment_date,
            Appointment.appointment_time
        ).all()

        # Organizar por días de la semana
        weekly_schedule = {}
        for i in range(7):
            day_date = monday + timedelta(days=i)
            day_name = day_date.strftime('%A').lower()
            weekly_schedule[day_name] = {
                'date': day_date.isoformat(),
                'appointments': []
            }

        # Llenar con citas
        for appointment in appointments:
            day_name = appointment.appointment_date.strftime('%A').lower()
            if day_name in weekly_schedule:
                weekly_schedule[day_name]['appointments'].append(appointment.to_dict())

        return jsonify({
            'success': True,
            'weekly_schedule': weekly_schedule,
            'week_info': {
                'monday': monday.isoformat(),
                'sunday': sunday.isoformat(),
                'week_offset': week_offset,
                'total_appointments': len(appointments)
            }
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo horario semanal: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/appointments/conflicts', methods=['GET'])
def check_appointment_conflicts():
    """Verificar conflictos de horarios"""
    try:
        veterinarian_id = request.args.get('veterinarian_id')
        appointment_date = request.args.get('appointment_date')
        appointment_time = request.args.get('appointment_time')
        exclude_appointment_id = request.args.get('exclude_appointment_id')  # Para ediciones

        if not all([veterinarian_id, appointment_date, appointment_time]):
            return jsonify({
                'success': False,
                'message': 'Parámetros requeridos: veterinarian_id, appointment_date, appointment_time'
            }), 400

        # Convertir fecha y hora
        try:
            date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            time_obj = datetime.strptime(appointment_time, '%H:%M').time()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Formato de fecha/hora inválido'
            }), 400

        # Buscar conflictos
        query = Appointment.query.filter(
            Appointment.veterinarian_id == veterinarian_id,
            Appointment.appointment_date == date_obj,
            Appointment.appointment_time == time_obj,
            Appointment.status.in_(['scheduled', 'confirmed'])
        )

        # Excluir cita específica si se está editando
        if exclude_appointment_id:
            query = query.filter(Appointment.id != exclude_appointment_id)

        conflicting_appointments = query.all()

        has_conflict = len(conflicting_appointments) > 0

        return jsonify({
            'success': True,
            'has_conflict': has_conflict,
            'conflicting_appointments': [apt.to_dict() for apt in conflicting_appointments],
            'checked_slot': {
                'veterinarian_id': veterinarian_id,
                'date': appointment_date,
                'time': appointment_time
            }
        }), 200

    except Exception as e:
        print(f"❌ Error verificando conflictos: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/appointments/bulk-update', methods=['PUT'])
def bulk_update_appointments():
    """Actualizar múltiples citas en lote"""
    try:
        data = request.get_json()
        appointment_ids = data.get('appointment_ids', [])
        updates = data.get('updates', {})

        if not appointment_ids:
            return jsonify({
                'success': False,
                'message': 'Lista de IDs de citas requerida'
            }), 400

        if not updates:
            return jsonify({
                'success': False,
                'message': 'Datos de actualización requeridos'
            }), 400

        # Campos permitidos para actualización en lote
        allowed_fields = ['status', 'notes']
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}

        if not filtered_updates:
            return jsonify({
                'success': False,
                'message': f'Campos de actualización inválidos. Permitidos: {", ".join(allowed_fields)}'
            }), 400

        # Actualizar citas
        updated_appointments = []
        for appointment_id in appointment_ids:
            appointment = Appointment.query.get(appointment_id)
            if appointment:
                for field, value in filtered_updates.items():
                    setattr(appointment, field, value)

                appointment.updated_at = datetime.utcnow()
                updated_appointments.append(appointment.to_dict())

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{len(updated_appointments)} citas actualizadas exitosamente',
            'updated_appointments': updated_appointments,
            'applied_updates': filtered_updates
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error en actualización en lote: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/appointments/reports/veterinarian/<vet_id>', methods=['GET'])
def get_veterinarian_appointment_report(vet_id):
    """Generar reporte de citas por veterinario"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Query base
        query = Appointment.query.filter_by(veterinarian_id=vet_id)

        # Aplicar filtros de fecha
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Appointment.appointment_date >= start_date_obj)

        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Appointment.appointment_date <= end_date_obj)

        appointments = query.order_by(
            Appointment.appointment_date.desc(),
            Appointment.appointment_time.desc()
        ).all()

        # Calcular estadísticas
        total_appointments = len(appointments)
        completed_appointments = len([a for a in appointments if a.status == 'completed'])
        cancelled_appointments = len([a for a in appointments if a.status == 'cancelled'])

        # Agrupar por fecha
        appointments_by_date = {}
        for appointment in appointments:
            date_str = appointment.appointment_date.isoformat()
            if date_str not in appointments_by_date:
                appointments_by_date[date_str] = []
            appointments_by_date[date_str].append(appointment.to_dict())

        return jsonify({
            'success': True,
            'report': {
                'veterinarian_id': vet_id,
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'statistics': {
                    'total_appointments': total_appointments,
                    'completed_appointments': completed_appointments,
                    'cancelled_appointments': cancelled_appointments,
                    'completion_rate': (
                                completed_appointments / total_appointments * 100) if total_appointments > 0 else 0,
                    'cancellation_rate': (
                                cancelled_appointments / total_appointments * 100) if total_appointments > 0 else 0
                },
                'appointments_by_date': appointments_by_date,
                'all_appointments': [appointment.to_dict() for appointment in appointments]
            }
        }), 200

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': 'Formato de fecha inválido. Use YYYY-MM-DD'
        }), 400
    except Exception as e:
        print(f"❌ Error generando reporte: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/schedules/staff', methods=['GET'])
def get_all_staff_schedules():
    """Obtener todos los horarios del personal desde Auth Service"""
    try:
        # Este endpoint actúa como proxy al Auth Service
        auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/schedules"

        # Reenviar la petición al Auth Service
        headers = {}
        if request.headers.get('Authorization'):
            headers['Authorization'] = request.headers.get('Authorization')

        response = requests.get(auth_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
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
        print(f"❌ Error en get_all_staff_schedules: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/schedules/staff/<user_id>', methods=['PUT'])
def update_staff_schedule(user_id):
    """Actualizar horario de un usuario específico vía Auth Service"""
    try:
        # Actuar como proxy al Auth Service
        auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/schedules/{user_id}"

        # Reenviar la petición con los datos
        headers = {'Content-Type': 'application/json'}
        if request.headers.get('Authorization'):
            headers['Authorization'] = request.headers.get('Authorization')

        data = request.get_json()
        response = requests.put(auth_url, json=data, headers=headers, timeout=10)

        if response.status_code == 200:
            response_data = response.json()

            # IMPORTANTE: Después de actualizar horarios, sincronizar con VeterinarianSchedule
            if response_data.get('success'):
                sync_veterinarian_schedules(user_id, data.get('weekly_schedule', {}))

            return jsonify(response_data)
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
        print(f"❌ Error en update_staff_schedule: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


def sync_veterinarian_schedules(user_id, weekly_schedule):
    """Sincronizar horarios con la tabla veterinarian_schedules - VERSIÓN CORREGIDA"""
    try:
        print(f"🔄 Iniciando sincronización para usuario: {user_id}")

        # ESTRATEGIA 1: Intentar endpoint interno sin autenticación
        auth_internal_url = f"{current_app.config.get('AUTH_SERVICE_URL', 'http://localhost:5001')}/auth/users/{user_id}/internal"

        user_role = None

        try:
            print(f"📡 Consultando rol de usuario en: {auth_internal_url}")
            response = requests.get(auth_internal_url, timeout=5)

            if response.status_code == 200:
                user_data = response.json()
                if user_data.get('success'):
                    user_role = user_data.get('user', {}).get('role')
                    print(f"✅ Rol obtenido: {user_role}")
                else:
                    print(f"❌ Error en respuesta: {user_data.get('message')}")
            else:
                print(f"⚠️ Error HTTP obteniendo usuario: {response.status_code}")

        except requests.RequestException as req_error:
            print(f"⚠️ Error de conexión obteniendo usuario: {req_error}")

        # ESTRATEGIA 2: Si falla, verificar directamente en la base de datos
        if not user_role:
            print("🔄 Intentando verificación directa en base de datos...")
            try:
                # Hacer una consulta directa a la base de datos del Auth Service
                # Nota: Esto requiere acceso a la misma base de datos
                from sqlalchemy import create_engine, text
                import os

                # Usar la misma configuración de base de datos
                db_url = os.environ.get('DATABASE_URL') or \
                         f"postgresql://{os.environ.get('POSTGRES_USER', 'postgres')}:{os.environ.get('POSTGRES_PASSWORD', 'bocato0731')}@{os.environ.get('POSTGRES_HOST', 'localhost')}:{os.environ.get('POSTGRES_PORT', '5432')}/{os.environ.get('POSTGRES_DB', 'veterinary-system')}"

                engine = create_engine(db_url)
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT role FROM users WHERE id = :user_id"), {"user_id": user_id})
                    row = result.fetchone()
                    if row:
                        user_role = row[0]
                        print(f"✅ Rol obtenido desde DB directa: {user_role}")
                    else:
                        print(f"❌ Usuario {user_id} no encontrado en DB")

            except Exception as db_error:
                print(f"⚠️ Error consultando DB directamente: {db_error}")

        # ESTRATEGIA 3: Si es un horario con muchos días activos, asumir que es veterinario
        if not user_role:
            active_days = sum(1 for day_data in weekly_schedule.values() if day_data.get('active'))
            if active_days >= 5:  # Si tiene 5 o más días activos, probablemente es veterinario
                user_role = 'veterinarian'
                print(f"🤔 Asumiendo rol 'veterinarian' basado en {active_days} días activos")

        # Solo proceder si es veterinario
        if user_role == 'veterinarian':
            print(f"👨‍⚕️ Confirmado: Usuario {user_id} es veterinario, sincronizando horarios...")

            # Eliminar horarios existentes del veterinario
            try:
                deleted_count = VeterinarianSchedule.query.filter_by(veterinarian_id=user_id).delete()
                print(f"🗑️ Eliminados {deleted_count} horarios existentes")
            except Exception as delete_error:
                print(f"⚠️ Error eliminando horarios existentes: {delete_error}")
                db.session.rollback()
                return

            # Crear nuevos horarios basados en weekly_schedule
            day_mapping = {
                'monday': 1, 'tuesday': 2, 'wednesday': 3, 'thursday': 4,
                'friday': 5, 'saturday': 6, 'sunday': 0
            }

            created_schedules = 0

            for day_name, day_data in weekly_schedule.items():
                if day_data.get('active') and day_data.get('start') and day_data.get('end'):
                    try:
                        # Validar formato de hora
                        start_time = datetime.strptime(day_data['start'], '%H:%M').time()
                        end_time = datetime.strptime(day_data['end'], '%H:%M').time()

                        # Validar que start < end
                        if start_time >= end_time:
                            print(f"⚠️ Horario inválido para {day_name}: {day_data['start']} >= {day_data['end']}")
                            continue

                        schedule = VeterinarianSchedule(
                            veterinarian_id=user_id,
                            day_of_week=day_mapping.get(day_name, 0),
                            start_time=start_time,
                            end_time=end_time,
                            is_available=True
                        )

                        db.session.add(schedule)
                        created_schedules += 1
                        print(f"✅ Horario agregado: {day_name} {day_data['start']}-{day_data['end']}")

                    except ValueError as time_error:
                        print(f"⚠️ Error de formato de hora para {day_name}: {time_error}")
                        continue
                    except Exception as day_error:
                        print(f"⚠️ Error procesando día {day_name}: {day_error}")
                        continue

            if created_schedules > 0:
                try:
                    db.session.commit()
                    print(f"✅ {created_schedules} horarios de veterinario sincronizados exitosamente para: {user_id}")

                    # Verificar que se guardaron correctamente
                    verification_count = VeterinarianSchedule.query.filter_by(veterinarian_id=user_id).count()
                    print(f"🔍 Verificación: {verification_count} horarios encontrados en la base de datos")

                except Exception as commit_error:
                    print(f"❌ Error haciendo commit: {commit_error}")
                    db.session.rollback()
                    raise commit_error
            else:
                print(f"⚠️ No se crearon horarios para el usuario {user_id}")

        elif user_role:
            print(f"ℹ️ Usuario {user_id} tiene rol '{user_role}', no es veterinario - no se sincroniza")
        else:
            print(f"⚠️ No se pudo determinar el rol del usuario {user_id}")

    except Exception as e:
        print(f"❌ Error general sincronizando horarios de veterinario: {e}")
        import traceback
        traceback.print_exc()
        try:
            db.session.rollback()
        except:
            pass

""""@appointment_bp.route('/schedules/veterinarians', methods=['GET'])
def get_veterinarian_schedules_only():
    try:
        schedules = VeterinarianSchedule.query.filter_by(is_available=True).all()

        # Agrupar por veterinario
        vet_schedules = {}
        for schedule in schedules:
            vet_id = str(schedule.veterinarian_id)
            if vet_id not in vet_schedules:
                vet_schedules[vet_id] = []
            vet_schedules[vet_id].append(schedule.to_dict())

        return jsonify({
            'success': True,
            'veterinarian_schedules': vet_schedules,
            'total_veterinarians': len(vet_schedules)
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo horarios de veterinarios: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
"""

@appointment_bp.route('/schedules/sync-all', methods=['POST'])
def sync_all_veterinarian_schedules():
    """Sincronizar todos los horarios de veterinarios desde Auth Service"""
    try:
        # Obtener todos los horarios desde Auth Service
        auth_url = f"{current_app.config['AUTH_SERVICE_URL']}/auth/schedules"
        headers = {}
        if request.headers.get('Authorization'):
            headers['Authorization'] = request.headers.get('Authorization')

        response = requests.get(auth_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('schedules'):

                synced_count = 0
                for staff in data['schedules']:
                    if staff.get('user_role') == 'veterinarian':
                        sync_veterinarian_schedules(
                            staff['user_id'],
                            staff.get('weekly_schedule', {})
                        )
                        synced_count += 1

                return jsonify({
                    'success': True,
                    'message': f'Sincronizados {synced_count} horarios de veterinarios',
                    'synced_count': synced_count
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': 'No se encontraron horarios para sincronizar'
                }), 400
        else:
            return jsonify({
                'success': False,
                'message': f'Error del Auth Service: {response.status_code}'
            }), response.status_code

    except Exception as e:
        print(f"❌ Error en sincronización masiva: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@appointment_bp.route('/schedules/veterinarians', methods=['GET'])
def get_veterinarian_schedules_grouped():
    """Obtener horarios de todos los veterinarios agrupados - ACCESO PÚBLICO"""
    try:
        # NO usar @jwt_required() para permitir acceso público

        # Obtener todos los horarios activos
        schedules = VeterinarianSchedule.query.filter_by(is_available=True).all()

        # Agrupar por veterinario
        veterinarian_schedules = {}

        for schedule in schedules:
            vet_id = schedule.veterinarian_id

            if vet_id not in veterinarian_schedules:
                veterinarian_schedules[vet_id] = []

            veterinarian_schedules[vet_id].append(schedule.to_dict())

        print(f"📋 Horarios agrupados para {len(veterinarian_schedules)} veterinarios")

        return jsonify({
            'success': True,
            'veterinarian_schedules': veterinarian_schedules,
            'total_veterinarians': len(veterinarian_schedules),
            'total_schedules': len(schedules)
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo horarios agrupados: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# =============== RUTA ADICIONAL PARA HORARIOS ESPECÍFICOS DE UN VETERINARIO EN UNA FECHA ===============

@appointment_bp.route('/schedules/veterinarian/<vet_id>/date/<date>', methods=['GET'])
def get_veterinarian_schedule_by_date(vet_id, date):
    """Obtener horario de un veterinario en una fecha específica - ACCESO PÚBLICO"""
    try:
        from datetime import datetime

        # Convertir fecha a día de la semana
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            # Python: Monday=0, Sunday=6 -> Backend: Sunday=0, Saturday=6
            day_of_week = (date_obj.weekday() + 1) % 7
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Formato de fecha inválido. Use YYYY-MM-DD'
            }), 400

        # Buscar horario del veterinario para ese día
        schedule = VeterinarianSchedule.query.filter_by(
            veterinarian_id=vet_id,
            day_of_week=day_of_week,
            is_available=True
        ).first()

        if schedule:
            print(f"✅ Horario encontrado para vet {vet_id} el {date} (día {day_of_week})")
            return jsonify({
                'success': True,
                'schedule': schedule.to_dict(),
                'date': date,
                'day_of_week': day_of_week,
                'veterinarian_id': vet_id
            }), 200
        else:
            print(f"❌ No hay horario para vet {vet_id} el {date} (día {day_of_week})")
            return jsonify({
                'success': False,
                'message': 'El veterinario no atiende este día',
                'date': date,
                'day_of_week': day_of_week,
                'veterinarian_id': vet_id
            }), 404

    except Exception as e:
        print(f"❌ Error obteniendo horario específico: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== RUTA PARA OBTENER CITAS EXISTENTES DE UN VETERINARIO EN UNA FECHA ===============

@appointment_bp.route('/appointments/veterinarian/<vet_id>/date/<date>', methods=['GET'])
def get_veterinarian_appointments_by_date_corrected(vet_id, date):
    """Obtener citas de un veterinario en una fecha específica - VERSIÓN CORREGIDA"""
    try:
        print(f"📅 Obteniendo citas para veterinario {vet_id} en {date}")

        # Validar formato de fecha
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Formato de fecha inválido. Use YYYY-MM-DD'
            }), 400

        # Buscar citas del veterinario en esa fecha
        appointments = Appointment.query.filter_by(
            veterinarian_id=vet_id,
            appointment_date=date_obj
        ).filter(
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).order_by(Appointment.appointment_time).all()

        print(f"✅ {len(appointments)} citas encontradas")

        # Convertir a lista de diccionarios
        appointments_list = []
        for apt in appointments:
            appointment_dict = {
                'id': str(apt.id),
                'veterinarian_id': str(apt.veterinarian_id),
                'client_id': str(apt.client_id),
                'pet_id': str(apt.pet_id),
                'appointment_date': apt.appointment_date.isoformat(),
                'appointment_time': apt.appointment_time.strftime('%H:%M'),
                'status': apt.status,
                'reason': apt.reason or '',
                'consultation_type': apt.consultation_type or 'general'
            }
            appointments_list.append(appointment_dict)

        return jsonify({
            'success': True,
            'appointments': appointments_list,
            'total': len(appointments_list),
            'date': date,
            'veterinarian_id': vet_id
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo citas por fecha: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}',
            'appointments': []
        }), 500

# =============== RUTA PARA CREAR CITA (ACCESO CON TOKEN) ===============

""""@appointment_bp.route('/appointments/create', methods=['POST'])
@jwt_required()  # Esta SÍ requiere autenticación
def create_appointment_public():
 #Crear nueva cita desde frontend público - requiere autenticación
    try:
        current_user = get_jwt_identity()
        data = request.get_json()

        print(f"📝 Creando cita con datos: {data}")

        # Validar datos requeridos
        required_fields = ['pet_id', 'veterinarian_id', 'client_id', 'appointment_date', 'appointment_time']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        # Verificar que no haya conflicto de horario
        existing_appointment = Appointment.query.filter_by(
            veterinarian_id=data['veterinarian_id'],
            appointment_date=data['appointment_date'],
            appointment_time=data['appointment_time']
        ).filter(
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).first()

        if existing_appointment:
            return jsonify({
                'success': False,
                'message': 'Ya existe una cita en ese horario'
            }), 400

        # Crear nueva cita (ajustar campos según tu modelo)
        try:
            new_appointment = Appointment(
                pet_id=data['pet_id'],
                veterinarian_id=data['veterinarian_id'],
                client_id=data['client_id'],
                appointment_date=data['appointment_date'],
                appointment_time=data['appointment_time'],
                reason=data.get('reason', ''),
                notes=data.get('notes', ''),
                status=data.get('status', 'scheduled'),
                priority=data.get('priority', 'normal'),
                consultation_type=data.get('consultation_type', 'general')
            )

            db.session.add(new_appointment)
            db.session.commit()

            print(f"✅ Cita creada: {new_appointment.id}")

            # Convertir a diccionario para respuesta
            try:
                appointment_dict = new_appointment.to_dict()
            except:
                # Fallback si no tienes método to_dict()
                appointment_dict = {
                    'id': new_appointment.id,
                    'pet_id': new_appointment.pet_id,
                    'veterinarian_id': new_appointment.veterinarian_id,
                    'client_id': new_appointment.client_id,
                    'appointment_date': new_appointment.appointment_date,
                    'appointment_time': new_appointment.appointment_time,
                    'status': new_appointment.status,
                    'reason': new_appointment.reason
                }

            return jsonify({
                'success': True,
                'message': 'Cita creada exitosamente',
                'appointment': appointment_dict
            }), 201

        except Exception as db_error:
            db.session.rollback()
            print(f"❌ Error de base de datos: {db_error}")
            return jsonify({
                'success': False,
                'message': f'Error de base de datos: {str(db_error)}'
            }), 500

    except Exception as e:
        print(f"❌ Error creando cita: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
"""

@appointment_bp.route('/appointments/create', methods=['POST'])
def create_appointment_corrected():
    """Crear nueva cita - VERSIÓN CORREGIDA"""
    try:
        data = request.get_json()
        print(f"📝 Datos recibidos para crear cita: {data}")

        # Validaciones básicas mejoradas
        required_fields = ['pet_id', 'veterinarian_id', 'client_id', 'appointment_date', 'appointment_time']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        # Validar formato de fecha
        try:
            from datetime import datetime
            appointment_date = datetime.strptime(data.get('appointment_date'), '%Y-%m-%d').date()
            appointment_time = datetime.strptime(data.get('appointment_time'), '%H:%M').time()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Formato de fecha o hora inválido'
            }), 400

        # Verificar disponibilidad ANTES de crear
        existing_appointment = Appointment.query.filter_by(
            veterinarian_id=data.get('veterinarian_id'),
            appointment_date=appointment_date,
            appointment_time=appointment_time
        ).filter(
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).first()

        if existing_appointment:
            return jsonify({
                'success': False,
                'message': 'Ya existe una cita en ese horario. Por favor selecciona otro horario.'
            }), 400

        # Crear nueva cita
        try:
            new_appointment = Appointment(
                pet_id=data.get('pet_id'),
                veterinarian_id=data.get('veterinarian_id'),
                client_id=data.get('client_id'),
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                reason=data.get('reason', ''),
                notes=data.get('notes', ''),
                status=data.get('status', 'scheduled'),
                priority=data.get('priority', 'normal'),
                consultation_type=data.get('consultation_type', 'general'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.session.add(new_appointment)
            db.session.commit()

            print(f"✅ Cita creada exitosamente: {new_appointment.id}")

            # Convertir a diccionario para respuesta
            appointment_dict = {
                'id': str(new_appointment.id),
                'pet_id': str(new_appointment.pet_id),
                'veterinarian_id': str(new_appointment.veterinarian_id),
                'client_id': str(new_appointment.client_id),
                'appointment_date': new_appointment.appointment_date.isoformat(),
                'appointment_time': new_appointment.appointment_time.strftime('%H:%M'),
                'reason': new_appointment.reason,
                'notes': new_appointment.notes,
                'status': new_appointment.status,
                'priority': new_appointment.priority,
                'consultation_type': new_appointment.consultation_type,
                'created_at': new_appointment.created_at.isoformat(),
                'updated_at': new_appointment.updated_at.isoformat()
            }

            return jsonify({
                'success': True,
                'message': 'Cita creada exitosamente',
                'appointment': appointment_dict,
                'appointment_id': str(new_appointment.id)
            }), 201

        except Exception as db_error:
            db.session.rollback()
            print(f"❌ Error de base de datos: {db_error}")
            return jsonify({
                'success': False,
                'message': f'Error al guardar en base de datos: {str(db_error)}'
            }), 500

    except Exception as e:
        print(f"❌ Error general creando cita: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500

@appointment_bp.route('/appointments/client/<client_id>', methods=['GET'])
def get_client_appointments_corrected(client_id):
    """Obtener todas las citas de un cliente - VERSIÓN CORREGIDA"""
    try:
        print(f"📋 Obteniendo citas para cliente {client_id}")

        # Parámetros opcionales
        status = request.args.get('status')
        limit = request.args.get('limit', type=int)

        # Construir query
        query = Appointment.query.filter_by(client_id=client_id)

        if status:
            query = query.filter_by(status=status)

        # Ordenar por fecha más reciente primero
        query = query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())

        if limit:
            query = query.limit(limit)

        appointments = query.all()

        print(f"✅ {len(appointments)} citas encontradas para cliente")

        # Convertir a diccionarios
        appointments_list = []
        for apt in appointments:
            appointment_dict = {
                'id': str(apt.id),
                'pet_id': str(apt.pet_id),
                'veterinarian_id': str(apt.veterinarian_id),
                'client_id': str(apt.client_id),
                'appointment_date': apt.appointment_date.isoformat(),
                'appointment_time': apt.appointment_time.strftime('%H:%M'),
                'status': apt.status,
                'priority': apt.priority or 'normal',
                'reason': apt.reason or '',
                'notes': apt.notes or '',
                'consultation_type': apt.consultation_type or 'general',
                'created_at': apt.created_at.isoformat() if apt.created_at else None,
                'updated_at': apt.updated_at.isoformat() if apt.updated_at else None
            }
            appointments_list.append(appointment_dict)

        return jsonify({
            'success': True,
            'appointments': appointments_list,
            'total': len(appointments_list),
            'client_id': client_id
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo citas del cliente: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}',
            'appointments': []
        }), 500



# =============== 6. RUTA PARA CITAS PRÓXIMAS DE UN CLIENTE (NUEVA) ===============
""""@appointment_bp.route('/appointments/client/<client_id>/upcoming', methods=['GET'])
@jwt_required()  # Requiere autenticación
def get_client_upcoming_appointments(client_id):

    try:
        from datetime import datetime, date

        current_user = get_jwt_identity()
        today = date.today()

        # Obtener citas futuras del cliente
        appointments = Appointment.query.filter_by(client_id=client_id).filter(
            Appointment.appointment_date >= today.isoformat()
        ).filter(
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()

        print(f"📅 {len(appointments)} citas próximas para cliente {client_id}")

        # Convertir a lista
        appointments_list = []
        for apt in appointments:
            try:
                appointments_list.append(apt.to_dict())
            except:
                appointments_list.append({
                    'id': apt.id,
                    'pet_id': apt.pet_id,
                    'veterinarian_id': apt.veterinarian_id,
                    'appointment_date': apt.appointment_date,
                    'appointment_time': apt.appointment_time,
                    'status': apt.status,
                    'reason': apt.reason
                })

        return jsonify({
            'success': True,
            'appointments': appointments_list,
            'total': len(appointments_list),
            'client_id': client_id
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo citas próximas: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
        
"""

@appointment_bp.route('/appointments/client/<client_id>/upcoming', methods=['GET'])
def get_client_upcoming_appointments_corrected(client_id):
    """Obtener citas próximas de un cliente - VERSIÓN CORREGIDA"""
    try:
        from datetime import datetime, date

        print(f"📅 Obteniendo citas próximas para cliente {client_id}")

        today = date.today()
        days_ahead = request.args.get('days', 30, type=int)  # Próximos 30 días por defecto

        # Calcular fecha límite
        from datetime import timedelta
        end_date = today + timedelta(days=days_ahead)

        # Obtener citas futuras del cliente
        appointments = Appointment.query.filter_by(client_id=client_id).filter(
            Appointment.appointment_date >= today,
            Appointment.appointment_date <= end_date
        ).filter(
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()

        print(f"✅ {len(appointments)} citas próximas encontradas")

        # Convertir a diccionarios
        appointments_list = []
        for apt in appointments:
            appointment_dict = {
                'id': str(apt.id),
                'pet_id': str(apt.pet_id),
                'veterinarian_id': str(apt.veterinarian_id),
                'client_id': str(apt.client_id),
                'appointment_date': apt.appointment_date.isoformat(),
                'appointment_time': apt.appointment_time.strftime('%H:%M'),
                'status': apt.status,
                'priority': apt.priority or 'normal',
                'reason': apt.reason or '',
                'consultation_type': apt.consultation_type or 'general',
                'days_until': (apt.appointment_date - today).days
            }
            appointments_list.append(appointment_dict)

        return jsonify({
            'success': True,
            'appointments': appointments_list,
            'total': len(appointments_list),
            'client_id': client_id,
            'period': {
                'start_date': today.isoformat(),
                'end_date': end_date.isoformat(),
                'days_ahead': days_ahead
            }
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo citas próximas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}',
            'appointments': []
        }), 500

@appointment_bp.route('/appointments/available-slots', methods=['GET'])
def get_available_slots_corrected():
    """Obtener slots disponibles - VERSIÓN CORREGIDA"""
    try:
        veterinarian_id = request.args.get('veterinarian_id')
        date = request.args.get('date')

        print(f"🔍 Buscando slots para veterinario {veterinarian_id} en {date}")

        if not veterinarian_id or not date:
            return jsonify({
                'success': False,
                'message': 'Parámetros requeridos: veterinarian_id, date'
            }), 400

        # Validar formato de fecha
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            day_of_week = (date_obj.weekday() + 1) % 7  # Convertir a formato backend (0=domingo)
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Formato de fecha inválido. Use YYYY-MM-DD'
            }), 400

        # PASO 1: Verificar si el veterinario tiene horario para ese día
        vet_schedule = VeterinarianSchedule.query.filter_by(
            veterinarian_id=veterinarian_id,
            day_of_week=day_of_week,
            is_available=True
        ).first()

        if not vet_schedule:
            print(f"❌ Veterinario {veterinarian_id} no atiende los {get_day_name(day_of_week)}")
            return jsonify({
                'success': False,
                'message': f'El veterinario no atiende los {get_day_name(day_of_week)}',
                'available_slots': [],
                'date': date,
                'veterinarian_id': veterinarian_id
            })

        # PASO 2: Generar todos los slots posibles según el horario
        all_slots = generate_time_slots(
            vet_schedule.start_time.strftime('%H:%M'),
            vet_schedule.end_time.strftime('%H:%M')
        )

        # PASO 3: Obtener citas existentes para ese día
        existing_appointments = Appointment.query.filter_by(
            veterinarian_id=veterinarian_id,
            appointment_date=date_obj
        ).filter(
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).all()

        occupied_times = [apt.appointment_time.strftime('%H:%M') for apt in existing_appointments]

        # PASO 4: Filtrar slots disponibles
        available_slots = [slot for slot in all_slots if slot not in occupied_times]

        print(f"✅ {len(all_slots)} slots totales, {len(occupied_times)} ocupados, {len(available_slots)} disponibles")

        return jsonify({
            'success': True,
            'available_slots': available_slots,
            'date': date,
            'veterinarian_id': veterinarian_id,
            'schedule_info': {
                'start_time': vet_schedule.start_time.strftime('%H:%M'),
                'end_time': vet_schedule.end_time.strftime('%H:%M'),
                'day_of_week': day_of_week
            }
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo slots disponibles: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}',
            'available_slots': []
        }), 500


@appointment_bp.route('/appointments/schedules/<vet_id>', methods=['GET'])
def get_veterinarian_schedules_fixed(vet_id):
    """Obtener horarios de un veterinario - VERSIÓN CORREGIDA PARA UUID"""
    try:
        print(f"📋 Obteniendo horarios para veterinario: {vet_id}")

        schedules = VeterinarianSchedule.query.filter_by(
            veterinarian_id=vet_id,
            is_available=True
        ).all()

        schedules_list = []
        for schedule in schedules:
            schedule_dict = {
                'id': str(schedule.id),  # CONVERSIÓN UUID
                'veterinarian_id': str(schedule.veterinarian_id),  # CONVERSIÓN UUID
                'day_of_week': schedule.day_of_week,
                'start_time': schedule.start_time.strftime('%H:%M'),
                'end_time': schedule.end_time.strftime('%H:%M'),
                'is_available': schedule.is_available,
                'day_name': get_day_name(schedule.day_of_week)
            }
            schedules_list.append(schedule_dict)

        # Ordenar por día de la semana
        schedules_list.sort(key=lambda x: x['day_of_week'])

        return jsonify({
            'success': True,
            'schedules': schedules_list,
            'veterinarian_id': str(vet_id),  # CONVERSIÓN UUID
            'total': len(schedules_list)
        }), 200

    except Exception as e:
        print(f"❌ Error obteniendo horarios del veterinario: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'schedules': []
        }), 500


from flask import Response
import json
import uuid
from datetime import time, datetime

# Función segura de serialización
def safe_serialize(obj):
    if isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, (datetime, time)):
        return obj.strftime('%H:%M') if isinstance(obj, time) else obj.isoformat()
    elif isinstance(obj, dict):
        return {safe_serialize(k): safe_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_serialize(i) for i in obj]
    else:
        return obj

@appointment_bp.route('/appointments/schedules/veterinarians-v2', methods=['GET'])
def get_veterinarian_schedules_grouped_fixed_v2():

    try:
        print("📋 Obteniendo horarios agrupados de veterinarios...")

        schedules = VeterinarianSchedule.query.filter_by(is_available=True).all()
        veterinarian_schedules = {}

        for schedule in schedules:
            print(f"🧩 Schedule ID: {schedule.id} - VetID: {schedule.veterinarian_id}")

            if not schedule.veterinarian_id:
                print(f"⚠️ Horario {schedule.id} sin veterinarian_id válido, omitido")
                continue

            try:
                vet_id_str = str(schedule.veterinarian_id)
            except Exception as e:
                print(f"❌ Error al convertir vet_id a str: {e}")
                continue

            if vet_id_str not in veterinarian_schedules:
                veterinarian_schedules[vet_id_str] = []

            schedule_dict = {
                'id': schedule.id,
                'veterinarian_id': schedule.veterinarian_id,
                'day_of_week': schedule.day_of_week,
                'start_time': schedule.start_time,
                'end_time': schedule.end_time,
                'is_available': schedule.is_available,
                'day_name': get_day_name(schedule.day_of_week)
            }

            veterinarian_schedules[vet_id_str].append(schedule_dict)

        for vet_id in veterinarian_schedules:
            veterinarian_schedules[vet_id].sort(key=lambda x: x['day_of_week'])

        payload = {
            'success': True,
            'veterinarian_schedules': veterinarian_schedules,
            'total_veterinarians': len(veterinarian_schedules),
            'total_schedules': len(schedules)
        }

        print("🐛 Veterinarian schedules dict justo antes del serializado:")
        print(veterinarian_schedules)

        serialized_payload = safe_serialize(payload)

        print("✅ Payload serializado correctamente")
        return Response(
            json.dumps(serialized_payload),
            status=200,
            mimetype='application/json'
        )

    except Exception as e:
        print(f"❌ ERROR FATAL en veterinarians-v2: {e}")
        import traceback
        traceback.print_exc()

        return Response(
            json.dumps({
                'success': False,
                'message': f'Error interno: {str(e)}',
                'veterinarian_schedules': {},
                'total_veterinarians': 0,
                'total_schedules': 0
            }),
            status=500,
            mimetype='application/json'
        )



def generate_time_slots(start_time, end_time):
    """Generar slots de tiempo cada 30 minutos"""
    try:
        from datetime import datetime, timedelta

        start_dt = datetime.strptime(start_time, '%H:%M')
        end_dt = datetime.strptime(end_time, '%H:%M')

        slots = []
        current = start_dt

        while current < end_dt:
            time_str = current.strftime('%H:%M')

            # Excluir hora de almuerzo (12:00-13:00)
            if not ('12:00' <= time_str < '13:00'):
                slots.append(time_str)

            current += timedelta(minutes=30)

        return slots

    except Exception as e:
        print(f"❌ Error generando slots: {e}")
        # Fallback con horarios básicos
        return ['08:00', '08:30', '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
                '14:00', '14:30', '15:00', '15:30', '16:00', '16:30', '17:00']


def get_day_name(day_of_week):
    """Obtener nombre del día en español"""
    day_names = {
        0: 'Domingo',
        1: 'Lunes',
        2: 'Martes',
        3: 'Miércoles',
        4: 'Jueves',
        5: 'Viernes',
        6: 'Sábado'
    }
    return day_names.get(day_of_week, 'Día desconocido')

def sync_veterinarian_schedules_fixed(user_id, weekly_schedule):
    """Sincronizar horarios con la tabla veterinarian_schedules - VERSIÓN CORREGIDA"""
    try:
        print(f"🔄 Iniciando sincronización para usuario: {user_id}")

        # CONVERSIÓN EXPLÍCITA A STRING DEL UUID
        user_id_str = str(user_id)

        # Obtener rol del usuario
        try:
            auth_internal_url = f"{current_app.config.get('AUTH_SERVICE_URL', 'http://localhost:5001')}/auth/users/{user_id_str}/internal"
            response = requests.get(auth_internal_url, timeout=5)

            user_role = None
            if response.status_code == 200:
                user_data = response.json()
                if user_data.get('success'):
                    user_role = user_data.get('user', {}).get('role')
                    print(f"✅ Rol obtenido: {user_role}")

        except Exception as e:
            print(f"⚠️ Error obteniendo rol: {e}")
            user_role = None

        # Solo proceder si es veterinario
        if user_role == 'veterinarian':
            print(f"👨‍⚕️ Confirmado: Usuario {user_id_str} es veterinario, sincronizando horarios...")

            # Eliminar horarios existentes del veterinario
            try:
                deleted_count = VeterinarianSchedule.query.filter_by(veterinarian_id=user_id_str).delete()
                print(f"🗑️ Eliminados {deleted_count} horarios existentes")
            except Exception as delete_error:
                print(f"⚠️ Error eliminando horarios existentes: {delete_error}")
                db.session.rollback()
                return

            # Crear nuevos horarios basados en weekly_schedule
            day_mapping = {
                'monday': 1, 'tuesday': 2, 'wednesday': 3, 'thursday': 4,
                'friday': 5, 'saturday': 6, 'sunday': 0
            }

            created_schedules = 0

            for day_name, day_data in weekly_schedule.items():
                if day_data.get('active') and day_data.get('start') and day_data.get('end'):
                    try:
                        # Validar formato de hora
                        start_time = datetime.strptime(day_data['start'], '%H:%M').time()
                        end_time = datetime.strptime(day_data['end'], '%H:%M').time()

                        # Validar que start < end
                        if start_time >= end_time:
                            print(f"⚠️ Horario inválido para {day_name}: {day_data['start']} >= {day_data['end']}")
                            continue

                        schedule = VeterinarianSchedule(
                            veterinarian_id=user_id_str,  # UUID YA CONVERTIDO A STRING
                            day_of_week=day_mapping.get(day_name, 0),
                            start_time=start_time,
                            end_time=end_time,
                            is_available=True
                        )

                        db.session.add(schedule)
                        created_schedules += 1
                        print(f"✅ Horario agregado: {day_name} {day_data['start']}-{day_data['end']}")

                    except ValueError as time_error:
                        print(f"⚠️ Error de formato de hora para {day_name}: {time_error}")
                        continue
                    except Exception as day_error:
                        print(f"⚠️ Error procesando día {day_name}: {day_error}")
                        continue

            if created_schedules > 0:
                try:
                    db.session.commit()
                    print(f"✅ {created_schedules} horarios de veterinario sincronizados exitosamente para: {user_id_str}")

                    # Verificar que se guardaron correctamente
                    verification_count = VeterinarianSchedule.query.filter_by(veterinarian_id=user_id_str).count()
                    print(f"🔍 Verificación: {verification_count} horarios encontrados en la base de datos")

                except Exception as commit_error:
                    print(f"❌ Error haciendo commit: {commit_error}")
                    db.session.rollback()
                    raise commit_error
            else:
                print(f"⚠️ No se crearon horarios para el usuario {user_id_str}")

        elif user_role:
            print(f"ℹ️ Usuario {user_id_str} tiene rol '{user_role}', no es veterinario - no se sincroniza")
        else:
            print(f"⚠️ No se pudo determinar el rol del usuario {user_id_str}")

    except Exception as e:
        print(f"❌ Error general sincronizando horarios de veterinario: {e}")
        import traceback
        traceback.print_exc()
        try:
            db.session.rollback()
        except:
            pass


@appointment_bp.route('/schedules/create-sample', methods=['POST'])
def create_sample_schedules():
    """Crear horarios de ejemplo para veterinarios existentes"""
    try:
        print("🔄 Creando horarios de ejemplo...")

        # Obtener veterinarios desde Auth Service
        auth_url = f"{current_app.config.get('AUTH_SERVICE_URL', 'http://localhost:5001')}/auth/users/veterinarians"
        response = requests.get(auth_url, timeout=10)

        if response.status_code != 200:
            return jsonify({
                'success': False,
                'message': 'No se pudieron obtener veterinarios'
            }), 400

        data = response.json()
        if not data.get('success'):
            return jsonify({
                'success': False,
                'message': 'Error obteniendo veterinarios'
            }), 400

        veterinarians = data.get('veterinarians', [])

        if not veterinarians:
            return jsonify({
                'success': False,
                'message': 'No hay veterinarios registrados'
            }), 400

        created_count = 0

        for vet in veterinarians:
            vet_id = str(vet['id'])  # CONVERSIÓN UUID

            # Verificar si ya tiene horarios
            existing_schedules = VeterinarianSchedule.query.filter_by(veterinarian_id=vet_id).count()

            if existing_schedules > 0:
                print(f"⚠️ Veterinario {vet['first_name']} {vet['last_name']} ya tiene horarios")
                continue

            # Crear horarios de ejemplo (Lun-Vie 8:00-17:00, Sáb 8:00-12:00)
            sample_schedules = [
                (1, '08:00', '17:00'),  # Lunes
                (2, '08:00', '17:00'),  # Martes
                (3, '08:00', '17:00'),  # Miércoles
                (4, '08:00', '17:00'),  # Jueves
                (5, '08:00', '16:00'),  # Viernes
                (6, '08:00', '12:00'),  # Sábado
            ]

            for day_of_week, start_time_str, end_time_str in sample_schedules:
                try:
                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                    end_time = datetime.strptime(end_time_str, '%H:%M').time()

                    schedule = VeterinarianSchedule(
                        veterinarian_id=vet_id,  # UUID YA CONVERTIDO
                        day_of_week=day_of_week,
                        start_time=start_time,
                        end_time=end_time,
                        is_available=True
                    )

                    db.session.add(schedule)
                    created_count += 1

                except Exception as schedule_error:
                    print(f"❌ Error creando horario para {vet['first_name']}: {schedule_error}")
                    continue

            print(f"✅ Horarios creados para {vet['first_name']} {vet['last_name']}")

        # Hacer commit de todos los horarios
        if created_count > 0:
            db.session.commit()
            print(f"✅ {created_count} horarios creados exitosamente")

        return jsonify({
            'success': True,
            'message': f'Se crearon {created_count} horarios de ejemplo',
            'created_count': created_count,
            'veterinarians_processed': len(veterinarians)
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creando horarios de ejemplo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


@appointment_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'appointment_service'
    }), 200