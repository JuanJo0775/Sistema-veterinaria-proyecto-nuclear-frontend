#!/bin/bash
# scripts/stop_dev.sh

echo "🛑 Deteniendo servicios de desarrollo..."
docker-compose -f docker-compose.dev.yml down

echo "✅ Servicios detenidos correctamente!"