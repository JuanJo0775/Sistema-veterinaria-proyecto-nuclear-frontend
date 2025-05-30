# 🐾 Sistema de Gestión para Clínica Veterinaria

Sistema web integral para la gestión completa de una clínica veterinaria con arquitectura de microservicios.

## 🏗️ Arquitectura

- **Backend**: Python con Flask
- **Base de Datos**: PostgreSQL
- **Cache**: Redis
- **Arquitectura**: Microservicios
- **Contenedores**: Docker & Docker Compose

## 📋 Prerequisitos

- Python 3.11+
- PostgreSQL y Redis (locales o en Docker)
- Puerto 5432 (PostgreSQL), 6379 (Redis), 5001-5005 (microservicios) disponibles

## 🚀 Formas de Ejecutar el Sistema

### **Opción 1: Main Principal (🌟 RECOMENDADO para desarrollo)**

Esta es la forma más fácil de ejecutar todos los microservicios desde un solo comando:

```bash
# 1. Instalar dependencias principales
pip install -r requirements.txt

# 2. Asegurar que PostgreSQL y Redis estén ejecutándose
# PostgreSQL:
docker run -d --name postgres-local -p 5432:5432 \
  -e POSTGRES_DB=veterinary-system \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=bocato0731 \
  postgres:15-alpine

# Redis:
docker run -d --name redis-local -p 6379:6379 redis:7-alpine

# 3. Ejecutar todos los microservicios
python main_principal.py
```

**¿Qué hace el main principal?**
- ✅ Verifica que PostgreSQL y Redis estén disponibles
- ✅ Configura automáticamente todas las variables de entorno
- ✅ Inicia los 5 microservicios en el orden correcto
- ✅ Monitorea el estado de cada servicio
- ✅ Muestra logs en tiempo real de todos los servicios
- ✅ Maneja el cierre limpio con Ctrl+C

### **Opción 2: Versión Simplificada**

Si prefieres una versión más simple sin monitoreo avanzado:

```bash
python start_all.py
```

### **Opción 3: Docker Compose (Para producción)**

```bash
# Iniciar todos los servicios con Docker
make dev-up

# Ver logs
make dev-logs

# Detener
make dev-down
```

### **Opción 4: Microservicios Individuales**

```bash
# Usando scripts de ayuda
./scripts/run_service.sh auth
./scripts/run_service.sh appointment
./scripts/run_service.sh medical
./scripts/run_service.sh notification
./scripts/run_service.sh inventory

# O manualmente
cd microservices/auth_service && python main_principal.py
cd microservices/appointment_service && python main_principal.py
# ... etc
```

## 🔍 URLs de Servicios

Cuando el sistema esté ejecutándose, tendrás acceso a:

- **Auth Service**: http://localhost:5001
- **Appointment Service**: http://localhost:5002
- **Notification Service**: http://localhost:5003
- **Medical Service**: http://localhost:5004
- **Inventory Service**: http://localhost:5005

## 📊 Verificar que todo funciona

```bash
# Health checks de todos los servicios
curl http://localhost:5001/health  # Auth Service
curl http://localhost:5002/health  # Appointment Service
curl http://localhost:5003/health  # Notification Service
curl http://localhost:5004/health  # Medical Service
curl http://localhost:5005/health  # Inventory Service

# O usar el comando make
make health
```

## 🗄️ Base de Datos

### Configuración por defecto
- **Host**: localhost:5432
- **Base de datos**: veterinary-system
- **Usuario**: postgres
- **Contraseña**: bocato0731

### Usuario administrador
- **Email**: admin@veterinariaclinic.com
- **Contraseña**: admin123

## 🧪 Pruebas Rápidas

### Registrar un usuario
```bash
curl -X POST http://localhost:5001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@test.com",
    "password": "password123",
    "first_name": "Test",
    "last_name": "User",
    "role": "client"
  }'
```

### Hacer login
```bash
curl -X POST http://localhost:5001/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@test.com",
    "password": "password123"
  }'
```

## 📁 Estructura del Proyecto

```
veterinary_clinic_system/
├── main_principal.py                    # 🌟 EJECUTOR PRINCIPAL
├── start_all.py              # Versión simplificada
├── requirements.txt          # Dependencias principales
├── microservices/           # Microservicios
│   ├── auth_service/        # Autenticación (Puerto 5001)
│   ├── appointment_service/ # Citas (Puerto 5002) 
│   ├── notification_service/# Notificaciones (Puerto 5003)
│   ├── medical_service/     # Historias clínicas (Puerto 5004)
│   └── inventory_service/   # Inventario (Puerto 5005)
├── scripts/                 # Scripts de ayuda
├── utils/                   # Utilidades compartidas
└── docker-compose.dev.yml  # Para Docker
```

