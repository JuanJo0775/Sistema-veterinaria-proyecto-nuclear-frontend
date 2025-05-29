## 🔍 URLs de Servicios

- **Auth Service**: http://localhost:5001
- **Appointment Service**: http://localhost:5002
- **Notification Service**: http://localhost:5003
- **Medical Service**: http://localhost:5004
- **Inventory Service**: http://localhost:5005
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 📊 Health Checks

```bash
# Verificar todos los servicios
make health

# Servicios específicos
curl http://localhost:5001/health
curl http://localhost:5002/health
curl http://localhost:5003/health
curl http://localhost:5004/health
curl http://localhost:5005/health
```

## 🧪# Sistema de Gestión para Clínica Veterinaria

Sistema web integral para la gestión completa de una clínica veterinaria con arquitectura de microservicios.

## 🏗️ Arquitectura

- **Backend**: Python con Flask
- **Base de Datos**: PostgreSQL
- **Cache**: Redis
- **Arquitectura**: Microservicios
- **Contenedores**: Docker & Docker Compose

## 📋 Prerequisitos

- Docker y Docker Compose instalados
- Puerto 5432 (PostgreSQL), 6379 (Redis), 5001+ (microservicios) disponibles
- Git

## 🚀 Inicio Rápido

### 1. Clonar el repositorio
```bash
git clone <repository-url>
cd veterinary_clinic_system
```

### 2. Configurar permisos
```bash
make setup
```

### 3. Iniciar en modo desarrollo (todos los servicios)
```bash
make dev-up
```

### 4. Verificar servicios
```bash
make health
```

## 🔧 Ejecución de Microservicios

### Opción 1: Todos los servicios con Docker Compose (Recomendado)

```bash
# Iniciar todos los servicios
make dev-up

# Ver logs en tiempo real
make dev-logs

# Detener todos los servicios
make dev-down

# Limpiar contenedores y volúmenes
make clean
```

### Opción 2: Microservicios individuales

#### 📋 Prerequisitos para ejecución individual
```bash
# Instalar PostgreSQL y Redis localmente
sudo apt-get install postgresql redis-server  # Ubuntu/Debian
# O usar Docker solo para la base de datos:
docker run -d --name postgres-local -p 5432:5432 -e POSTGRES_DB=veterinary-system -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=bocato0731 postgres:15-alpine
docker run -d --name redis-local -p 6379:6379 redis:7-alpine
```

#### 🔐 Auth Service (Puerto 5001)

**Con Docker:**
```bash
# Construir imagen
docker build -t vet-auth-service ./microservices/auth_service/

# Ejecutar contenedor
docker run -d \
  --name vet-auth-service \
  -p 5001:5001 \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_DB=veterinary-system \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=bocato0731 \
  -e REDIS_URL=redis://host.docker.internal:6379/0 \
  -e FLASK_ENV=development \
  vet-auth-service

# Ver logs
docker logs -f vet-auth-service

# Detener
docker stop vet-auth-service && docker rm vet-auth-service
```

**Con Python (main.py):**
```bash
# Ir al directorio del servicio
cd microservices/auth_service

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
export POSTGRES_HOST=localhost
export POSTGRES_DB=veterinary-system
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=bocato0731
export REDIS_URL=redis://localhost:6379/0
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key-auth

# Ejecutar servicio
python main.py

# El servicio estará disponible en http://localhost:5001
```

#### 📅 Appointment Service (Puerto 5002)

**Con Docker:**
```bash
# Construir imagen
docker build -t vet-appointment-service ./microservices/appointment_service/

# Ejecutar contenedor
docker run -d \
  --name vet-appointment-service \
  -p 5002:5002 \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_DB=veterinary-system \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=bocato0731 \
  -e REDIS_URL=redis://host.docker.internal:6379/1 \
  -e FLASK_ENV=development \
  -e AUTH_SERVICE_URL=http://host.docker.internal:5001 \
  -e NOTIFICATION_SERVICE_URL=http://host.docker.internal:5003 \
  vet-appointment-service

# Ver logs
docker logs -f vet-appointment-service

# Detener
docker stop vet-appointment-service && docker rm vet-appointment-service
```

