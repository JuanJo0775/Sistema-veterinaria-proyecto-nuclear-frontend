# microservices/medical_service/app/routes/medical_routes.py
from flask import Blueprint, request, jsonify
from datetime import datetime
from werkzeug.utils import secure_filename
from ..models.pet import Pet, db
from ..models.medical_record import MedicalRecord, Prescription, ExamResult
from ..services.medical_service import MedicalService

medical_bp = Blueprint('medical', __name__)
medical_service = MedicalService()


@medical_bp.route('/pets', methods=['POST'])
def create_pet():
    """Crear nueva mascota"""
    try:
        data = request.get_json()

        # Validaciones básicas
        required_fields = ['owner_id', 'name', 'species']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        pet = medical_service.create_pet(data)

        return jsonify({
            'success': True,
            'message': 'Mascota creada exitosamente',
            'pet': pet.to_dict()
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@medical_bp.route('/pets/<pet_id>', methods=['GET'])
def get_pet(pet_id):
    """Obtener información de una mascota"""
    try:
        pet = medical_service.get_pet_by_id(pet_id)

        if pet:
            pet_data = pet.to_dict()
            pet_data['age'] = pet.get_age()
            return jsonify({
                'success': True,
                'pet': pet_data
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Mascota no encontrada'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@medical_bp.route('/pets/<pet_id>', methods=['PUT'])
def update_pet(pet_id):
    """Actualizar información de mascota"""
    try:
        data = request.get_json()

        pet = medical_service.update_pet(pet_id, data)

        if pet:
            return jsonify({
                'success': True,
                'message': 'Mascota actualizada exitosamente',
                'pet': pet.to_dict()
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Mascota no encontrada'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@medical_bp.route('/pets/owner/<owner_id>', methods=['GET'])
def get_pets_by_owner(owner_id):
    """Obtener mascotas de un propietario"""
    try:
        pets = medical_service.get_pets_by_owner(owner_id)

        pets_data = []
        for pet in pets:
            pet_data = pet.to_dict()
            pet_data['age'] = pet.get_age()
            pets_data.append(pet_data)

        return jsonify({
            'success': True,
            'pets': pets_data,
            'total': len(pets_data)
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@medical_bp.route('/pets/search', methods=['GET'])
def search_pets():
    """Buscar mascotas"""
    try:
        search_term = request.args.get('q', '')

        if not search_term:
            return jsonify({
                'success': False,
                'message': 'Parámetro de búsqueda requerido'
            }), 400

        pets = medical_service.search_pets(search_term)

        pets_data = []
        for pet in pets:
            pet_data = pet.to_dict()
            pet_data['age'] = pet.get_age()
            pets_data.append(pet_data)

        return jsonify({
            'success': True,
            'pets': pets_data,
            'total': len(pets_data),
            'search_term': search_term
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@medical_bp.route('/pets/<pet_id>/photo', methods=['POST'])
def upload_pet_photo(pet_id):
    """Subir foto de mascota"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No se encontró archivo'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No se seleccionó archivo'
            }), 400

        photo_url = medical_service.upload_pet_photo(pet_id, file)

        if photo_url:
            return jsonify({
                'success': True,
                'message': 'Foto subida exitosamente',
                'photo_url': photo_url
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Error al subir la foto'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== MEDICAL RECORDS ROUTES ===============

@medical_bp.route('/records', methods=['POST'])
def create_medical_record():
    """Crear nueva historia clínica"""
    try:
        data = request.get_json()

        # Validaciones básicas
        required_fields = ['pet_id', 'veterinarian_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        medical_record = medical_service.create_medical_record(data)

        return jsonify({
            'success': True,
            'message': 'Historia clínica creada exitosamente',
            'medical_record': medical_record.to_dict()
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@medical_bp.route('/records/<record_id>', methods=['GET'])
def get_medical_record(record_id):
    """Obtener historia clínica por ID"""
    try:
        medical_record = medical_service.get_medical_record_by_id(record_id)

        if medical_record:
            record_data = medical_record.to_dict()
            # Incluir prescripciones y resultados de exámenes
            record_data['prescriptions'] = [p.to_dict() for p in medical_record.prescriptions]
            record_data['exam_results'] = [e.to_dict() for e in medical_record.exam_results]

            return jsonify({
                'success': True,
                'medical_record': record_data
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Historia clínica no encontrada'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@medical_bp.route('/records/<record_id>', methods=['PUT'])
def update_medical_record(record_id):
    """Actualizar historia clínica"""
    try:
        data = request.get_json()

        medical_record = medical_service.update_medical_record(record_id, data)

        if medical_record:
            return jsonify({
                'success': True,
                'message': 'Historia clínica actualizada exitosamente',
                'medical_record': medical_record.to_dict()
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Historia clínica no encontrada'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@medical_bp.route('/records/<record_id>/complete', methods=['PUT'])
def complete_medical_record(record_id):
    """Marcar historia clínica como completada"""
    try:
        medical_record = medical_service.complete_medical_record(record_id)

        if medical_record:
            return jsonify({
                'success': True,
                'message': 'Historia clínica completada exitosamente',
                'medical_record': medical_record.to_dict()
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Historia clínica no encontrada'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@medical_bp.route('/records/pet/<pet_id>', methods=['GET'])
def get_medical_records_by_pet(pet_id):
    """Obtener historias clínicas de una mascota"""
    try:
        medical_records = medical_service.get_medical_records_by_pet(pet_id)

        records_data = []
        for record in medical_records:
            record_data = record.to_dict()
            record_data['prescriptions'] = [p.to_dict() for p in record.prescriptions]
            record_data['exam_results'] = [e.to_dict() for e in record.exam_results]
            records_data.append(record_data)

        return jsonify({
            'success': True,
            'medical_records': records_data,
            'total': len(records_data),
            'pet_id': pet_id
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== PRESCRIPTIONS ROUTES ===============

@medical_bp.route('/prescriptions', methods=['POST'])
def add_prescription():
    """Agregar prescripción a historia clínica"""
    try:
        data = request.get_json()

        # Validaciones básicas
        required_fields = ['medical_record_id', 'medication_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        prescription = medical_service.add_prescription(data)

        return jsonify({
            'success': True,
            'message': 'Prescripción agregada exitosamente',
            'prescription': prescription.to_dict()
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== EXAM RESULTS ROUTES ===============

@medical_bp.route('/exam-results', methods=['POST'])
def add_exam_result():
    """Agregar resultado de examen"""
    try:
        # Obtener datos del formulario
        exam_data = {
            'medical_record_id': request.form.get('medical_record_id'),
            'exam_id': request.form.get('exam_id'),
            'exam_name': request.form.get('exam_name'),
            'observations': request.form.get('observations'),
            'date_performed': request.form.get('date_performed'),
            'performed_by': request.form.get('performed_by')
        }

        # Validaciones básicas
        required_fields = ['medical_record_id', 'exam_name']
        for field in required_fields:
            if not exam_data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        # Obtener archivo si existe
        file = request.files.get('file')

        exam_result = medical_service.add_exam_result(exam_data, file)

        return jsonify({
            'success': True,
            'message': 'Resultado de examen agregado exitosamente',
            'exam_result': exam_result.to_dict()
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== SUMMARY ROUTES ===============

@medical_bp.route('/summary/pet/<pet_id>', methods=['GET'])
def get_medical_summary(pet_id):
    """Obtener resumen médico de una mascota"""
    try:
        summary = medical_service.get_medical_summary(pet_id)

        if summary:
            return jsonify({
                'success': True,
                'summary': summary
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Mascota no encontrada'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@medical_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'medical_service'
    }), 200