## 📁 Estructura del Proyecto total

```
veterinary_clinic_system/
├── veterinary_console_app.py          # 🎮 Aplicación principal de testing
├── main_principal.py                  # 🚀 Gestor de microservicios (alternativo)
├── start_all.py                      # 🔧 Iniciador simple de servicios
├── requirements.txt                   # 📦 Dependencias globales
├── README.md                         # 📖 Esta documentación
│
├── microservices/                    # 🏗️ Microservicios
│   ├── auth_service/                 # 🔐 Servicio de Autenticación
│   │   ├── app/
│   │   │   ├── models/user.py
│   │   │   ├── routes/auth_routes.py
│   │   │   └── services/auth_service.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── medical_service/              # 🏥 Servicio Médico
│   │   ├── app/
│   │   │   ├── models/
│   │   │   │   ├── pet.py
│   │   │   │   └── medical_record.py
│   │   │   ├── routes/medical_routes.py
│   │   │   └── services/medical_service.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── inventory_service/            # 📦 Servicio de Inventario
│   │   ├── app/
│   │   │   ├── models/medication.py
│   │   │   ├── routes/inventory_routes.py
│   │   │   └── services/inventory_service.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── appointment_service/          # 📅 Servicio de Citas
│   │   ├── app/
│   │   │   ├── models/
│   │   │   │   ├── appointment.py
│   │   │   │   └── schedule.py
│   │   │   ├── routes/appointment_routes.py
│   │   │   └── services/appointment_service.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── notification_service/         # 📧 Servicio de Notificaciones
│       ├── app/
│       │   ├── models/notification.py
│       │   ├── routes/notification_routes.py
│       │   └── services/
│       │       ├── email_service.py
│       │       └── whatsapp_service.py
│       ├── main.py
│       ├── config.py
│       ├── requirements.txt
│       └── Dockerfile
│
├── database/                         # 🗄️ Base de Datos
│   └── init.sql                     # Script de inicialización
│
├── utils/                           # 🔧 Utilidades
│   ├── logger.py
│   └── health_check.py
│
├── scripts/                         # 📜 Scripts auxiliares
│   ├── start_dev.sh
│   ├── stop_dev.sh
│   ├── test_*.sh
│   └── insert_sample_data.sh
│
├── docker-compose.yml               # 🐳 Docker Compose producción
├── docker-compose.dev.yml          # 🐳 Docker Compose desarrollo
└── Makefile                        # ⚙️ Automatización de tareas
```

## 🚀 Inicio Rápido - 3 Pasos

1. **Preparar base de datos:**
   ```bash
   docker run -d --name postgres-local -p 5432:5432 -e POSTGRES_DB=veterinary-system -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=bocato0731 postgres:15-alpine
   docker run -d --name redis-local -p 6379:6379 redis:7-alpine
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecutar sistema:**
   ```bash
   python main_principal.py
   ```

¡Eso es todo! El sistema estará disponible en los puertos 5001-5005.

## 🔧 Comandos Útiles

```bash
# Ver estado de todos los servicios
make health

# Limpiar y reiniciar todo
make clean && make dev-up

# Ver logs específicos
docker logs vet_auth_service_dev

# Conectar a la base de datos
docker exec -it postgres-local psql -U postgres -d veterinary-system
```

## 🐛 Troubleshooting

### Puerto ocupado
```bash
# Ver qué está usando el puerto
lsof -i :5001
netstat -tulpn | grep 5001

# Matar proceso específico
kill -9 <PID>
```

### Reiniciar base de datos
```bash
docker rm -f postgres-local redis-local
# Luego ejecutar los comandos de inicio de nuevo
```

### Logs del main principal
Cuando ejecutas `python main.py`, verás logs de todos los servicios en tiempo real:
```
[10:30:15] [Auth Service] 🚀 Auth Service iniciado en puerto 5001
[10:30:18] [Appointment Service] 🚀 Appointment Service iniciado en puerto 5002
...
```

## 🎯 Próximos Pasos

1. ✅ Todos los microservicios funcionando
2. ✅ Main principal para ejecutar todo
3. ⏳ Gateway con interfaz web
4. ⏳ Autenticación completa entre servicios
5. ⏳ Tests automatizados

---

**¿Problemas?** Abre un issue o revisa la documentación en `/docs`