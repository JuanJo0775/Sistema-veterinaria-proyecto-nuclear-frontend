# microservices/medical_service/app/routes/medical_routes.py
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from werkzeug.utils import secure_filename
from ..models.pet import Pet, db
from ..models.medical_record import MedicalRecord, Prescription, ExamResult
from ..services.medical_service import MedicalService
import uuid
from sqlalchemy.exc import IntegrityError

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
    """Crear nueva historia clínica - VERSIÓN CORREGIDA"""
    try:
        data = request.get_json()

        print(f"📡 Datos recibidos para crear historia clínica: {data}")

        # Validaciones básicas
        required_fields = ['pet_id', 'veterinarian_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido: {field}'
                }), 400

        # Validar UUIDs
        try:
            if isinstance(data.get('pet_id'), str):
                uuid.UUID(data.get('pet_id'))
            if isinstance(data.get('veterinarian_id'), str):
                uuid.UUID(data.get('veterinarian_id'))
        except ValueError as e:
            return jsonify({
                'success': False,
                'message': f'ID inválido: {str(e)}'
            }), 400

        # Crear record con manejo de errores mejorado
        try:
            medical_record = MedicalRecord(
                pet_id=data.get('pet_id'),
                veterinarian_id=data.get('veterinarian_id'),
                appointment_id=data.get('appointment_id'),
                symptoms_description=data.get('symptoms_description', ''),
                physical_examination=data.get('physical_examination', ''),
                diagnosis=data.get('diagnosis', ''),
                treatment=data.get('treatment', ''),
                medications_prescribed=data.get('medications_prescribed', ''),
                exams_requested=data.get('exams_requested', ''),
                observations=data.get('observations', ''),
                next_appointment_recommendation=data.get('next_appointment_recommendation', ''),
                weight_at_visit=float(data.get('weight_at_visit')) if data.get('weight_at_visit') else None,
                temperature=float(data.get('temperature')) if data.get('temperature') else None,
                pulse=int(data.get('pulse')) if data.get('pulse') else None,
                respiratory_rate=int(data.get('respiratory_rate')) if data.get('respiratory_rate') else None,
                is_emergency=bool(data.get('is_emergency', False)),
                status=data.get('status', 'draft')
            )

            db.session.add(medical_record)
            db.session.commit()

            print(f"✅ Historia clínica creada exitosamente: {medical_record.id}")

            return jsonify({
                'success': True,
                'message': 'Historia clínica creada exitosamente',
                'medical_record': medical_record.to_dict()
            }), 201

        except IntegrityError as e:
            db.session.rollback()
            print(f"❌ Error de integridad: {e}")
            return jsonify({
                'success': False,
                'message': 'Error de integridad en los datos'
            }), 400

        except ValueError as e:
            db.session.rollback()
            print(f"❌ Error de valor: {e}")
            return jsonify({
                'success': False,
                'message': f'Valor inválido: {str(e)}'
            }), 400

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creando historia clínica: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