**Con Python (main.py):**
```bash
# Ir al directorio del servicio
cd microservices/appointment_service

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
export POSTGRES_HOST=localhost
export POSTGRES_DB=veterinary-system
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=bocato0731
export REDIS_URL=redis://localhost:6379/1
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key-appointment
export AUTH_SERVICE_URL=http://localhost:5001
export NOTIFICATION_SERVICE_URL=http://localhost:5003

# Ejecutar servicio
python main.py

# El servicio estará disponible en http://localhost:5002
```

#### 📧 Notification Service (Puerto 5003)

**Con Docker:**
```bash
# Construir imagen
docker build -t vet-notification-service ./microservices/notification_service/

# Ejecutar contenedor
docker run -d \
  --name vet-notification-service \
  -p 5003:5003 \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_DB=veterinary-system \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=bocato0731 \
  -e REDIS_URL=redis://host.docker.internal:6379/2 \
  -e FLASK_ENV=development \
  -e GMAIL_USER=dev@veterinariaclinic.com \
  -e GMAIL_PASSWORD=dev_password \
  vet-notification-service

# Ver logs
docker logs -f vet-notification-service

# Detener
docker stop vet-notification-service && docker rm vet-notification-service
```

**Con Python (main.py):**
```bash
# Ir al directorio del servicio
cd microservices/notification_service

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
export POSTGRES_HOST=localhost
export POSTGRES_DB=veterinary-system
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=bocato0731
export REDIS_URL=redis://localhost:6379/2
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key-notification
export GMAIL_USER=dev@veterinariaclinic.com
export GMAIL_PASSWORD=dev_password

# Ejecutar servicio
python main.py

# El servicio estará disponible en http://localhost:5003
```

#### 🏥 Medical Service (Puerto 5004)

**Con Docker:**
```bash
# Construir imagen
docker build -t vet-medical-service ./microservices/medical_service/

# Ejecutar contenedor
docker run -d \
  --name vet-medical-service \
  -p 5004:5004 \
  -v $(pwd)/uploads:/app/uploads \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_DB=veterinary-system \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=bocato0731 \
  -e REDIS_URL=redis://host.docker.internal:6379/3 \
  -e FLASK_ENV=development \
  -e UPLOAD_FOLDER=/app/uploads \
  vet-medical-service

# Ver logs
docker logs -f vet-medical-service

# Detener
docker stop vet-medical-service && docker rm vet-medical-service
```

**Con Python (main.py):**
```bash
# Ir al directorio del servicio
cd microservices/medical_service

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Crear directorio de uploads
mkdir -p uploads/pets uploads/exams

# Configurar variables de entorno
export POSTGRES_HOST=localhost
export POSTGRES_DB=veterinary-system
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=bocato0731
export REDIS_URL=redis://localhost:6379/3
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key-medical
export UPLOAD_FOLDER=./uploads
export INVENTORY_SERVICE_URL=http://localhost:5005

# Ejecutar servicio
python main.py

# El servicio estará disponible en http://localhost:5004
```

#### 💊 Inventory Service (Puerto 5005)

**Con Docker:**
```bash
# Construir imagen
docker build -t vet-inventory-service ./microservices/inventory_service/

# Ejecutar contenedor
docker run -d \
  --name vet-inventory-service \
  -p 5005:5005 \
  -e POSTGRES_HOST=host.docker.internal \
  -e POSTGRES_DB=veterinary-system \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=bocato0731 \
  -e REDIS_URL=redis://host.docker.internal:6379/4 \
  -e FLASK_ENV=development \
  -e NOTIFICATION_SERVICE_URL=http://host.docker.internal:5003 \
  vet-inventory-service

# Ver logs
docker logs -f vet-inventory-service

# Detener
docker stop vet-inventory-service && docker rm vet-inventory-service
```

