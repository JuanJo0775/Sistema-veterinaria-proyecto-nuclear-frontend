#!/bin/bash
# scripts/test_individual_services.sh
# Script para probar que los servicios funcionan individualmente

echo "🧪 Probando microservicios individuales..."
echo "=========================================="

# Función para verificar si un servicio está ejecutándose
check_service() {
    local port=$1
    local service_name=$2
    local max_attempts=30
    local attempt=0

    echo "⏳ Esperando que $service_name esté disponible en puerto $port..."

    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:$port/health > /dev/null 2>&1; then
            echo "✅ $service_name está ejecutándose"
            return 0
        fi

        attempt=$((attempt + 1))
        sleep 2
    done

    echo "❌ $service_name no está disponible después de $max_attempts intentos"
    return 1
}

# Función para probar un endpoint
test_endpoint() {
    local url=$1
    local description=$2
    local method=${3:-GET}
    local data=$4

    echo "🔍 Probando: $description"

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "%{http_code}" -o /dev/null "$url")
    else
        response=$(curl -s -w "%{http_code}" -o /dev/null -X "$method" -H "Content-Type: application/json" -d "$data" "$url")
    fi

    if [ "$response" = "200" ] || [ "$response" = "201" ]; then
        echo "✅ $description - HTTP $response"
    else
        echo "❌ $description - HTTP $response"
    fi
}

echo ""
echo "📋 Prerequisitos:"
echo "1. PostgreSQL ejecutándose en localhost:5432"
echo "2. Redis ejecutándose en localhost:6379"
echo "3. Base de datos 'veterinary-system' creada"
echo ""

# Verificar PostgreSQL
if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "✅ PostgreSQL está ejecutándose"
else
    echo "❌ PostgreSQL no está disponible"
    echo "💡 Ejecuta: docker run -d --name postgres-local -p 5432:5432 -e POSTGRES_DB=veterinary-system -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=bocato0731 postgres:15-alpine"
    exit 1
fi

# Verificar Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis está ejecutándose"
else
    echo "❌ Redis no está disponible"
    echo "💡 Ejecuta: docker run -d --name redis-local -p 6379:6379 redis:7-alpine"
    exit 1
fi

echo ""
echo "🚀 Instrucciones para probar:"
echo "1. Abre 5 terminales diferentes"
echo "2. En cada terminal, ejecuta uno de estos comandos:"
echo ""
echo "Terminal 1 (Auth Service):"
echo "cd microservices/auth_service && python main.py"
echo ""
echo "Terminal 2 (Appointment Service):"
echo "cd microservices/appointment_service && python main.py"
echo ""
echo "Terminal 3 (Medical Service):"
echo "cd microservices/medical_service && python main.py"
echo ""
echo "Terminal 4 (Notification Service):"
echo "cd microservices/notification_service && python main.py"
echo ""
echo "Terminal 5 (Inventory Service):"
echo "cd microservices/inventory_service && python main.py"
echo ""
echo "O usa los scripts de ayuda:"
echo "scripts/run_service.sh auth"
echo "scripts/run_service.sh appointment"
echo "scripts/run_service.sh medical"
echo "scripts/run_service.sh notification"
echo "scripts/run_service.sh inventory"
echo ""

# Verificar si los servicios están ejecutándose
echo "🔍 Verificando servicios..."
services_running=0

if check_service 5001 "Auth Service"; then
    services_running=$((services_running + 1))
    test_endpoint "http://localhost:5001/health" "Auth Service Health Check"
fi

if check_service 5002 "Appointment Service"; then
    services_running=$((services_running + 1))
    test_endpoint "http://localhost:5002/health" "Appointment Service Health Check"
fi

if check_service 5003 "Notification Service"; then
    services_running=$((services_running + 1))
    test_endpoint "http://localhost:5003/health" "Notification Service Health Check"
fi

if check_service 5004 "Medical Service"; then
    services_running=$((services_running + 1))
    test_endpoint "http://localhost:5004/health" "Medical Service Health Check"
fi

if check_service 5005 "Inventory Service"; then
    services_running=$((services_running + 1))
    test_endpoint "http://localhost:5005/health" "Inventory Service Health Check"
fi

echo ""
echo "📊 Resumen:"
echo "Servicios ejecutándose: $services_running/5"

if [ $services_running -eq 5 ]; then
    echo "🎉 ¡Todos los servicios están funcionando correctamente!"

    echo ""
    echo "🧪 Ejecutando pruebas básicas..."

    # Probar registro de usuario
    test_endpoint "http://localhost:5001/auth/register" "Registro de usuario" "POST" '{
        "email": "test@example.com",
        "password": "password123",
        "first_name": "Test",
        "last_name": "User",
        "role": "client"
    }'

    # Probar login
    test_endpoint "http://localhost:5001/auth/login" "Login de usuario" "POST" '{
        "email": "test@example.com",
        "password": "password123"
    }'

    echo ""
    echo "✅ ¡Sistema listo para usar!"
else
    echo "⚠️  Algunos servicios no están ejecutándose"
    echo "Verifica que todos los servicios estén iniciados correctamente"
fi