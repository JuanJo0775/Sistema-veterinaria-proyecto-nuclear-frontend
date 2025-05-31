# API Documentation - Sistema de Gestión Clínica Veterinaria

## Descripción
Sistema de microservicios para gestión integral de clínica veterinaria con los siguientes servicios:
- **Auth Service** (Puerto 5001) - Autenticación y usuarios
- **Appointment Service** (Puerto 5002) - Gestión de citas
- **Notification Service** (Puerto 5003) - Notificaciones email/WhatsApp
- **Medical Service** (Puerto 5004) - Historias clínicas y mascotas
- **Inventory Service** (Puerto 5005) - Gestión de inventario

## Base URLs
```
Auth Service: http://localhost:5001
Appointment Service: http://localhost:5002
Notification Service: http://localhost:5003
Medical Service: http://localhost:5004
Inventory Service: http://localhost:5005
```

---

## 🔐 AUTH SERVICE (Puerto 5001)

### 1. Login
```http
POST /auth/login
```
**Body:**
```json
{
  "email": "admin@veterinariaclinic.com",
  "password": "admin123"
}
```

### 2. Registro de Usuario
```http
POST /auth/register
```
**Body:**
```json
{
  "email": "cliente@email.com",
  "password": "password123",
  "first_name": "Juan",
  "last_name": "Pérez",
  "phone": "+1234567890",
  "address": "Calle 123",
  "role": "client"
}
```

### 3. Verificar Token
```http
POST /auth/verify
```
**Headers:**
```
Authorization: Bearer <token>
```

### 4. Cambiar Contraseña
```http
PUT /auth/change-password
```
**Headers:**
```
Authorization: Bearer <token>
```
**Body:**
```json
{
  "old_password": "password_actual",
  "new_password": "nuevo_password"
}
```

### 5. Ver Perfil
```http
GET /auth/profile
```
**Headers:**
```
Authorization: Bearer <token>
```

### 6. Actualizar Perfil
```http
PUT /auth/profile
```
**Headers:**
```
Authorization: Bearer <token>
```
**Body:**
```json
{
  "first_name": "Nuevo Nombre",
  "last_name": "Nuevo Apellido",
  "phone": "+0987654321"
}
```

### 7. Health Check
```http
GET /auth/health
```

---

## 📅 APPOINTMENT SERVICE (Puerto 5002)

### 1. Crear Cita
```http
POST /appointments/create
```
**Body:**
```json
{
  "pet_id": "uuid-mascota",
  "veterinarian_id": "uuid-veterinario",
  "client_id": "uuid-cliente",
  "appointment_date": "2024-01-15",
  "appointment_time": "10:30",
  "reason": "Consulta general"
}
```

### 2. Ver Horarios Disponibles
```http
GET /appointments/available-slots?veterinarian_id=<uuid>&date=2024-01-15
```

### 3. Citas por Veterinario
```http
GET /appointments/by-veterinarian/<veterinarian_id>?start_date=2024-01-01&end_date=2024-01-31
```

### 4. Citas por Cliente
```http
GET /appointments/by-client/<client_id>?status=scheduled
```

### 5. Actualizar Cita
```http
PUT /appointments/update/<appointment_id>
```
**Body:**
```json
{
  "appointment_date": "2024-01-16",
  "appointment_time": "11:00",
  "reason": "Control post-operatorio"
}
```

### 6. Cancelar Cita
```http
PUT /appointments/cancel/<appointment_id>
```

### 7. Confirmar Cita
```http
PUT /appointments/confirm/<appointment_id>
```

### 8. Completar Cita
```http
PUT /appointments/complete/<appointment_id>
```

### 9. Citas de Hoy
```http
GET /appointments/today
```

### 10. Health Check
```http
GET /appointments/health
```

---

## 🐕 MEDICAL SERVICE (Puerto 5004)

### Gestión de Mascotas

### 1. Crear Mascota
```http
POST /medical/pets
```
**Body:**
```json
{
  "owner_id": "uuid-propietario",
  "name": "Firulais",
  "species": "Canino",
  "breed": "Golden Retriever",
  "birth_date": "2020-05-15",
  "weight": 25.5,
  "gender": "Macho",
  "microchip_number": "123456789",
  "allergies": "Ninguna conocida",
  "vaccination_status": "Al día"
}
```

### 2. Ver Mascota
```http
GET /medical/pets/<pet_id>
```

### 3. Actualizar Mascota
```http
PUT /medical/pets/<pet_id>
```
**Body:**
```json
{
  "weight": 26.0,
  "medical_notes": "Tratamiento completado"
}
```

### 4. Mascotas por Propietario
```http
GET /medical/pets/owner/<owner_id>
```

### 5. Buscar Mascotas
```http
GET /medical/pets/search?q=firulais
```

