#!/bin/bash
# scripts/test_medical.sh

echo "🧪 Probando Medical Service..."

# Test de health check
echo "1. Health Check:"
curl -s http://localhost:5004/health | python -m json.tool

echo -e "\n2. Crear mascota:"
RESPONSE=$(curl -s -X POST http://localhost:5004/medical/pets \
  -H "Content-Type: application/json" \
  -d '{
    "owner_id": "test-owner-id",
    "name": "Luna",
    "species": "Gato",
    "breed": "Persa",
    "birth_date": "2020-03-15",
    "weight": 4.5,
    "gender": "Hembra",
    "allergies": "Ninguna conocida",
    "vaccination_status": "Al día"
  }')

echo $RESPONSE | python -m json.tool

# Extraer pet_id de la respuesta
PET_ID=$(echo $RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['pet']['id'])" 2>/dev/null || echo "test-pet-id")

echo -e "\n3. Obtener información de mascota:"
curl -s http://localhost:5004/medical/pets/$PET_ID | python -m json.tool

echo -e "\n4. Buscar mascotas:"
curl -s "http://localhost:5004/medical/pets/search?q=Luna" | python -m json.tool

echo -e "\n5. Crear historia clínica:"
RECORD_RESPONSE=$(curl -s -X POST http://localhost:5004/medical/records \
  -H "Content-Type: application/json" \
  -d "{
    \"pet_id\": \"$PET_ID\",
    \"veterinarian_id\": \"test-vet-id\",
    \"symptoms_description\": \"Pérdida de apetito y letargo\",
    \"physical_examination\": \"Temperatura normal, ganglios sin alteraciones\",
    \"diagnosis\": \"Infección gastrointestinal leve\",
    \"treatment\": \"Dieta blanda y medicación\",
    \"weight_at_visit\": 4.3,
    \"temperature\": 38.5
  }")

echo $RECORD_RESPONSE | python -m json.tool

# Extraer record_id
RECORD_ID=$(echo $RECORD_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['medical_record']['id'])" 2>/dev/null || echo "test-record-id")

echo -e "\n6. Agregar prescripción:"
curl -s -X POST http://localhost:5004/medical/prescriptions \
  -H "Content-Type: application/json" \
  -d "{
    \"medical_record_id\": \"$RECORD_ID\",
    \"medication_name\": \"Amoxicilina 250mg\",
    \"dosage\": \"1 comprimido\",
    \"frequency\": \"Cada 12 horas\",
    \"duration\": \"7 días\",
    \"quantity_prescribed\": 14,
    \"instructions\": \"Administrar con comida\"
  }" | python -m json.tool

echo -e "\n7. Obtener historias clínicas de la mascota:"
curl -s http://localhost:5004/medical/records/pet/$PET_ID | python -m json.tool

echo -e "\n8. Obtener resumen médico:"
curl -s http://localhost:5004/medical/summary/pet/$PET_ID | python -m json.tool

echo -e "\n9. Completar historia clínica:"
curl -s -X PUT http://localhost:5004/medical/records/$RECORD_ID/complete | python -m json.tool

echo -e "\n✅ Tests de Medical Service completados!"
echo "📝 Pet ID creado: $PET_ID"
echo "📝 Record ID creado: $RECORD_ID"