# microservices/appointment_service/app/services/appointment_service.py
from datetime import datetime, timedelta, time, date
import requests
from flask import current_app
from ..models.appointment import Appointment, db
from ..models.schedule import VeterinarianSchedule


class AppointmentService:
    def check_availability(self, veterinarian_id, appointment_date, appointment_time):
        """Verificar si un horario está disponible"""
        # Convertir strings a objetos date y time si es necesario
        if isinstance(appointment_date, str):
            appointment_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        if isinstance(appointment_time, str):
            appointment_time = datetime.strptime(appointment_time, '%H:%M').time()

        # Verificar horario del veterinario
        day_of_week = appointment_date.weekday()  # 0=Lunes, 6=Domingo
        schedule = VeterinarianSchedule.get_by_day(veterinarian_id, day_of_week)

        if not schedule:
            return False

        # Verificar que esté dentro del horario laboral
        if not (schedule.start_time <= appointment_time <= schedule.end_time):
            return False

        # Verificar que no haya cita existente
        return Appointment.check_availability(veterinarian_id, appointment_date, appointment_time)

    def create_appointment(self, appointment_data):
        """Crear nueva cita"""
        appointment = Appointment(
            pet_id=appointment_data.get('pet_id'),
            veterinarian_id=appointment_data.get('veterinarian_id'),
            client_id=appointment_data.get('client_id'),
            appointment_date=datetime.strptime(appointment_data.get('appointment_date'), '%Y-%m-%d').date(),
            appointment_time=datetime.strptime(appointment_data.get('appointment_time'), '%H:%M').time(),
            reason=appointment_data.get('reason'),
            status='scheduled'
        )

        db.session.add(appointment)
        db.session.commit()
        return appointment

    def get_available_slots(self, veterinarian_id, date_str):
        """Obtener slots disponibles para un veterinario en una fecha"""
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        day_of_week = appointment_date.weekday()

        # Obtener horario del veterinario
        schedule = VeterinarianSchedule.get_by_day(veterinarian_id, day_of_week)
        if not schedule:
            return []

        # Generar slots cada 30 minutos
        slots = []
        current_time = schedule.start_time
        end_time = schedule.end_time

        while current_time < end_time:
            if Appointment.check_availability(veterinarian_id, appointment_date, current_time):
                slots.append(current_time.strftime('%H:%M'))

            # Agregar 30 minutos
            current_datetime = datetime.combine(appointment_date, current_time)
            current_datetime += timedelta(minutes=30)
            current_time = current_datetime.time()

        return slots

    def get_appointments_by_veterinarian(self, vet_id, start_date=None, end_date=None):
        """Obtener citas de un veterinario"""
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        appointments = Appointment.get_by_veterinarian(vet_id, start_date, end_date)
        return [apt.to_dict() for apt in appointments]

    def get_appointments_by_client(self, client_id, status=None):
        """Obtener citas de un cliente"""
        appointments = Appointment.get_by_client(client_id, status)
        return [apt.to_dict() for apt in appointments]

    def update_appointment(self, appointment_id, update_data):
        """Actualizar cita existente"""
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            return None

        # Actualizar campos permitidos
        for key, value in update_data.items():
            if key == 'appointment_date' and value:
                appointment.appointment_date = datetime.strptime(value, '%Y-%m-%d').date()
            elif key == 'appointment_time' and value:
                appointment.appointment_time = datetime.strptime(value, '%H:%M').time()
            elif hasattr(appointment, key):
                setattr(appointment, key, value)

        db.session.commit()
        return appointment

    def cancel_appointment(self, appointment_id):
        """Cancelar cita"""
        appointment = Appointment.query.get(appointment_id)
        if appointment:
            appointment.status = 'cancelled'
            db.session.commit()
            return appointment
        return None

    def confirm_appointment(self, appointment_id):
        """Confirmar cita"""
        appointment = Appointment.query.get(appointment_id)
        if appointment:
            appointment.status = 'confirmed'
            db.session.commit()
            return appointment
        return None

    def complete_appointment(self, appointment_id):
        """Marcar cita como completada"""
        appointment = Appointment.query.get(appointment_id)
        if appointment:
            appointment.status = 'completed'
            db.session.commit()
            return appointment
        return None

    def notify_new_appointment(self, appointment_id):
        """Notificar nueva cita al servicio de notificaciones"""
        try:
            notification_url = f"{current_app.config['NOTIFICATION_SERVICE_URL']}/notifications/appointment-alert"
            appointment = Appointment.query.get(appointment_id)

            if not appointment:
                return False

            payload = {
                'appointment_details': {
                    'id': appointment.id,
                    'date': appointment.appointment_date.isoformat(),
                    'time': appointment.appointment_time.strftime('%H:%M'),
                    'client_id': appointment.client_id,
                    'pet_id': appointment.pet_id,
                    'veterinarian_id': appointment.veterinarian_id,
                    'reason': appointment.reason
                },
                'receptionist_emails': ['recepcion@veterinariaclinic.com']  # Configurar dinámicamente
            }

            response = requests.post(notification_url, json=payload, timeout=5)
            return response.status_code == 200

        except Exception as e:
            print(f"Error notificando nueva cita: {e}")
            return False