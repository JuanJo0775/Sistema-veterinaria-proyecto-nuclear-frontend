# microservices/notification_service/app/services/whatsapp_service.py
from flask import current_app
import logging
from datetime import datetime


class WhatsAppService:
    def __init__(self):
        self.client = None
        self.logger = logging.getLogger(__name__)

    def init_app(self, app):
        """Inicializar Twilio client"""
        try:
            # Solo importar Twilio si estamos en producción
            if app.config['FLASK_ENV'] == 'production':
                from twilio.rest import Client
                account_sid = app.config.get('TWILIO_ACCOUNT_SID')
                auth_token = app.config.get('TWILIO_AUTH_TOKEN')

                if account_sid and auth_token:
                    self.client = Client(account_sid, auth_token)
                    self.logger.info("✅ Twilio inicializado para producción")
                else:
                    self.logger.warning("⚠️ Credenciales de Twilio no encontradas")
            else:
                self.logger.info("📱 WhatsApp Service en modo desarrollo")

        except ImportError:
            self.logger.warning("⚠️ Twilio no instalado, usando modo simulado")
        except Exception as e:
            self.logger.error(f"❌ Error inicializando Twilio: {str(e)}")

    def send_whatsapp_message(self, to_phone, message):
        """Enviar mensaje de WhatsApp"""
        try:
            # Formatear número de teléfono
            if not to_phone.startswith('+'):
                to_phone = '+' + to_phone.replace(' ', '').replace('-', '')

            # En desarrollo, solo simular el envío
            if current_app.config['FLASK_ENV'] == 'development' or not self.client:
                self.logger.info(f"📱 [SIMULADO] WhatsApp enviado a {to_phone}")
                self.logger.info(f"   Mensaje: {message[:100]}...")
                return True

            # En producción, enviar WhatsApp real
            from_phone = f"whatsapp:{current_app.config.get('TWILIO_PHONE_NUMBER')}"
            to_whatsapp = f"whatsapp:{to_phone}"

            message = self.client.messages.create(
                body=message,
                from_=from_phone,
                to=to_whatsapp
            )

            self.logger.info(f"✅ WhatsApp enviado a {to_phone}, SID: {message.sid}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error enviando WhatsApp a {to_phone}: {str(e)}")
            return False

    def send_appointment_reminder(self, to_phone, appointment_details):
        """Enviar recordatorio de cita por WhatsApp"""
        try:
            message = f"""
🐾 *Recordatorio de Cita*

Hola! Le recordamos su cita:

📅 *Fecha:* {appointment_details.get('date')}
🕐 *Hora:* {appointment_details.get('time')}
👨‍⚕️ *Veterinario:* Dr. {appointment_details.get('veterinarian_name', 'N/A')}
🐕 *Mascota:* {appointment_details.get('pet_name', 'N/A')}

Por favor llegue 15 minutos antes.

_Clínica Veterinaria_
📞 +1234567890
            """.strip()

            return self.send_whatsapp_message(to_phone, message)

        except Exception as e:
            self.logger.error(f"❌ Error enviando recordatorio WhatsApp: {str(e)}")
            return False

    def send_appointment_confirmation(self, to_phone, appointment_details):
        """Enviar confirmación de cita por WhatsApp"""
        try:
            message = f"""
✅ *Cita Confirmada*

Su cita ha sido confirmada:

📅 *Fecha:* {appointment_details.get('date')}
🕐 *Hora:* {appointment_details.get('time')}
👨‍⚕️ *Veterinario:* Dr. {appointment_details.get('veterinarian_name', 'N/A')}
🐕 *Mascota:* {appointment_details.get('pet_name', 'N/A')}

¡Gracias por confiar en nosotros!

_Clínica Veterinaria_
            """.strip()

            return self.send_whatsapp_message(to_phone, message)

        except Exception as e:
            self.logger.error(f"❌ Error enviando confirmación WhatsApp: {str(e)}")
            return False

    def send_appointment_cancellation(self, to_phone, appointment_details):
        """Enviar notificación de cancelación por WhatsApp"""
        try:
            message = f"""
❌ *Cita Cancelada*

Su cita ha sido cancelada:

📅 *Fecha:* {appointment_details.get('date')}
🕐 *Hora:* {appointment_details.get('time')}

Puede reagendar llamando al 📞 +1234567890

_Clínica Veterinaria_
            """.strip()

            return self.send_whatsapp_message(to_phone, message)

        except Exception as e:
            self.logger.error(f"❌ Error enviando cancelación WhatsApp: {str(e)}")
            return False