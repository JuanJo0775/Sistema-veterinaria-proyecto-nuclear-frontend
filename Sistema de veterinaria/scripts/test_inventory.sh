#!/bin/bash
# scripts/test_inventory.sh

echo "🧪 Probando Inventory Service..."

# Test de health check
echo "1. Health Check:"
curl -s http://localhost:5005/health | python -m json.tool

echo -e "\n2. Crear medicamento:"
RESPONSE=$(curl -s -X POST http://localhost:5005/inventory/medications \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ibuprofeno 400mg",
    "description": "Antiinflamatorio no esteroideo",
    "stock_quantity": 50,
    "unit_price": 1200,
    "expiration_date": "2025-06-15",
    "supplier": "Laboratorios Farmacéuticos SA",
    "minimum_stock_alert": 15,
    "category": "Analgésico",
    "presentation": "Comprimidos",
    "concentration": "400mg",
    "laboratory": "LabFarma",
    "batch_number": "LOT2024001",
    "storage_conditions": "Mantener en lugar fresco y seco"
  }')

echo $RESPONSE | python -m json.tool

# Extraer medication_id de la respuesta
MED_ID=$(echo $RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['medication']['id'])" 2>/dev/null || echo "test-med-id")

echo -e "\n3. Obtener información del medicamento:"
curl -s http://localhost:5005/inventory/medications/$MED_ID | python -m json.tool

echo -e "\n4. Buscar medicamentos:"
curl -s "http://localhost:5005/inventory/medications/search?q=Ibuprofeno" | python -m json.tool

echo -e "\n5. Agregar stock (compra):"
curl -s -X POST http://localhost:5005/inventory/add-stock \
  -H "Content-Type: application/json" \
  -d "{
    \"medication_id\": \"$MED_ID\",
    \"quantity\": 25,
    \"reason\": \"Compra a proveedor\",
    \"unit_cost\": 1150,
    \"user_id\": \"admin-user\"
  }" | python -m json.tool

echo -e "\n6. Reducir stock (prescripción):"
curl -s -X POST http://localhost:5005/inventory/reduce-stock \
  -H "Content-Type: application/json" \
  -d "{
    \"medication_id\": \"$MED_ID\",
    \"quantity\": 5,
    \"reason\": \"Prescripción médica\",
    \"reference_id\": \"prescription-123\",
    \"user_id\": \"vet-user\"
  }" | python -m json.tool

echo -e "\n7. Ver movimientos de stock:"
curl -s "http://localhost:5005/inventory/movements?medication_id=$MED_ID" | python -m json.tool

echo -e "\n8. Crear medicamento con stock bajo:"
curl -s -X POST http://localhost:5005/inventory/medications \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Amoxicilina 250mg",
    "stock_quantity": 3,
    "unit_price": 2500,
    "minimum_stock_alert": 10,
    "category": "Antibiótico"
  }' | python -m json.tool

echo -e "\n9. Verificar alertas de stock bajo:"
curl -s http://localhost:5005/inventory/alerts/low-stock | python -m json.tool

echo -e "\n10. Crear medicamento próximo a vencer:"
TOMORROW=$(date -d "+1 day" +%Y-%m-%d)
curl -s -X POST http://localhost:5005/inventory/medications \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Medicina que vence pronto\",
    \"stock_quantity\": 10,
    \"unit_price\": 5000,
    \"expiration_date\": \"$TOMORROW\",
    \"category\": \"Test\"
  }" | python -m json.tool

echo -e "\n11. Verificar medicamentos próximos a vencer:"
curl -s "http://localhost:5005/inventory/alerts/expiring?days=5" | python -m json.tool

echo -e "\n12. Obtener resumen del inventario:"
curl -s http://localhost:5005/inventory/summary | python -m json.tool

echo -e "\n13. Obtener estadísticas:"
curl -s http://localhost:5005/inventory/stats | python -m json.tool

echo -e "\n14. Obtener categorías:"
curl -s http://localhost:5005/inventory/categories | python -m json.tool

echo -e "\n15. Generar reporte de movimientos:"
YESTERDAY=$(date -d "-1 day" +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)
curl -s "http://localhost:5005/inventory/reports/movements?start_date=$YESTERDAY&end_date=$TODAY" | python -m json.tool

echo -e "\n16. Verificar alertas automáticas de vencimiento:"
curl -s -X POST http://localhost:5005/inventory/alerts/check-expiration \
  -H "Content-Type: application/json" \
  -d '{
    "days_threshold": 5
  }' | python -m json.tool

echo -e "\n✅ Tests de Inventory Service completados!"
echo "📝 Medication ID creado: $MED_ID"