**Con Python (main.py):**
```bash
# Ir al directorio del servicio
cd microservices/inventory_service

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
export POSTGRES_HOST=localhost
export POSTGRES_DB=veterinary-system
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=bocato0731
export REDIS_URL=redis://localhost:6379/4
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key-inventory
export NOTIFICATION_SERVICE_URL=http://localhost:5003
export AUTO_ALERTS_ENABLED=true

# Ejecutar servicio
python main.py

# El servicio estará disponible en http://localhost:5005
```

### 🔧 Scripts de Variables de Entorno

Para facilitar la configuración, puedes crear scripts de variables de entorno:

**scripts/set_env_auth.sh:**
```bash
#!/bin/bash
export POSTGRES_HOST=localhost
export POSTGRES_DB=veterinary-system
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=bocato0731
export REDIS_URL=redis://localhost:6379/0
export FLASK_ENV=development
export SECRET_KEY=dev-secret-key-auth
export JWT_SECRET_KEY=dev-jwt-secret-key
```

**Uso:**
```bash
# Hacer ejecutable
chmod +x scripts/set_env_auth.sh

# Cargar variables y ejecutar servicio
cd microservices/auth_service
source ../../scripts/set_env_auth.sh
python main.py
```

### 📊 Verificación de servicios individuales

```bash
# Health checks individuales
curl http://localhost:5001/health  # Auth Service
curl http://localhost:5002/health  # Appointment Service
curl http://localhost:5003/health  # Notification Service
curl http://localhost:5004/health  # Medical Service
curl http://localhost:5005/health  # Inventory Service

# Tests específicos
make test-auth
make test-appointments
make test-notifications
make test-medical
make test-inventory
```

### ⚠️ Notas importantes para ejecución individual

1. **Orden de inicio recomendado:**
   1. PostgreSQL y Redis
   2. Auth Service
   3. Notification Service
   4. Inventory Service
   5. Medical Service
   6. Appointment Service

2. **Dependencias entre servicios:**
   - Medical Service → Inventory Service (para actualizar stock)
   - Appointment Service → Notification Service (para alertas)
   - Todos los servicios → Auth Service (para autenticación)

3. **Puertos requeridos:**
   - 5432: PostgreSQL
   - 6379: Redis
   - 5001-5005: Microservicios

4. **Variables de entorno críticas:**
   - Configuración de base de datos debe ser consistente
   - URLs de servicios deben apuntar a las direcciones correctas
   - Redis debe usar diferentes bases de datos (0-4)

## 📁 Estructura del Proyecto enfocado en microservicios

```
veterinary_clinic_system/
├── microservices/           # Microservicios
│   ├── auth_service/       # Autenticación
│   ├── appointment_service/ # Citas
│   ├── notification_service/ # Notificaciones
│   ├── medical_service/    # Historias clínicas
│   └── inventory_service/  # Inventario
├── gateway/                # API Gateway y Frontend
├── database/              # Scripts SQL
├── scripts/               # Scripts de automatización
├── utils/                 # Utilidades compartidas
└── docker-compose.dev.yml # Configuración desarrollo
```

## 📁 Estructura completa

