#!/bin/bash
# scripts/start_dev.sh

echo "🚀 Iniciando Clínica Veterinaria en modo desarrollo..."

# Verificar si Docker está ejecutándose
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker no está ejecutándose. Por favor inicia Docker primero."
    exit 1
fi

# Crear red si no existe
docker network create vet_clinic_dev_network 2>/dev/null || true

# Construir y levantar servicios
echo "📦 Construyendo contenedores..."
docker-compose -f docker-compose.dev.yml build

echo "🔄 Iniciando servicios..."
docker-compose -f docker-compose.dev.yml up -d

# Esperar a que la base de datos esté lista
echo "⏳ Esperando a que la base de datos esté lista..."
sleep 15

echo "✅ Servicios iniciados correctamente!"
echo ""
echo "🌐 URLs de los servicios:"
echo "  Auth Service: http://localhost:5001"
echo "  Appointment Service: http://localhost:5002"
echo "  Notification Service: http://localhost:5003"
echo "  Medical Service: http://localhost:5004"
echo "  Inventory Service: http://localhost:5005"
echo "  PostgreSQL: localhost:5432"
echo "  Redis: localhost:6379"
echo ""
echo "📊 Monitoreo:"
echo "  Auth Health Check: http://localhost:5001/health"
echo "  Appointment Health Check: http://localhost:5002/health"
echo "  Notification Health Check: http://localhost:5003/health"
echo "  Medical Health Check: http://localhost:5004/health"
echo "  Inventory Health Check: http://localhost:5005/health"
echo ""
echo "🛑 Para detener: ./scripts/stop_dev.sh"