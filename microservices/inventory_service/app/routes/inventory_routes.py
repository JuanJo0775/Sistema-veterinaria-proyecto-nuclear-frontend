# microservices/inventory_service/app/routes/inventory_routes.py
from flask import Blueprint, request, jsonify, make_response
from datetime import datetime, timedelta
import csv
import io
from ..models.medication import Medication, StockMovement, db
from ..services.inventory_service import InventoryService

inventory_bp = Blueprint('inventory', __name__)
inventory_service = InventoryService()



@inventory_bp.route('/medications', methods=['POST'])
def create_medication():
    """Crear nuevo medicamento"""
    try:
        data = request.get_json()

        # Validaciones básicas
        required_fields = ['name', 'unit_price']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        medication = inventory_service.create_medication(data)

        return jsonify({
            'success': True,
            'message': 'Medicamento creado exitosamente',
            'medication': medication.to_dict()
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/medications', methods=['GET'])
def get_medications():
    """Obtener todos los medicamentos"""
    try:
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        category = request.args.get('category')

        medications = inventory_service.get_all_medications(include_inactive)

        # Filtrar por categoría si se especifica
        if category:
            medications = [med for med in medications if med.category == category]

        medications_data = [med.to_dict() for med in medications]

        return jsonify({
            'success': True,
            'medications': medications_data,
            'total': len(medications_data)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/medications/<medication_id>', methods=['GET'])
def get_medication(medication_id):
    """Obtener medicamento por ID"""
    try:
        medication = inventory_service.get_medication_by_id(medication_id)

        if medication:
            medication_data = medication.to_dict()
            # Incluir movimientos recientes
            recent_movements = inventory_service.get_stock_movements(medication_id, limit=10)
            medication_data['recent_movements'] = [movement.to_dict() for movement in recent_movements]

            return jsonify({
                'success': True,
                'medication': medication_data
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Medicamento no encontrado'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/medications/<medication_id>', methods=['PUT'])
def update_medication(medication_id):
    """Actualizar medicamento"""
    try:
        data = request.get_json()

        medication = inventory_service.update_medication(medication_id, data)

        if medication:
            return jsonify({
                'success': True,
                'message': 'Medicamento actualizado exitosamente',
                'medication': medication.to_dict()
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Medicamento no encontrado'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/medications/<medication_id>/deactivate', methods=['PUT'])
def deactivate_medication(medication_id):
    """Desactivar medicamento"""
    try:
        medication = inventory_service.deactivate_medication(medication_id)

        if medication:
            return jsonify({
                'success': True,
                'message': 'Medicamento desactivado exitosamente'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Medicamento no encontrado'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/medications/search', methods=['GET'])
def search_medications():
    """Buscar medicamentos"""
    try:
        search_term = request.args.get('q', '')

        if not search_term:
            return jsonify({
                'success': False,
                'message': 'Parámetro de búsqueda requerido'
            }), 400

        medications = inventory_service.search_medications(search_term)
        medications_data = [med.to_dict() for med in medications]

        return jsonify({
            'success': True,
            'medications': medications_data,
            'total': len(medications_data),
            'search_term': search_term
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== STOCK ROUTES ===============

@inventory_bp.route('/update-stock', methods=['PUT'])
def update_stock():
    """Actualizar stock de medicamento"""
    try:
        data = request.get_json()

        required_fields = ['medication_id', 'quantity_change', 'reason']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        result = inventory_service.update_stock(
            data.get('medication_id'),
            data.get('quantity_change'),
            data.get('reason'),
            data.get('reference_id'),
            data.get('user_id')
        )

        return jsonify({
            'success': True,
            'message': 'Stock actualizado exitosamente',
            'result': {
                'medication': result['medication'].to_dict(),
                'previous_stock': result['previous_stock'],
                'new_stock': result['new_stock'],
                'movement': result['movement'].to_dict()
            }
        }), 200

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/add-stock', methods=['POST'])
def add_stock():
    """Agregar stock (compra, donación, etc.)"""
    try:
        data = request.get_json()

        required_fields = ['medication_id', 'quantity', 'reason']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        result = inventory_service.add_stock(
            data.get('medication_id'),
            data.get('quantity'),
            data.get('reason'),
            data.get('unit_cost'),
            data.get('user_id')
        )

        return jsonify({
            'success': True,
            'message': 'Stock agregado exitosamente',
            'result': {
                'medication': result['medication'].to_dict(),
                'previous_stock': result['previous_stock'],
                'new_stock': result['new_stock'],
                'movement': result['movement'].to_dict()
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/reduce-stock', methods=['POST'])
def reduce_stock():
    """Reducir stock (prescripción, vencimiento, etc.)"""
    try:
        data = request.get_json()

        required_fields = ['medication_id', 'quantity', 'reason']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        result = inventory_service.reduce_stock(
            data.get('medication_id'),
            data.get('quantity'),
            data.get('reason'),
            data.get('reference_id'),
            data.get('user_id')
        )

        return jsonify({
            'success': True,
            'message': 'Stock reducido exitosamente',
            'result': {
                'medication': result['medication'].to_dict(),
                'previous_stock': result['previous_stock'],
                'new_stock': result['new_stock'],
                'movement': result['movement'].to_dict()
            }
        }), 200

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/movements', methods=['GET'])
def get_stock_movements():
    """Obtener movimientos de stock"""
    try:
        medication_id = request.args.get('medication_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit')

        # Convertir fechas si se proporcionan
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
        limit_int = int(limit) if limit else None

        movements = inventory_service.get_stock_movements(
            medication_id, start_date_obj, end_date_obj, limit_int
        )

        movements_data = [movement.to_dict() for movement in movements]

        return jsonify({
            'success': True,
            'movements': movements_data,
            'total': len(movements_data)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== ALERTS ROUTES ===============

@inventory_bp.route('/alerts/low-stock', methods=['GET'])
def get_low_stock_alerts():
    """Obtener medicamentos con stock bajo"""
    try:
        medications = inventory_service.get_low_stock_medications()
        medications_data = [med.to_dict() for med in medications]

        return jsonify({
            'success': True,
            'low_stock_medications': medications_data,
            'total': len(medications_data)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/alerts/expiring', methods=['GET'])
def get_expiring_medications():
    """Obtener medicamentos próximos a vencer"""
    try:
        days_threshold = int(request.args.get('days', 30))

        medications = inventory_service.get_expiring_medications(days_threshold)
        medications_data = [med.to_dict() for med in medications]

        return jsonify({
            'success': True,
            'expiring_medications': medications_data,
            'total': len(medications_data),
            'days_threshold': days_threshold
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/alerts/check-expiration', methods=['POST'])
def check_expiration_alerts():
    """Verificar y enviar alertas de vencimiento"""
    try:
        data = request.get_json() or {}
        days_threshold = data.get('days_threshold', 30)

        medications = inventory_service.check_expiration_alerts(days_threshold)

        return jsonify({
            'success': True,
            'message': f'Verificación completada. {len(medications)} medicamentos próximos a vencer',
            'expiring_medications': [med.to_dict() for med in medications]
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== REPORTS ROUTES ===============

@inventory_bp.route('/summary', methods=['GET'])
def get_inventory_summary():
    """Obtener resumen del inventario"""
    try:
        summary = inventory_service.get_inventory_summary()

        return jsonify({
            'success': True,
            'summary': summary
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/reports/movements', methods=['GET'])
def get_movement_report():
    """Generar reporte de movimientos"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Convertir fechas si se proporcionan
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None

        report = inventory_service.get_movement_report(start_date_obj, end_date_obj)

        return jsonify({
            'success': True,
            'report': report
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/export/csv', methods=['GET'])
def export_inventory_csv():
    """Exportar inventario a CSV"""
    try:
        data = inventory_service.export_inventory_to_csv()

        # Crear CSV en memoria
        output = io.StringIO()
        if data:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        # Crear respuesta
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers[
            'Content-Disposition'] = f'attachment; filename=inventario_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        return response

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== CATEGORIES AND STATS ===============

@inventory_bp.route('/categories', methods=['GET'])
def get_categories():
    """Obtener categorías de medicamentos"""
    try:
        categories = db.session.query(Medication.category).filter(
            Medication.category.isnot(None),
            Medication.is_active == True
        ).distinct().all()

        categories_list = [cat[0] for cat in categories if cat[0]]

        return jsonify({
            'success': True,
            'categories': sorted(categories_list)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/stats', methods=['GET'])
def get_inventory_stats():
    """Obtener estadísticas del inventario"""
    try:
        # Estadísticas básicas
        total_medications = Medication.query.filter_by(is_active=True).count()
        low_stock = len(inventory_service.get_low_stock_medications())
        expiring_soon = len(inventory_service.get_expiring_medications(30))

        # Estadísticas por categoría
        category_stats = db.session.query(
            Medication.category,
            db.func.count(Medication.id).label('count'),
            db.func.sum(Medication.stock_quantity).label('total_stock')
        ).filter(
            Medication.is_active == True,
            Medication.category.isnot(None)
        ).group_by(Medication.category).all()

        return jsonify({
            'success': True,
            'stats': {
                'total_medications': total_medications,
                'low_stock_count': low_stock,
                'expiring_soon_count': expiring_soon,
                'category_stats': [
                    {
                        'category': stat[0],
                        'medication_count': stat[1],
                        'total_stock': stat[2] or 0
                    }
                    for stat in category_stats
                ]
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'inventory_service'
    }), 200