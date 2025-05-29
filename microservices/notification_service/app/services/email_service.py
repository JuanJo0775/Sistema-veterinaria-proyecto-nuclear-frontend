# microservices/notification_service/app/services/email_service.py
from flask import current_app
from flask_mail import Mail, Message
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging


class EmailService:
    def __init__(self):
        self.mail = None
        self.logger = logging.getLogger(__name__)

    def init_app(self, app):
        """Inicializar Flask-Mail con la app"""
        self.mail = Mail(app)

    def send_email(self, to_email, subject, body, html_body=None):
        """Enviar email básico"""
        try:
            # En desarrollo, solo simular el envío
            if current_app.config['FLASK_ENV'] == 'development':
                self.logger.info(f"📧 [SIMULADO] Email enviado a {to_email}")
                self.logger.info(f"   Asunto: {subject}")
                self.logger.info(f"   Contenido: {body[:100]}...")
                return True

            # En producción, enviar email real
            msg = Message(
                subject=subject,
                recipients=[to_email],
                body=body,
                html=html_body,
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )

            if self.mail:
                self.mail.send(msg)
                self.logger.info(f"✅ Email enviado a {to_email}")
                return True
            else:
                self.logger.error("❌ Flask-Mail no inicializado")
                return False

        except Exception as e:
            self.logger.error(f"❌ Error enviando email a {to_email}: {str(e)}")
            return False

    def send_appointment_reminder(self, to_email, appointment_details):
        """Enviar recordatorio de cita"""
        try:
            subject = "🐾 Recordatorio de Cita - Clínica Veterinaria"

            body = f"""
Estimado cliente,

Le recordamos que tiene una cita programada:

📅 Fecha: {appointment_details.get('date')}
🕐 Hora: {appointment_details.get('time')}
👨‍⚕️ Veterinario: Dr. {appointment_details.get('veterinarian_name', 'N/A')}
🐕 Mascota: {appointment_details.get('pet_name', 'N/A')}
📋 Motivo: {appointment_details.get('reason', 'Consulta general')}

Por favor, llegue 15 minutos antes de su cita.

Si necesita cancelar o reprogramar, contáctenos con al menos 24 horas de anticipación.

Saludos cordiales,
Clínica Veterinaria
📞 +1234567890
📧 info@veterinariaclinic.com
            """

            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                        <h2 style="color: #2c5aa0; text-align: center;">🐾 Recordatorio de Cita</h2>

                        <p>Estimado cliente,</p>

                        <p>Le recordamos que tiene una cita programada:</p>

                        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p><strong>📅 Fecha:</strong> {appointment_details.get('date')}</p>
                            <p><strong>🕐 Hora:</strong> {appointment_details.get('time')}</p>
                            <p><strong>👨‍⚕️ Veterinario:</strong> Dr. {appointment_details.get('veterinarian_name', 'N/A')}</p>
                            <p><strong>🐕 Mascota:</strong> {appointment_details.get('pet_name', 'N/A')}</p>
                            <p><strong>📋 Motivo:</strong> {appointment_details.get('reason', 'Consulta general')}</p>
                        </div>

                        <p><em>Por favor, llegue 15 minutos antes de su cita.</em></p>

                        <p>Si necesita cancelar o reprogramar, contáctenos con al menos 24 horas de anticipación.</p>

                        <hr style="margin: 30px 0;">

                        <p style="text-align: center; color: #666;">
                            <strong>Clínica Veterinaria</strong><br>
                            📞 +1234567890<br>
                            📧 info@veterinariaclinic.com
                        </p>
                    </div>
                </body>
            </html>
            """

            return self.send_email(to_email, subject, body, html_body)

        except Exception as e:
            self.logger.error(f"❌ Error enviando recordatorio de cita: {str(e)}")
            return False

    def send_new_appointment_alert(self, to_email, appointment_details):
        """Enviar alerta de nueva cita a recepcionistas"""
        try:
            subject = "🔔 Nueva Cita Agendada - Clínica Veterinaria"

            body = f"""
Nueva cita agendada en el sistema:

📅 Fecha: {appointment_details.get('date')}
🕐 Hora: {appointment_details.get('time')}
👨‍⚕️ Veterinario: Dr. {appointment_details.get('veterinarian_name', 'N/A')}
👤 Cliente: {appointment_details.get('client_name', 'N/A')}
🐕 Mascota: {appointment_details.get('pet_name', 'N/A')}
📋 Motivo: {appointment_details.get('reason', 'Consulta general')}

Por favor, revise la agenda y confirme con el cliente si es necesario.

Sistema de Gestión Clínica Veterinaria
            """

            return self.send_email(to_email, subject, body)

        except Exception as e:
            self.logger.error(f"❌ Error enviando alerta de nueva cita: {str(e)}")
            return False

    def send_low_stock_alert(self, to_email, medication_details):
        """Enviar alerta de stock bajo"""
        try:
            subject = "⚠️ Alerta de Stock Bajo - Clínica Veterinaria"

            medications_list = ""
            if isinstance(medication_details, list):
                for med in medication_details:
                    medications_list += f"• {med.get('name', 'N/A')} - Stock: {med.get('stock_quantity', 0)} unidades\n"
            else:
                medications_list = f"• {medication_details.get('name', 'N/A')} - Stock: {medication_details.get('stock_quantity', 0)} unidades"

            body = f"""
ALERTA: Los siguientes medicamentos tienen stock bajo:

{medications_list}

Por favor, proceder con el reabastecimiento lo antes posible.

Sistema de Gestión de Inventario
Clínica Veterinaria
            """

            return self.send_email(to_email, subject, body)

        except Exception as e:
            self.logger.error(f"❌ Error enviando alerta de stock bajo: {str(e)}")
            return False

    def send_expiration_alert(self, to_email, medication_details):
        """Enviar alerta de medicamentos por vencer"""
        try:
            subject = "⚠️ Alerta de Medicamentos por Vencer - Clínica Veterinaria"

            medications_list = ""
            if isinstance(medication_details, list):
                for med in medication_details:
                    medications_list += f"• {med.get('name', 'N/A')} - Vence: {med.get('expiration_date', 'N/A')}\n"
            else:
                medications_list = f"• {medication_details.get('name', 'N/A')} - Vence: {medication_details.get('expiration_date', 'N/A')}"

            body = f"""
ALERTA: Los siguientes medicamentos están próximos a vencer:

{medications_list}

Por favor, revisar y tomar las medidas necesarias.

Sistema de Gestión de Inventario
Clínica Veterinaria
            """

            return self.send_email(to_email, subject, body)

        except Exception as e:
            self.logger.error(f"❌ Error enviando alerta de vencimiento: {str(e)}")
            return False