```
veterinary_clinic_system/
├── microservices/
│   ├── auth_service/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   └── user.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   └── auth_routes.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── auth_service.py
│   │   ├── config.py
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   └── Dockerfile
│   ├── appointment_service/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── appointment.py
│   │   │   │   └── schedule.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   └── appointment_routes.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── appointment_service.py
│   │   ├── config.py
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   └── Dockerfile
│   ├── notification_service/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   └── notification.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   └── notification_routes.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       ├── email_service.py
│   │   │       └── whatsapp_service.py
│   │   ├── config.py
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   └── Dockerfile
│   ├── medical_service/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── medical_record.py
│   │   │   │   └── pet.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   └── medical_routes.py
│   │   │   └── services/
│   │   │       ├── __init__.py
│   │   │       └── medical_service.py
│   │   ├── config.py
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   └── Dockerfile
│   └── inventory_service/
│       ├── app/
│       │   ├── __init__.py
│       │   ├── models/
│       │   │   ├── __init__.py
│       │   │   └── medication.py
│       │   ├── routes/
│       │   │   ├── __init__.py
│       │   │   └── inventory_routes.py
│       │   └── services/
│       │       ├── __init__.py
│       │       └── inventory_service.py
│       ├── config.py
│       ├── requirements.txt
│       ├── main.py
│       └── Dockerfile
├── gateway/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── gateway_routes.py
│   │   ├── templates/
│   │   │   ├── base.html
│   │   │   ├── index.html
│   │   │   ├── client/
│   │   │   │   └── dashboard.html
│   │   │   ├── veterinarian/
│   │   │   │   └── dashboard.html
│   │   │   ├── receptionist/
│   │   │   │   └── dashboard.html
│   │   │   ├── auxiliary/
│   │   │   │   └── dashboard.html
│   │   │   └── admin/
│   │   │       └── dashboard.html
│   │   ├── static/
│   │   │   ├── css/
│   │   │   │   └── style.css
│   │   │   ├── js/
│   │   │   │   └── main.js
│   │   │   └── images/
│   │   └── services/
│   │       ├── __init__.py
│   │       └── api_client.py
│   ├── config.py
│   ├── requirements.txt
│   ├── main.py
│   └── Dockerfile
├── database/
│   └── init.sql
├── scripts/
│   ├── start_dev.sh
│   ├── stop_dev.sh
│   ├── clean_dev.sh
│   ├── deploy_prod.sh
│   ├── backup.sh
│   └── generate_secrets.sh
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   ├── health_check.py
│   └── swagger_config.py
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.development
├── .env.production
├── Makefile
└── README.md
```

## 🐳 Comandos Docker

```bash
# Iniciar desarrollo
make dev-up

# Ver logs
make dev-logs

# Detener servicios
make dev-down

# Limpiar todo
make clean

# Construir contenedores
make dev-build
```

## 🔍 URLs de Servicios

- **Auth Service**: http://localhost:5001
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 📊 Health Checks

```bash
# Verificar todos los servicios
make health

# Auth Service específico
curl http://localhost:5001/health
```

## 🗄️ Base de Datos

### Conexión
- **Host**: localhost
- **Puerto**: 5432
- **Base de datos**: veterinary-system
- **Usuario**: postgres
- **Contraseña**: bocato0731

### Usuario administrador por defecto
- **Email**: admin@veterinariaclinic.com
- **Contraseña**: admin123

## 🧪 Testing Auth Service

### Registro de usuario
```bash
curl -X POST http://localhost:5001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@test.com",
    "password": "password123",
    "first_name": "Test",
    "last_name": "User",
    "phone": "+1234567890",
    "role": "client"
  }'
```

### Login
```bash
curl -X POST http://localhost:5001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@test.com",
    "password": "password123"
  }'
```



### Variables de entorno
- `.env.development` - Desarrollo
- `.env.production` - Producción

## 📝 Próximos Pasos

1. ✅ Auth Service implementado
2. ✅ Appointment Service
3. ✅ Notification Service  
4. ✅ Medical Service
5. ✅ Inventory Service
6. ⏳ Probar y ejecutar 
7. ⏳ Gateway con Frontend

## 🐛 Troubleshooting

### Puerto ocupado
```bash
sudo lsof -i :5432  # PostgreSQL
sudo lsof -i :5001  # Auth Service
```

### Logs de contenedor específico
```bash
docker-compose -f docker-compose.dev.yml logs auth_service
```

### Recrear base de datos
```bash
make clean
make dev-up
```