# microservices/inventory_service/app/services/inventory_service.py
from datetime import datetime, date, timedelta
import requests
from flask import current_app
from ..models.medication import Medication, StockMovement, db


class InventoryService:

    def __init__(self):
        self.notification_service_url = None

    def init_app(self, app):
        self.notification_service_url = app.config.get('NOTIFICATION_SERVICE_URL')

    # =============== MEDICATION MANAGEMENT ===============

    def create_medication(self, medication_data):
        """Crear nuevo medicamento"""
        medication = Medication(
            name=medication_data.get('name'),
            description=medication_data.get('description'),
            stock_quantity=medication_data.get('stock_quantity', 0),
            unit_price=medication_data.get('unit_price'),
            expiration_date=datetime.strptime(medication_data.get('expiration_date'),
                                              '%Y-%m-%d').date() if medication_data.get('expiration_date') else None,
            supplier=medication_data.get('supplier'),
            minimum_stock_alert=medication_data.get('minimum_stock_alert', 10),
            category=medication_data.get('category'),
            presentation=medication_data.get('presentation'),
            concentration=medication_data.get('concentration'),
            laboratory=medication_data.get('laboratory'),
            batch_number=medication_data.get('batch_number'),
            storage_conditions=medication_data.get('storage_conditions')
        )

        db.session.add(medication)
        db.session.commit()

        # Registrar movimiento inicial si hay stock
        if medication.stock_quantity > 0:
            self._record_stock_movement(
                medication.id,
                'in',
                medication.stock_quantity,
                0,
                medication.stock_quantity,
                'Inventario inicial',
                user_id=medication_data.get('created_by')
            )

        return medication

    def get_medication_by_id(self, medication_id):
        """Obtener medicamento por ID"""
        return Medication.query.get(medication_id)

    def get_all_medications(self, include_inactive=False):
        """Obtener todos los medicamentos"""
        query = Medication.query
        if not include_inactive:
            query = query.filter_by(is_active=True)
        return query.order_by(Medication.name).all()

    def update_medication(self, medication_id, medication_data):
        """Actualizar información de medicamento"""
        medication = Medication.query.get(medication_id)
        if not medication:
            return None

        # Actualizar campos permitidos
        for key, value in medication_data.items():
            if key == 'expiration_date' and value:
                medication.expiration_date = datetime.strptime(value, '%Y-%m-%d').date()
            elif hasattr(medication, key) and key not in ['id', 'stock_quantity', 'created_at']:
                setattr(medication, key, value)

        db.session.commit()
        return medication

    def search_medications(self, search_term):
        """Buscar medicamentos"""
        return Medication.search_medications(search_term)

    def deactivate_medication(self, medication_id):
        """Desactivar medicamento"""
        medication = Medication.query.get(medication_id)
        if medication:
            medication.is_active = False
            db.session.commit()
            return medication
        return None

    # =============== STOCK MANAGEMENT ===============

    def update_stock(self, medication_id, quantity_change, reason, reference_id=None, user_id=None):
        """Actualizar stock de medicamento"""
        medication = Medication.query.get(medication_id)
        if not medication:
            return None

        previous_stock = medication.stock_quantity
        new_stock = previous_stock + quantity_change

        # Validar que no sea negativo
        if new_stock < 0:
            raise ValueError("Stock insuficiente")

        # Actualizar stock
        medication.stock_quantity = new_stock

        # Determinar tipo de movimiento
        movement_type = 'in' if quantity_change > 0 else 'out'
        if reason == 'adjustment':
            movement_type = 'adjustment'

        # Registrar movimiento
        movement = self._record_stock_movement(
            medication_id,
            movement_type,
            abs(quantity_change),
            previous_stock,
            new_stock,
            reason,
            reference_id,
            user_id
        )

        db.session.commit()

        # Verificar alertas
        self._check_stock_alerts(medication)

        return {
            'medication': medication,
            'movement': movement,
            'previous_stock': previous_stock,
            'new_stock': new_stock
        }

    def add_stock(self, medication_id, quantity, reason, unit_cost=None, user_id=None):
        """Agregar stock (compra, donación, etc.)"""
        result = self.update_stock(medication_id, quantity, reason, user_id=user_id)

        # Actualizar costo unitario si se proporciona
        if unit_cost and result:
            medication = result['medication']
            medication.unit_price = unit_cost

            # Actualizar el movimiento con el costo
            movement = result['movement']
            movement.unit_cost = unit_cost

            db.session.commit()

        return result

    def reduce_stock(self, medication_id, quantity, reason, reference_id=None, user_id=None):
        """Reducir stock (prescripción, vencimiento, etc.)"""
        return self.update_stock(medication_id, -quantity, reason, reference_id, user_id)

    def _record_stock_movement(self, medication_id, movement_type, quantity, previous_stock, new_stock, reason,
                               reference_id=None, user_id=None):
        """Registrar movimiento de stock"""
        movement = StockMovement(
            medication_id=medication_id,
            movement_type=movement_type,
            quantity=quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reason=reason,
            reference_id=reference_id,
            user_id=user_id
        )

        db.session.add(movement)
        return movement

    def get_stock_movements(self, medication_id=None, start_date=None, end_date=None, limit=None):
        """Obtener movimientos de stock"""
        if medication_id:
            return StockMovement.get_by_medication(medication_id, limit)
        else:
            return StockMovement.get_movements_by_date_range(start_date, end_date)

    # =============== ALERTS AND NOTIFICATIONS ===============

    def _check_stock_alerts(self, medication):
        """Verificar y enviar alertas de stock"""
        if not current_app.config.get('AUTO_ALERTS_ENABLED', True):
            return

        # Alerta de stock bajo
        if medication.get_stock_status() == 'low_stock':
            self._send_low_stock_alert(medication)

    def check_expiration_alerts(self, days_threshold=30):
        """Verificar medicamentos próximos a vencer"""
        expiring_medications = Medication.get_expiring_medications(days_threshold)

        if expiring_medications:
            self._send_expiration_alert(expiring_medications)

        return expiring_medications

    def get_low_stock_medications(self):
        """Obtener medicamentos con stock bajo"""
        return Medication.get_low_stock_medications()

    def get_expiring_medications(self, days_threshold=30):
        """Obtener medicamentos próximos a vencer"""
        return Medication.get_expiring_medications(days_threshold)

    def _send_low_stock_alert(self, medication):
        """Enviar alerta de stock bajo"""
        try:
            if not self.notification_service_url:
                print(f"⚠️ Stock bajo: {medication.name} ({medication.stock_quantity} unidades)")
                return

            url = f"{self.notification_service_url}/notifications/inventory-alert"
            data = {
                'alert_type': 'low_stock',
                'medication_details': {
                    'name': medication.name,
                    'stock_quantity': medication.stock_quantity,
                    'minimum_stock_alert': medication.minimum_stock_alert
                },
                'admin_emails': ['admin@veterinariaclinic.com', 'inventario@veterinariaclinic.com']
            }

            response = requests.post(url, json=data, timeout=5)
            return response.status_code == 200

        except Exception as e:
            print(f"Error enviando alerta de stock bajo: {e}")
            return False

    def _send_expiration_alert(self, medications):
        """Enviar alerta de medicamentos próximos a vencer"""
        try:
            if not self.notification_service_url:
                print(f"⚠️ Medicamentos próximos a vencer: {len(medications)}")
                return

            url = f"{self.notification_service_url}/notifications/inventory-alert"
            data = {
                'alert_type': 'expiration',
                'medication_details': [
                    {
                        'name': med.name,
                        'expiration_date': med.expiration_date.isoformat(),
                        'days_to_expiration': med.get_days_to_expiration(),
                        'stock_quantity': med.stock_quantity
                    }
                    for med in medications
                ],
                'admin_emails': ['admin@veterinariaclinic.com', 'inventario@veterinariaclinic.com']
            }

            response = requests.post(url, json=data, timeout=5)
            return response.status_code == 200

        except Exception as e:
            print(f"Error enviando alerta de vencimiento: {e}")
            return False

    # =============== REPORTS AND ANALYTICS ===============

    def get_inventory_summary(self):
        """Obtener resumen del inventario"""
        medications = self.get_all_medications()

        total_medications = len(medications)
        total_value = sum(float(med.unit_price or 0) * med.stock_quantity for med in medications)
        low_stock_count = len([med for med in medications if med.get_stock_status() == 'low_stock'])
        out_of_stock_count = len([med for med in medications if med.get_stock_status() == 'out_of_stock'])
        expiring_count = len([med for med in medications if med.is_near_expiration(30)])

        return {
            'total_medications': total_medications,
            'total_inventory_value': total_value,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'expiring_soon_count': expiring_count,
            'last_updated': datetime.now().isoformat()
        }

    def get_movement_report(self, start_date=None, end_date=None):
        """Generar reporte de movimientos"""
        movements = self.get_stock_movements(start_date=start_date, end_date=end_date)

        # Agrupar por tipo de movimiento
        movements_by_type = {}
        total_in = 0
        total_out = 0

        for movement in movements:
            movement_type = movement.movement_type
            if movement_type not in movements_by_type:
                movements_by_type[movement_type] = []

            movements_by_type[movement_type].append(movement.to_dict())

            if movement_type == 'in':
                total_in += movement.quantity
            elif movement_type == 'out':
                total_out += movement.quantity

        return {
            'movements_by_type': movements_by_type,
            'summary': {
                'total_movements': len(movements),
                'total_in': total_in,
                'total_out': total_out,
                'net_change': total_in - total_out
            },
            'period': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            }
        }

    def export_inventory_to_csv(self):
        """Exportar inventario a CSV (retorna datos para generar CSV)"""
        medications = self.get_all_medications()

        data = []
        for med in medications:
            data.append({
                'ID': med.id,
                'Nombre': med.name,
                'Categoría': med.category,
                'Laboratorio': med.laboratory,
                'Stock': med.stock_quantity,
                'Precio Unitario': float(med.unit_price or 0),
                'Valor Total': float(med.unit_price or 0) * med.stock_quantity,
                'Fecha Vencimiento': med.expiration_date.isoformat() if med.expiration_date else '',
                'Días para Vencimiento': med.get_days_to_expiration(),
                'Estado Stock': med.get_stock_status(),
                'Proveedor': med.supplier,
                'Lote': med.batch_number,
                'Alerta Stock Mínimo': med.minimum_stock_alert
            })

        return data