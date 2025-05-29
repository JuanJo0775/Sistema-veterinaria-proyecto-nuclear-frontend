# microservices/inventory_service/app/models/__init__.py
from .medication import Medication, StockMovement, db

__all__ = ['Medication', 'StockMovement', 'db']