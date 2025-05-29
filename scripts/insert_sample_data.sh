#!/bin/bash
# scripts/insert_sample_data.sh

echo "📦 Insertando datos de ejemplo..."

# Crear veterinario de ejemplo
echo "Creando veterinario de ejemplo..."
curl -X POST http://localhost:5001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "vet@veterinariaclinic.com",
    "password": "vet123",
    "first_name": "Dr. Juan",
    "last_name": "Pérez",
    "phone": "+1234567891",
    "role": "veterinarian"
  }'

echo -e "\n"

# Crear cliente de ejemplo
echo "Creando cliente de ejemplo..."
curl -X POST http://localhost:5001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "cliente@example.com",
    "password": "cliente123",
    "first_name": "María",
    "last_name": "García",
    "phone": "+1234567892",
    "role": "client"
  }'

echo -e "\n"

# Obtener ID del veterinario (necesitarás ajustar esto)
echo "Para insertar horarios del veterinario, ejecuta estas consultas SQL:"
echo "1. Conectar a la base de datos:"
echo "   docker exec -it vet_clinic_db_dev psql -U postgres -d veterinary-system"
echo ""
echo "2. Obtener ID del veterinario:"
echo "   SELECT id, email FROM users WHERE role = 'veterinarian';"
echo ""
echo "3. Insertar horarios (reemplaza VET_ID con el ID obtenido):"
echo "   INSERT INTO veterinarian_schedules (veterinarian_id, day_of_week, start_time, end_time) VALUES"
echo "   ('VET_ID', 1, '08:00', '17:00'),"  # Lunes
echo "   ('VET_ID', 2, '08:00', '17:00'),"  # Martes
echo "   ('VET_ID', 3, '08:00', '17:00'),"  # Miércoles
echo "   ('VET_ID', 4, '08:00', '17:00'),"  # Jueves
echo "   ('VET_ID', 5, '08:00', '16:00');"  # Viernes
echo ""
echo "4. Crear mascota de ejemplo (reemplaza CLIENT_ID):"
echo "   INSERT INTO pets (owner_id, name, species, breed, weight, gender) VALUES"
echo "   ('CLIENT_ID', 'Firulais', 'Perro', 'Labrador', 25.5, 'Macho');"

echo -e "\n✅ Datos de ejemplo creados!"