@medical_bp.route('/records/<record_id>', methods=['GET'])
def get_medical_record(record_id):
    """Obtener historia clínica por ID"""
    try:
        medical_record = medical_service.get_medical_record_by_id(record_id)

        if medical_record:
            record_data = medical_record.to_dict()
            # TEMPORAL: No incluir prescriptions y exam_results hasta arreglar relaciones
            # record_data['prescriptions'] = [p.to_dict() for p in medical_record.prescriptions]
            # record_data['exam_results'] = [e.to_dict() for e in medical_record.exam_results]

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
def update_medical_record():
    """Actualizar historia clínica - VERSIÓN CORREGIDA"""
    try:
        record_id = str(record_id)
        data = request.get_json()

        print(f"📡 Actualizando historia clínica {record_id} con datos: {data}")

        # Validar UUID del record_id
        try:
            uuid.UUID(record_id)
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'ID de historia clínica inválido'
            }), 400

        # Buscar la historia clínica
        medical_record = MedicalRecord.query.get(record_id)
        if not medical_record:
            return jsonify({
                'success': False,
                'message': 'Historia clínica no encontrada'
            }), 404

        # Actualizar campos permitidos con validación
        try:
            if 'symptoms_description' in data:
                medical_record.symptoms_description = str(data['symptoms_description']) if data[
                    'symptoms_description'] else ''

            if 'physical_examination' in data:
                medical_record.physical_examination = str(data['physical_examination']) if data[
                    'physical_examination'] else ''

            if 'diagnosis' in data:
                medical_record.diagnosis = str(data['diagnosis']) if data['diagnosis'] else ''

            if 'treatment' in data:
                medical_record.treatment = str(data['treatment']) if data['treatment'] else ''

            if 'medications_prescribed' in data:
                medical_record.medications_prescribed = str(data['medications_prescribed']) if data[
                    'medications_prescribed'] else ''

            if 'exams_requested' in data:
                medical_record.exams_requested = str(data['exams_requested']) if data['exams_requested'] else ''

            if 'observations' in data:
                medical_record.observations = str(data['observations']) if data['observations'] else ''

            if 'next_appointment_recommendation' in data:
                medical_record.next_appointment_recommendation = str(data['next_appointment_recommendation']) if data[
                    'next_appointment_recommendation'] else ''

            if 'weight_at_visit' in data and data['weight_at_visit'] is not None:
                medical_record.weight_at_visit = float(data['weight_at_visit'])

            if 'temperature' in data and data['temperature'] is not None:
                medical_record.temperature = float(data['temperature'])

            if 'pulse' in data and data['pulse'] is not None:
                medical_record.pulse = int(data['pulse'])

            if 'respiratory_rate' in data and data['respiratory_rate'] is not None:
                medical_record.respiratory_rate = int(data['respiratory_rate'])

            if 'is_emergency' in data:
                medical_record.is_emergency = bool(data['is_emergency'])

            if 'status' in data and data['status']:
                medical_record.status = str(data['status'])

            # Actualizar timestamp
            medical_record.updated_at = datetime.utcnow()

            db.session.commit()

            print(f"✅ Historia clínica {record_id} actualizada exitosamente")

            return jsonify({
                'success': True,
                'message': 'Historia clínica actualizada exitosamente',
                'medical_record': medical_record.to_dict()
            }), 200

        except ValueError as e:
            db.session.rollback()
            print(f"❌ Error de valor en actualización: {e}")
            return jsonify({
                'success': False,
                'message': f'Valor inválido: {str(e)}'
            }), 400

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error actualizando historia clínica: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


@medical_bp.route('/records/<record_id>/complete', methods=['PUT'])
def complete_medical_record(record_id):
    """Marcar historia clínica como completada - VERSIÓN CORREGIDA"""
    try:
        record_id = str(record_id)

        print(f"📡 Completando historia clínica: {record_id}")

        # Validar UUID
        try:
            uuid.UUID(record_id)
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'ID de historia clínica inválido'
            }), 400

        # Buscar la historia clínica
        medical_record = MedicalRecord.query.get(record_id)
        if not medical_record:
            return jsonify({
                'success': False,
                'message': 'Historia clínica no encontrada'
            }), 404

        # Marcar como completada
        medical_record.status = 'completed'
        medical_record.updated_at = datetime.utcnow()

        db.session.commit()

        print(f"✅ Historia clínica {record_id} marcada como completada")

        # Marcar cita como completada si existe appointment_id
        if medical_record.appointment_id:
            try:
                complete_appointment_result = medical_service._complete_appointment(medical_record.appointment_id)
                print(f"📅 Resultado completar cita: {complete_appointment_result}")
            except Exception as e:
                print(f"⚠️ Error completando cita: {e}")

        return jsonify({
            'success': True,
            'message': 'Historia clínica completada exitosamente',
            'medical_record': medical_record.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error completando historia clínica: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error interno: {str(e)}'
        }), 500


