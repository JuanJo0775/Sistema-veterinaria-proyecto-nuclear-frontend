#!/bin/bash
# scripts/test_notifications.sh

echo "🧪 Probando Notification Service..."

# Test de health check
echo "1. Health Check:"
curl -s http://localhost:5003/health | python -m json.tool

echo -e "\n2. Test de email:"
curl -X POST http://localhost:5003/notifications/test-email \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com"
  }' | python -m json.tool

echo -e "\n3. Test de WhatsApp:"
curl -X POST http://localhost:5003/notifications/test-whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1234567890"
  }' | python -m json.tool

echo -e "\n4. Test de recordatorio de cita:"
curl -X POST http://localhost:5003/notifications/send-reminder \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-id",
    "email": "cliente@example.com",
    "phone": "+1234567890",
    "appointment_details": {
      "date": "2024-12-25",
      "time": "10:00",
      "veterinarian_name": "Juan Pérez",
      "pet_name": "Firulais",
      "reason": "Consulta general"
    }
  }' | python -m json.tool

echo -e "\n5. Test de alerta de nueva cita:"
curl -X POST http://localhost:5003/notifications/appointment-alert \
  -H "Content-Type: application/json" \
  -d '{
    "appointment_details": {
      "date": "2024-12-25",
      "time": "10:00",
      "veterinarian_name": "Juan Pérez",
      "client_name": "María García",
      "pet_name": "Firulais",
      "reason": "Consulta general"
    },
    "receptionist_emails": ["recepcion@veterinariaclinic.com"]
  }' | python -m json.tool

echo -e "\n6. Test de alerta de inventario:"
curl -X POST http://localhost:5003/notifications/inventory-alert \
  -H "Content-Type: application/json" \
  -d '{
    "alert_type": "low_stock",
    "medication_details": {
      "name": "Amoxicilina 500mg",
      "stock_quantity": 5
    },
    "admin_emails": ["admin@veterinariaclinic.com"]
  }' | python -m json.tool

echo -e "\n✅ Tests de Notification Service completados!"