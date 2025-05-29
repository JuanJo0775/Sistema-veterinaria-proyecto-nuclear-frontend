# Makefile
.PHONY: help dev-up dev-down dev-build dev-logs clean test health

help: ## Mostrar ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

dev-build: ## Construir contenedores de desarrollo
	docker-compose -f docker-compose.dev.yml build

dev-up: ## Iniciar servicios de desarrollo
	chmod +x scripts/start_dev.sh
	./scripts/start_dev.sh

dev-down: ## Detener servicios de desarrollo
	chmod +x scripts/stop_dev.sh
	./scripts/stop_dev.sh

dev-logs: ## Ver logs de desarrollo
	docker-compose -f docker-compose.dev.yml logs -f

clean: ## Limpiar contenedores y volúmenes
	docker-compose -f docker-compose.dev.yml down -v
	docker system prune -f

health: ## Verificar estado de servicios
	@echo "🔍 Verificando servicios..."
	@curl -s http://localhost:5001/health | python -m json.tool || echo "❌ Auth Service no disponible"
	@curl -s http://localhost:5002/health | python -m json.tool || echo "❌ Appointment Service no disponible"
	@curl -s http://localhost:5003/health | python -m json.tool || echo "❌ Notification Service no disponible"
	@curl -s http://localhost:5004/health | python -m json.tool || echo "❌ Medical Service no disponible"
	@curl -s http://localhost:5005/health | python -m json.tool || echo "❌ Inventory Service no disponible"

test-auth: ## Probar endpoints de autenticación
	@echo "🧪 Probando Auth Service..."
	@echo "Health Check:"
	@curl -s http://localhost:5001/health | python -m json.tool || echo "❌ No disponible"

test-appointments: ## Probar endpoints de citas
	@echo "🧪 Probando Appointment Service..."
	@echo "Health Check:"
	@curl -s http://localhost:5002/health | python -m json.tool || echo "❌ No disponible"

test-notifications: ## Probar endpoints de notificaciones
	@echo "🧪 Probando Notification Service..."
	@echo "Health Check:"
	@curl -s http://localhost:5003/health | python -m json.tool || echo "❌ No disponible"

test-medical: ## Probar endpoints médicos
	@echo "🧪 Probando Medical Service..."
	@echo "Health Check:"
	@curl -s http://localhost:5004/health | python -m json.tool || echo "❌ No disponible"

test-inventory: ## Probar endpoints de inventario
	@echo "🧪 Probando Inventory Service..."
	@echo "Health Check:"
	@curl -s http://localhost:5005/health | python -m json.tool || echo "❌ No disponible"

setup: ## Configurar permisos y estructura inicial
	chmod +x scripts/*.sh
	@echo "✅ Permisos configurados"