### 6. Subir Foto de Mascota
```http
POST /medical/pets/<pet_id>/photo
```
**Form Data:**
```
file: [archivo de imagen]
```

### Historias Clínicas

### 7. Crear Historia Clínica
```http
POST /medical/records
```
**Body:**
```json
{
  "pet_id": "uuid-mascota",
  "veterinarian_id": "uuid-veterinario",
  "appointment_id": "uuid-cita",
  "symptoms_description": "Decaimiento y falta de apetito",
  "physical_examination": "Temperatura elevada",
  "diagnosis": "Infección viral",
  "treatment": "Reposo y medicación",
  "weight_at_visit": 25.2,
  "temperature": 39.5
}
```

### 8. Ver Historia Clínica
```http
GET /medical/records/<record_id>
```

### 9. Actualizar Historia Clínica
```http
PUT /medical/records/<record_id>
```

### 10. Completar Historia Clínica
```http
PUT /medical/records/<record_id>/complete
```

### 11. Historias por Mascota
```http
GET /medical/records/pet/<pet_id>
```

### Prescripciones

### 12. Agregar Prescripción
```http
POST /medical/prescriptions
```
**Body:**
```json
{
  "medical_record_id": "uuid-historia",
  "medication_id": "uuid-medicamento",
  "medication_name": "Amoxicilina",
  "dosage": "500mg",
  "frequency": "Cada 8 horas",
  "duration": "7 días",
  "quantity_prescribed": 21,
  "instructions": "Tomar con alimento"
}
```

### Resultados de Exámenes

### 13. Agregar Resultado de Examen
```http
POST /medical/exam-results
```
**Form Data:**
```
medical_record_id: uuid-historia
exam_name: Hemograma Completo
observations: Valores normales
date_performed: 2024-01-15
performed_by: Lab Central
file: [archivo PDF opcional]
```

### 14. Resumen Médico
```http
GET /medical/summary/pet/<pet_id>
```

### 15. Health Check
```http
GET /medical/health
```

---

## 💊 INVENTORY SERVICE (Puerto 5005)

### Gestión de Medicamentos

### 1. Crear Medicamento
```http
POST /inventory/medications
```
**Body:**
```json
{
  "name": "Amoxicilina 500mg",
  "description": "Antibiótico para infecciones bacterianas",
  "stock_quantity": 100,
  "unit_price": 2500,
  "expiration_date": "2025-12-31",
  "supplier": "Laboratorios Vet SA",
  "minimum_stock_alert": 20,
  "category": "Antibiótico",
  "presentation": "Comprimidos",
  "concentration": "500mg",
  "laboratory": "LabVet"
}
```

### 2. Ver Todos los Medicamentos
```http
GET /inventory/medications?include_inactive=false&category=Antibiótico
```

### 3. Ver Medicamento por ID
```http
GET /inventory/medications/<medication_id>
```

### 4. Actualizar Medicamento
```http
PUT /inventory/medications/<medication_id>
```
**Body:**
```json
{
  "unit_price": 2800,
  "supplier": "Nuevo Proveedor"
}
```

### 5. Desactivar Medicamento
```http
PUT /inventory/medications/<medication_id>/deactivate
```

### 6. Buscar Medicamentos
```http
GET /inventory/medications/search?q=amoxicilina
```

### Gestión de Stock

### 7. Actualizar Stock
```http
PUT /inventory/update-stock
```
**Body:**
```json
{
  "medication_id": "uuid-medicamento",
  "quantity_change": -5,
  "reason": "prescription",
  "reference_id": "uuid-prescripcion",
  "user_id": "uuid-usuario"
}
```

### 8. Agregar Stock (Compra)
```http
POST /inventory/add-stock
```
**Body:**
```json
{
  "medication_id": "uuid-medicamento",
  "quantity": 50,
  "reason": "purchase",
  "unit_cost": 2400,
  "user_id": "uuid-usuario"
}
```

### 9. Reducir Stock
```http
POST /inventory/reduce-stock
```
**Body:**
```json
{
  "medication_id": "uuid-medicamento",
  "quantity": 10,
  "reason": "expired",
  "user_id": "uuid-usuario"
}
```

### 10. Ver Movimientos de Stock
```http
GET /inventory/movements?medication_id=<uuid>&start_date=2024-01-01&end_date=2024-01-31&limit=50
```

### Alertas y Reportes

### 11. Medicamentos con Stock Bajo
```http
GET /inventory/alerts/low-stock
```

### 12. Medicamentos por Vencer
```http
GET /inventory/alerts/expiring?days=30
```

### 13. Verificar Alertas de Vencimiento
```http
POST /inventory/alerts/check-expiration
```
**Body:**
```json
{
  "days_threshold": 30
}
```

