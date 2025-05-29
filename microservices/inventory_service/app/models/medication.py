# microservices/inventory_service/app/models/medication.py
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime, date, timedelta

db = SQLAlchemy()


class Medication(db.Model):
    __tablename__ = 'medications'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    expiration_date = db.Column(db.Date)
    supplier = db.Column(db.String(255))
    minimum_stock_alert = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Campos adicionales
    category = db.Column(db.String(100))  # Antibiótico, Analgésico, etc.
    presentation = db.Column(db.String(100))  # Comprimidos, Jarabe, etc.
    concentration = db.Column(db.String(50))  # 500mg, 250mg/5ml, etc.
    laboratory = db.Column(db.String(255))
    batch_number = db.Column(db.String(50))
    storage_conditions = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    # Relaciones
    stock_movements = db.relationship('StockMovement', backref='medication', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'stock_quantity': self.stock_quantity,
            'unit_price': float(self.unit_price) if self.unit_price else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'supplier': self.supplier,
            'minimum_stock_alert': self.minimum_stock_alert,
            'category': self.category,
            'presentation': self.presentation,
            'concentration': self.concentration,
            'laboratory': self.laboratory,
            'batch_number': self.batch_number,
            'storage_conditions': self.storage_conditions,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'days_to_expiration': self.get_days_to_expiration(),
            'stock_status': self.get_stock_status()
        }

    def get_days_to_expiration(self):
        """Calcular días hasta vencimiento"""
        if self.expiration_date:
            delta = self.expiration_date - date.today()
            return delta.days
        return None

    def get_stock_status(self):
        """Obtener estado del stock"""
        if self.stock_quantity <= 0:
            return 'out_of_stock'
        elif self.stock_quantity <= self.minimum_stock_alert:
            return 'low_stock'
        else:
            return 'in_stock'

    def is_near_expiration(self, days_threshold=30):
        """Verificar si está próximo a vencer"""
        days_to_exp = self.get_days_to_expiration()
        return days_to_exp is not None and 0 <= days_to_exp <= days_threshold

    def is_expired(self):
        """Verificar si está vencido"""
        if self.expiration_date:
            return self.expiration_date < date.today()
        return False

    @classmethod
    def get_low_stock_medications(cls):
        """Obtener medicamentos con stock bajo"""
        return cls.query.filter(
            cls.is_active == True,
            cls.stock_quantity <= cls.minimum_stock_alert
        ).all()

    @classmethod
    def get_expiring_medications(cls, days_threshold=30):
        """Obtener medicamentos próximos a vencer"""
        expiration_limit = date.today() + timedelta(days=days_threshold)
        return cls.query.filter(
            cls.is_active == True,
            cls.expiration_date <= expiration_limit,
            cls.expiration_date >= date.today()
        ).all()

    @classmethod
    def search_medications(cls, search_term):
        """Buscar medicamentos por nombre, categoría o laboratorio"""
        return cls.query.filter(
            cls.is_active == True,
            db.or_(
                cls.name.ilike(f'%{search_term}%'),
                cls.category.ilike(f'%{search_term}%'),
                cls.laboratory.ilike(f'%{search_term}%'),
                cls.supplier.ilike(f'%{search_term}%')
            )
        ).all()


class StockMovement(db.Model):
    __tablename__ = 'stock_movements'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    medication_id = db.Column(db.String(36), db.ForeignKey('medications.id'), nullable=False)
    movement_type = db.Column(db.Enum('in', 'out', 'adjustment', name='movement_type_enum'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    previous_stock = db.Column(db.Integer, nullable=False)
    new_stock = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255))
    reference_id = db.Column(db.String(36))  # ID de prescripción, compra, etc.
    user_id = db.Column(db.String(36))  # Usuario que realizó el movimiento
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Campos adicionales
    unit_cost = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'medication_id': self.medication_id,
            'movement_type': self.movement_type,
            'quantity': self.quantity,
            'previous_stock': self.previous_stock,
            'new_stock': self.new_stock,
            'reason': self.reason,
            'reference_id': self.reference_id,
            'user_id': self.user_id,
            'unit_cost': float(self.unit_cost) if self.unit_cost else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def get_by_medication(cls, medication_id, limit=None):
        """Obtener movimientos de un medicamento"""
        query = cls.query.filter_by(medication_id=medication_id).order_by(cls.created_at.desc())
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_movements_by_date_range(cls, start_date=None, end_date=None):
        """Obtener movimientos por rango de fechas"""
        query = cls.query
        if start_date:
            query = query.filter(cls.created_at >= start_date)
        if end_date:
            query = query.filter(cls.created_at <= end_date)
        return query.order_by(cls.created_at.desc()).all()