@medical_bp.route('/records/pet/<pet_id>', methods=['GET'])
def get_medical_records_by_pet(pet_id):
    """Obtener historias clínicas de una mascota"""
    try:
        medical_records = medical_service.get_medical_records_by_pet(pet_id)

        records_data = []
        for record in medical_records:
            record_data = record.to_dict()
            # TEMPORAL: No incluir prescriptions y exam_results hasta arreglar relaciones
            # record_data['prescriptions'] = [p.to_dict() for p in record.prescriptions]
            # record_data['exam_results'] = [e.to_dict() for e in record.exam_results]
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


@medical_bp.route('/pets', methods=['GET'])
def get_all_pets():
    """Obtener todas las mascotas (para admin)"""
    try:
        # Aquí podrías agregar verificación de permisos de admin
        pets = Pet.query.filter_by(is_active=True).order_by(Pet.name).all()

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


@medical_bp.route('/pets/<pet_id>', methods=['DELETE'])
def delete_pet(pet_id):
    """Eliminar mascota (marcar como inactiva)"""
    try:
        pet = medical_service.get_pet_by_id(pet_id)

        if pet:
            # En lugar de eliminar físicamente, marcar como inactiva
            pet.is_active = False
            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'Mascota {pet.name} eliminada exitosamente'
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


@medical_bp.route('/pets/<pet_id>/upload-photo', methods=['POST'])
def upload_pet_photo_alt(pet_id):
    """Ruta alternativa para subir foto de mascota"""
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


# =============== RUTAS DE ESTADÍSTICAS ===============