### 14. Resumen de Inventario
```http
GET /inventory/summary
```

### 15. Reporte de Movimientos
```http
GET /inventory/reports/movements?start_date=2024-01-01&end_date=2024-01-31
```

### 16. Exportar a CSV
```http
GET /inventory/export/csv
```

### 17. Categorías de Medicamentos
```http
GET /inventory/categories
```

### 18. Estadísticas del Inventario
```http
GET /inventory/stats
```

### 19. Health Check
```http
GET /inventory/health
```

---

## 📧 NOTIFICATION SERVICE (Puerto 5003)

### 1. Enviar Recordatorio de Cita
```http
POST /notifications/send-reminder
```
**Body:**
```json
{
  "user_id": "uuid-usuario",
  "email": "cliente@email.com",
  "phone": "+1234567890",
  "appointment_details": {
    "date": "2024-01-15",
    "time": "10:30",
    "veterinarian_name": "Dr. Pérez",
    "pet_name": "Firulais",
    "reason": "Consulta general"
  }
}
```

### 2. Alerta de Nueva Cita
```http
POST /notifications/appointment-alert
```
**Body:**
```json
{
  "appointment_details": {
    "date": "2024-01-15",
    "time": "10:30",
    "client_name": "Juan Pérez",
    "pet_name": "Firulais",
    "veterinarian_name": "Dr. García",
    "reason": "Emergencia"
  },
  "receptionist_emails": ["recepcion@veterinariaclinic.com"]
}
```

### 3. Alerta de Inventario
```http
POST /notifications/inventory-alert
```
**Body:**
```json
{
  "alert_type": "low_stock",
  "medication_details": {
    "name": "Amoxicilina",
    "stock_quantity": 5,
    "minimum_stock_alert": 20
  },
  "admin_emails": ["admin@veterinariaclinic.com"]
}
```

### 4. Ver Notificaciones de Usuario
```http
GET /notifications/user/<user_id>?unread_only=true
```

### 5. Marcar como Leída
```http
PUT /notifications/mark-read/<notification_id>
```
**Body:**
```json
{
  "user_id": "uuid-usuario"
}
```

### 6. Enviar Confirmación de Cita
```http
POST /notifications/send-confirmation
```
**Body:**
```json
{
  "email": "cliente@email.com",
  "phone": "+1234567890",
  "appointment_details": {
    "date": "2024-01-15",
    "time": "10:30",
    "veterinarian_name": "Dr. Pérez",
    "pet_name": "Firulais"
  }
}
```

### 7. Enviar Cancelación de Cita
```http
POST /notifications/send-cancellation
```

### 8. Test Email
```http
POST /notifications/test-email
```
**Body:**
```json
{
  "email": "test@email.com"
}
```

### 9. Test WhatsApp
```http
POST /notifications/test-whatsapp
```
**Body:**
```json
{
  "phone": "+1234567890"
}
```

### 10. Health Check
```http
GET /notifications/health
```

---

## 🔧 Health Checks Generales

Todos los servicios tienen endpoint de health check:
```http
GET /{service}/health
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "service": "nombre_del_servicio",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 📝 Notas Importantes

### Autenticación
- La mayoría de endpoints requieren token de autorización
- Incluir en headers: `Authorization: Bearer <token>`
- Obtener token mediante `/auth/login`

### Formatos de Fecha
- Fechas: `YYYY-MM-DD` (ejemplo: `2024-01-15`)
- Horas: `HH:MM` (ejemplo: `10:30`)
- Timestamps: ISO 8601 format

### UUIDs
- Todos los IDs son UUIDs v4
- Ejemplo: `123e4567-e89b-12d3-a456-426614174000`

### Códigos de Estado HTTP
- `200` - Éxito
- `201` - Creado exitosamente
- `400` - Error en petición
- `401` - No autorizado
- `404` - No encontrado
- `500` - Error interno del servidor

### Variables de Entorno Principales
```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=bocato0731
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=veterinary-system
REDIS_URL=redis://localhost:6379
```

---

## 🚀 Inicio Rápido

1. **Iniciar servicios:**
```bash
# Auth Service
cd microservices/auth_service && python main.py

# Appointment Service  
cd microservices/appointment_service && python main.py

# Medical Service
cd microservices/medical_service && python main.py

# Notification Service
cd microservices/notification_service && python main.py

# Inventory Service
cd microservices/inventory_service && python main.py
```

2. **Login inicial:**
```bash
curl -X POST http://localhost:5001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@veterinariaclinic.com","password":"admin123"}'
```

3. **Verificar servicios:**
```bash
curl http://localhost:5001/auth/health
curl http://localhost:5002/appointments/health
curl http://localhost:5003/notifications/health
curl http://localhost:5004/medical/health
curl http://localhost:5005/inventory/health
```