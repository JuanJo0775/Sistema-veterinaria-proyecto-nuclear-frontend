# microservices/notification_service/app/routes/notification_routes.py
from flask import Blueprint, request, jsonify
from datetime import datetime
from ..services.email_service import EmailService
from ..services.whatsapp_service import WhatsAppService
from ..models.notification import Notification, db

notification_bp = Blueprint('notifications', __name__)
email_service = EmailService()
whatsapp_service = WhatsAppService()


@notification_bp.route('/send-reminder', methods=['POST'])
def send_appointment_reminder():
    """Enviar recordatorio de cita por email y WhatsApp"""
    try:
        data = request.get_json()

        # Validaciones básicas
        required_fields = ['user_id', 'appointment_details']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        appointment_details = data.get('appointment_details')
        user_id = data.get('user_id')
        email = data.get('email')
        phone = data.get('phone')

        results = {
            'email_sent': False,
            'whatsapp_sent': False
        }

        # Enviar por email si se proporciona
        if email:
            results['email_sent'] = email_service.send_appointment_reminder(email, appointment_details)

        # Enviar por WhatsApp si se proporciona
        if phone:
            results['whatsapp_sent'] = whatsapp_service.send_appointment_reminder(phone, appointment_details)

        # Guardar notificación en BD
        notification = Notification.create_notification(
            user_id=user_id,
            notification_type='appointment_reminder',
            title='Recordatorio de Cita',
            message=f"Recordatorio: Cita programada para {appointment_details.get('date')} a las {appointment_details.get('time')}"
        )

        # Actualizar campos de envío
        notification.email_sent = results['email_sent']
        notification.sms_sent = results['whatsapp_sent']
        notification.sent_at = datetime.utcnow()

        if results['email_sent']:
            notification.email_sent_at = datetime.utcnow()
        if results['whatsapp_sent']:
            notification.sms_sent_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'success': True,
            'notification_id': notification.id,
            'email_sent': results['email_sent'],
            'whatsapp_sent': results['whatsapp_sent']
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@notification_bp.route('/appointment-alert', methods=['POST'])
def send_appointment_alert():
    """Enviar alerta de nueva cita a recepcionistas"""
    try:
        data = request.get_json()

        appointment_details = data.get('appointment_details')
        receptionist_emails = data.get('receptionist_emails', [])

        if not appointment_details:
            return jsonify({
                'success': False,
                'message': 'appointment_details requerido'
            }), 400

        # Enviar alertas a todos los recepcionistas
        emails_sent = 0
        for email in receptionist_emails:
            if email_service.send_new_appointment_alert(email, appointment_details):
                emails_sent += 1

        return jsonify({
            'success': True,
            'message': f'Alertas enviadas a {emails_sent} recepcionistas',
            'emails_sent': emails_sent,
            'total_emails': len(receptionist_emails)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@notification_bp.route('/inventory-alert', methods=['POST'])
def send_inventory_alert():
    """Enviar alertas de inventario"""
    try:
        data = request.get_json()

        admin_emails = data.get('admin_emails', [])
        alert_type = data.get('alert_type')  # 'low_stock' o 'expiration'
        medication_details = data.get('medication_details')

        if not alert_type or not medication_details:
            return jsonify({
                'success': False,
                'message': 'alert_type y medication_details requeridos'
            }), 400

        emails_sent = 0
        for email in admin_emails:
            success = False
            if alert_type == 'low_stock':
                success = email_service.send_low_stock_alert(email, medication_details)
            elif alert_type == 'expiration':
                success = email_service.send_expiration_alert(email, medication_details)

            if success:
                emails_sent += 1

        return jsonify({
            'success': True,
            'message': f'Alertas de inventario enviadas a {emails_sent} administradores',
            'emails_sent': emails_sent,
            'alert_type': alert_type
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@notification_bp.route('/user/<user_id>', methods=['GET'])
def get_user_notifications(user_id):
    """Obtener notificaciones de un usuario"""
    try:
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'

        notifications = Notification.get_by_user(user_id, unread_only)

        return jsonify({
            'success': True,
            'notifications': [notif.to_dict() for notif in notifications],
            'total': len(notifications)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@notification_bp.route('/mark-read/<notification_id>', methods=['PUT'])
def mark_notification_as_read(notification_id):
    """Marcar notificación como leída"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')

        if not user_id:
            return jsonify({
                'success': False,
                'message': 'user_id requerido'
            }), 400

        notification = Notification.mark_as_read(notification_id, user_id)

        if notification:
            return jsonify({
                'success': True,
                'message': 'Notificación marcada como leída',
                'notification': notification.to_dict()
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Notificación no encontrada'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@notification_bp.route('/send-confirmation', methods=['POST'])
def send_appointment_confirmation():
    """Enviar confirmación de cita"""
    try:
        data = request.get_json()

        appointment_details = data.get('appointment_details')
        email = data.get('email')
        phone = data.get('phone')

        results = {
            'email_sent': False,
            'whatsapp_sent': False
        }

        if email:
            # Usar el método de recordatorio para confirmación (similar formato)
            results['email_sent'] = email_service.send_appointment_reminder(email, appointment_details)

        if phone:
            results['whatsapp_sent'] = whatsapp_service.send_appointment_confirmation(phone, appointment_details)

        return jsonify({
            'success': True,
            'email_sent': results['email_sent'],
            'whatsapp_sent': results['whatsapp_sent']
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@notification_bp.route('/send-cancellation', methods=['POST'])
def send_appointment_cancellation():
    """Enviar notificación de cancelación"""
    try:
        data = request.get_json()

        appointment_details = data.get('appointment_details')
        email = data.get('email')
        phone = data.get('phone')

        results = {
            'email_sent': False,
            'whatsapp_sent': False
        }

        if phone:
            results['whatsapp_sent'] = whatsapp_service.send_appointment_cancellation(phone, appointment_details)

        # Para email de cancelación, usar un template básico
        if email:
            subject = "Cita Cancelada - Clínica Veterinaria"
            body = f"""
Su cita ha sido cancelada:

Fecha: {appointment_details.get('date')}
Hora: {appointment_details.get('time')}

Para reagendar, contáctenos al +1234567890

Clínica Veterinaria
            """
            results['email_sent'] = email_service.send_email(email, subject, body)

        return jsonify({
            'success': True,
            'email_sent': results['email_sent'],
            'whatsapp_sent': results['whatsapp_sent']
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@notification_bp.route('/test-email', methods=['POST'])
def test_email():
    """Endpoint de prueba para emails"""
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({
                'success': False,
                'message': 'email requerido'
            }), 400

        success = email_service.send_email(
            email,
            "Test Email - Clínica Veterinaria",
            "Este es un email de prueba del sistema de notificaciones."
        )

        return jsonify({
            'success': True,
            'email_sent': success
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@notification_bp.route('/test-whatsapp', methods=['POST'])
def test_whatsapp():
    """Endpoint de prueba para WhatsApp"""
    try:
        data = request.get_json()
        phone = data.get('phone')

        if not phone:
            return jsonify({
                'success': False,
                'message': 'phone requerido'
            }), 400

        success = whatsapp_service.send_whatsapp_message(
            phone,
            "🐾 Este es un mensaje de prueba del sistema de notificaciones de la Clínica Veterinaria."
        )

        return jsonify({
            'success': True,
            'whatsapp_sent': success
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@notification_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'notification_service'
    }), 200