@medical_bp.route('/pets/stats', methods=['GET'])
def get_pets_statistics():
    """Obtener estadísticas de mascotas"""
    try:
        # Estadísticas básicas
        total_pets = Pet.query.filter_by(is_active=True).count()

        # Por especie
        dogs_count = Pet.query.filter_by(species='perro', is_active=True).count()
        cats_count = Pet.query.filter_by(species='gato', is_active=True).count()
        others_count = total_pets - dogs_count - cats_count

        # Por estado de vacunación
        complete_vaccination = Pet.query.filter_by(vaccination_status='completo', is_active=True).count()
        partial_vaccination = Pet.query.filter_by(vaccination_status='parcial', is_active=True).count()
        pending_vaccination = Pet.query.filter_by(vaccination_status='pendiente', is_active=True).count()
        unknown_vaccination = Pet.query.filter_by(vaccination_status='desconocido', is_active=True).count()

        return jsonify({
            'success': True,
            'stats': {
                'total_pets': total_pets,
                'by_species': {
                    'dogs': dogs_count,
                    'cats': cats_count,
                    'others': others_count
                },
                'by_vaccination': {
                    'complete': complete_vaccination,
                    'partial': partial_vaccination,
                    'pending': pending_vaccination,
                    'unknown': unknown_vaccination
                }
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== BÚSQUEDA Y FILTROS ===============

@medical_bp.route('/pets/by-species/<species>', methods=['GET'])
def get_pets_by_species(species):
    """Obtener mascotas por especie"""
    try:
        pets = Pet.query.filter_by(species=species, is_active=True).order_by(Pet.name).all()

        pets_data = []
        for pet in pets:
            pet_data = pet.to_dict()
            pet_data['age'] = pet.get_age()
            pets_data.append(pet_data)

        return jsonify({
            'success': True,
            'pets': pets_data,
            'total': len(pets_data),
            'species': species
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@medical_bp.route('/pets/by-vaccination/<status>', methods=['GET'])
def get_pets_by_vaccination_status(status):
    """Obtener mascotas por estado de vacunación"""
    try:
        pets = Pet.query.filter_by(vaccination_status=status, is_active=True).order_by(Pet.name).all()

        pets_data = []
        for pet in pets:
            pet_data = pet.to_dict()
            pet_data['age'] = pet.get_age()
            pets_data.append(pet_data)

        return jsonify({
            'success': True,
            'pets': pets_data,
            'total': len(pets_data),
            'vaccination_status': status
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============== DASHBOARD DATA ===============

@medical_bp.route('/dashboard/summary', methods=['GET'])
def get_medical_dashboard_summary():
    """Obtener resumen para el dashboard"""
    try:
        # Contar mascotas totales
        total_pets = Pet.query.filter_by(is_active=True).count()

        # Contar historias clínicas del mes actual
        from datetime import datetime, timedelta
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        records_this_month = MedicalRecord.query.filter(
            MedicalRecord.created_at >= current_month_start
        ).count()

        # Mascotas registradas este mes
        pets_this_month = Pet.query.filter(
            Pet.created_at >= current_month_start,
            Pet.is_active == True
        ).count()

        # Próximas citas (requiere integración con appointment service)
        # Por ahora retornamos 0
        upcoming_appointments = 0

        return jsonify({
            'success': True,
            'summary': {
                'total_pets': total_pets,
                'records_this_month': records_this_month,
                'pets_this_month': pets_this_month,
                'upcoming_appointments': upcoming_appointments
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

    @medical_bp.route('/records/<record_id>', methods=['DELETE'])
    def delete_medical_record(record_id):
        """Eliminar historia clínica definitivamente"""
        try:
            medical_record = medical_service.get_medical_record_by_id(record_id)

            if medical_record:
                # Eliminar físicamente de la base de datos
                db.session.delete(medical_record)
                db.session.commit()

                return jsonify({
                    'success': True,
                    'message': f'Historia clínica eliminada definitivamente'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': 'Historia clínica no encontrada'
                }), 404

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @medical_bp.route('/records', methods=['GET'])
    def get_all_medical_records():
        """Obtener todas las historias clínicas (para admin)"""
        try:
            # Obtener parámetros de consulta
            limit = request.args.get('limit', type=int)
            offset = request.args.get('offset', type=int, default=0)
            status = request.args.get('status')
            veterinarian_id = request.args.get('veterinarian_id')
            pet_id = request.args.get('pet_id')
            is_emergency = request.args.get('is_emergency')

            # Construir query
            query = MedicalRecord.query

            # Aplicar filtros
            if status:
                query = query.filter_by(status=status)
            if veterinarian_id:
                query = query.filter_by(veterinarian_id=veterinarian_id)
            if pet_id:
                query = query.filter_by(pet_id=pet_id)
            if is_emergency is not None:
                query = query.filter_by(is_emergency=is_emergency.lower() == 'true')

            # Ordenar por más recientes
            query = query.order_by(MedicalRecord.created_at.desc())

            # Aplicar paginación si se especifica
            if limit:
                query = query.offset(offset).limit(limit)

            medical_records = query.all()

            return jsonify({
                'success': True,
                'medical_records': [record.to_dict() for record in medical_records],
                'total': len(medical_records)
            }), 200

        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @medical_bp.route('/records/search', methods=['GET'])
    def search_medical_records():
        """Buscar historias clínicas"""
        try:
            search_term = request.args.get('q', '')

            if not search_term:
                return jsonify({
                    'success': False,
                    'message': 'Parámetro de búsqueda requerido'
                }), 400

            # Buscar en múltiples campos
            medical_records = MedicalRecord.query.filter(
                db.or_(
                    MedicalRecord.symptoms_description.ilike(f'%{search_term}%'),
                    MedicalRecord.diagnosis.ilike(f'%{search_term}%'),
                    MedicalRecord.treatment.ilike(f'%{search_term}%'),
                    MedicalRecord.observations.ilike(f'%{search_term}%')
                )
            ).order_by(MedicalRecord.created_at.desc()).all()

            return jsonify({
                'success': True,
                'medical_records': [record.to_dict() for record in medical_records],
                'total': len(medical_records),
                'search_term': search_term
            }), 200

        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @medical_bp.route('/records/statistics', methods=['GET'])
    def get_medical_records_statistics():
        """Obtener estadísticas de historias clínicas"""
        try:
            from datetime import datetime, timedelta

            # Estadísticas básicas
            total_records = MedicalRecord.query.count()

            # Registros de hoy
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            records_today = MedicalRecord.query.filter(
                MedicalRecord.created_at >= today_start
            ).count()

            # Registros de emergencia
            emergency_records = MedicalRecord.query.filter_by(is_emergency=True).count()

            # Por estado
            completed_records = MedicalRecord.query.filter_by(status='completed').count()
            draft_records = MedicalRecord.query.filter_by(status='draft').count()
            reviewed_records = MedicalRecord.query.filter_by(status='reviewed').count()

            # Registros de la última semana
            week_ago = datetime.now() - timedelta(days=7)
            records_this_week = MedicalRecord.query.filter(
                MedicalRecord.created_at >= week_ago
            ).count()

            # Registros del último mes
            month_ago = datetime.now() - timedelta(days=30)
            records_this_month = MedicalRecord.query.filter(
                MedicalRecord.created_at >= month_ago
            ).count()

            return jsonify({
                'success': True,
                'statistics': {
                    'total_records': total_records,
                    'records_today': records_today,
                    'records_this_week': records_this_week,
                    'records_this_month': records_this_month,
                    'emergency_records': emergency_records,
                    'by_status': {
                        'completed': completed_records,
                        'draft': draft_records,
                        'reviewed': reviewed_records
                    }
                }
            }), 200

        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @medical_bp.route('/records/by-veterinarian/<vet_id>', methods=['GET'])
    def get_records_by_veterinarian(vet_id):
        """Obtener historias clínicas por veterinario"""
        try:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            status = request.args.get('status')

            # Construir query base
            query = MedicalRecord.query.filter_by(veterinarian_id=vet_id)

            # Aplicar filtros opcionales
            if start_date:
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                    query = query.filter(MedicalRecord.created_at >= start_date_obj)
                except ValueError:
                    return jsonify({
                        'success': False,
                        'message': 'Formato de fecha inválido para start_date. Use YYYY-MM-DD'
                    }), 400

            if end_date:
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                    # Agregar 23:59:59 para incluir todo el día
                    end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
                    query = query.filter(MedicalRecord.created_at <= end_date_obj)
                except ValueError:
                    return jsonify({
                        'success': False,
                        'message': 'Formato de fecha inválido para end_date. Use YYYY-MM-DD'
                    }), 400

            if status:
                query = query.filter_by(status=status)

            # Ordenar por fecha más reciente
            medical_records = query.order_by(MedicalRecord.created_at.desc()).all()

            return jsonify({
                'success': True,
                'medical_records': [record.to_dict() for record in medical_records],
                'total': len(medical_records),
                'veterinarian_id': vet_id,
                'filters': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'status': status
                }
            }), 200

        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @medical_bp.route('/records/by-status/<status>', methods=['GET'])
    def get_records_by_status(status):
        """Obtener historias clínicas por estado"""
        try:
            # Validar estado
            valid_statuses = ['draft', 'completed', 'reviewed']
            if status not in valid_statuses:
                return jsonify({
                    'success': False,
                    'message': f'Estado inválido. Estados válidos: {", ".join(valid_statuses)}'
                }), 400

            medical_records = MedicalRecord.query.filter_by(status=status).order_by(
                MedicalRecord.created_at.desc()
            ).all()

            return jsonify({
                'success': True,
                'medical_records': [record.to_dict() for record in medical_records],
                'total': len(medical_records),
                'status': status
            }), 200

        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @medical_bp.route('/records/emergency', methods=['GET'])
    def get_emergency_records():
        """Obtener historias clínicas de emergencia"""
        try:
            emergency_records = MedicalRecord.query.filter_by(
                is_emergency=True
            ).order_by(MedicalRecord.created_at.desc()).all()

            return jsonify({
                'success': True,
                'medical_records': [record.to_dict() for record in emergency_records],
                'total': len(emergency_records)
            }), 200

        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    # =============== RUTAS ADICIONALES PARA PRESCRIPCIONES ===============

    @medical_bp.route('/prescriptions/by-record/<record_id>', methods=['GET'])
    def get_prescriptions_by_record(record_id):
        """Obtener prescripciones de una historia clínica específica"""
        try:
            prescriptions = Prescription.query.filter_by(medical_record_id=record_id).all()

            return jsonify({
                'success': True,
                'prescriptions': [prescription.to_dict() for prescription in prescriptions],
                'total': len(prescriptions),
                'medical_record_id': record_id
            }), 200

        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @medical_bp.route('/prescriptions/<prescription_id>', methods=['PUT'])
    def update_prescription(prescription_id):
        """Actualizar prescripción específica"""
        try:
            data = request.get_json()

            prescription = Prescription.query.get(prescription_id)
            if not prescription:
                return jsonify({
                    'success': False,
                    'message': 'Prescripción no encontrada'
                }), 404

            # Actualizar campos permitidos
            updatable_fields = ['medication_name', 'dosage', 'frequency', 'duration', 'quantity_prescribed',
                                'instructions']

            for field in updatable_fields:
                if field in data:
                    setattr(prescription, field, data[field])

            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Prescripción actualizada exitosamente',
                'prescription': prescription.to_dict()
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @medical_bp.route('/prescriptions/<prescription_id>', methods=['DELETE'])
    def delete_prescription(prescription_id):
        """Eliminar prescripción"""
        try:
            prescription = Prescription.query.get(prescription_id)
            if not prescription:
                return jsonify({
                    'success': False,
                    'message': 'Prescripción no encontrada'
                }), 404

            db.session.delete(prescription)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Prescripción eliminada exitosamente'
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    # =============== RUTAS ADICIONALES PARA RESULTADOS DE EXÁMENES ===============

    @medical_bp.route('/exam-results/by-record/<record_id>', methods=['GET'])
    def get_exam_results_by_record(record_id):
        """Obtener resultados de exámenes de una historia clínica específica"""
        try:
            exam_results = ExamResult.query.filter_by(medical_record_id=record_id).all()

            return jsonify({
                'success': True,
                'exam_results': [result.to_dict() for result in exam_results],
                'total': len(exam_results),
                'medical_record_id': record_id
            }), 200

        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @medical_bp.route('/exam-results/<result_id>', methods=['PUT'])
    def update_exam_result(result_id):
        """Actualizar resultado de examen específico"""
        try:
            # Obtener datos del formulario (puede incluir archivo)
            exam_data = {
                'exam_name': request.form.get('exam_name'),
                'observations': request.form.get('observations'),
                'date_performed': request.form.get('date_performed'),
                'performed_by': request.form.get('performed_by')
            }

            exam_result = ExamResult.query.get(result_id)
            if not exam_result:
                return jsonify({
                    'success': False,
                    'message': 'Resultado de examen no encontrado'
                }), 404

            # Actualizar campos
            for key, value in exam_data.items():
                if value is not None:
                    if key == 'date_performed' and value:
                        try:
                            exam_result.date_performed = datetime.strptime(value, '%Y-%m-%d').date()
                        except ValueError:
                            return jsonify({
                                'success': False,
                                'message': 'Formato de fecha inválido. Use YYYY-MM-DD'
                            }), 400
                    else:
                        setattr(exam_result, key, value)

            # Manejar archivo actualizado si existe
            file = request.files.get('file')
            if file and medical_service.allowed_file(file.filename):
                file_url = medical_service._save_exam_file(exam_result.medical_record_id, file)
                exam_result.result_file_url = file_url

            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Resultado de examen actualizado exitosamente',
                'exam_result': exam_result.to_dict()
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @medical_bp.route('/exam-results/<result_id>', methods=['DELETE'])
    def delete_exam_result(result_id):
        """Eliminar resultado de examen"""
        try:
            exam_result = ExamResult.query.get(result_id)
            if not exam_result:
                return jsonify({
                    'success': False,
                    'message': 'Resultado de examen no encontrado'
                }), 404

            # Eliminar archivo asociado si existe
            if exam_result.result_file_url:
                try:
                    import os
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'],
                                             exam_result.result_file_url.lstrip('/uploads/'))
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"⚠️ Error eliminando archivo: {e}")

            db.session.delete(exam_result)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Resultado de examen eliminado exitosamente'
            }), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    # =============== RUTAS DE REPORTES AVANZADOS ===============

    @medical_bp.route('/reports/veterinarian/<vet_id>', methods=['GET'])
    def get_veterinarian_report(vet_id):
        """Generar reporte detallado de un veterinario"""
        try:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')

            # Construir query
            query = MedicalRecord.query.filter_by(veterinarian_id=vet_id)

            if start_date:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(MedicalRecord.created_at >= start_date_obj)

            if end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(MedicalRecord.created_at <= end_date_obj)

            records = query.order_by(MedicalRecord.created_at.desc()).all()

            # Calcular estadísticas
            total_consultations = len(records)
            emergency_consultations = len([r for r in records if r.is_emergency])
            completed_consultations = len([r for r in records if r.status == 'completed'])

            # Agrupar por especie
            species_count = {}
            for record in records:
                # Necesitaríamos obtener la especie desde la tabla de mascotas
                # Por ahora simulamos
                species = 'unknown'  # Se podría mejorar con JOIN
                species_count[species] = species_count.get(species, 0) + 1

            return jsonify({
                'success': True,
                'report': {
                    'veterinarian_id': vet_id,
                    'period': {
                        'start_date': start_date,
                        'end_date': end_date
                    },
                    'statistics': {
                        'total_consultations': total_consultations,
                        'emergency_consultations': emergency_consultations,
                        'completed_consultations': completed_consultations,
                        'completion_rate': (
                                    completed_consultations / total_consultations * 100) if total_consultations > 0 else 0,
                        'emergency_rate': (
                                    emergency_consultations / total_consultations * 100) if total_consultations > 0 else 0
                    },
                    'consultations_by_species': species_count,
                    'recent_records': [record.to_dict() for record in records[:10]]
                }
            }), 200

        except ValueError as e:
            return jsonify({
                'success': False,
                'message': 'Formato de fecha inválido. Use YYYY-MM-DD'
            }), 400
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @medical_bp.route('/reports/monthly', methods=['GET'])
    def get_monthly_report():
        """Generar reporte mensual de actividad"""
        try:
            year = request.args.get('year', datetime.now().year, type=int)
            month = request.args.get('month', datetime.now().month, type=int)

            # Calcular fechas del mes
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)

            # Obtener registros del mes
            records = MedicalRecord.query.filter(
                MedicalRecord.created_at >= start_date,
                MedicalRecord.created_at <= end_date
            ).all()

            # Calcular estadísticas diarias
            daily_stats = {}
            for record in records:
                day = record.created_at.day
                if day not in daily_stats:
                    daily_stats[day] = {
                        'total': 0,
                        'emergency': 0,
                        'completed': 0
                    }

                daily_stats[day]['total'] += 1
                if record.is_emergency:
                    daily_stats[day]['emergency'] += 1
                if record.status == 'completed':
                    daily_stats[day]['completed'] += 1

            return jsonify({
                'success': True,
                'report': {
                    'period': {
                        'year': year,
                        'month': month,
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat()
                    },
                    'summary': {
                        'total_records': len(records),
                        'emergency_records': len([r for r in records if r.is_emergency]),
                        'completed_records': len([r for r in records if r.status == 'completed']),
                        'average_per_day': len(records) / 30 if len(records) > 0 else 0
                    },
                    'daily_statistics': daily_stats
                }
            }), 200

        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    @medical_bp.route('/dashboard/recent-activity', methods=['GET'])
    def get_recent_activity():
        """Obtener actividad reciente para dashboard"""
        try:
            limit = request.args.get('limit', 10, type=int)

            # Últimas historias clínicas
            recent_records = MedicalRecord.query.order_by(
                MedicalRecord.created_at.desc()
            ).limit(limit).all()

            # Estadísticas rápidas
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            records_today = MedicalRecord.query.filter(
                MedicalRecord.created_at >= today
            ).count()

            emergency_today = MedicalRecord.query.filter(
                MedicalRecord.created_at >= today,
                MedicalRecord.is_emergency == True
            ).count()

            return jsonify({
                'success': True,
                'recent_activity': {
                    'recent_records': [record.to_dict() for record in recent_records],
                    'today_stats': {
                        'total_records': records_today,
                        'emergency_records': emergency_today
                    }
                }
            }), 200

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