# microservices/medical_service/app/services/medical_service.py
import os
import uuid
from datetime import datetime, date
from werkzeug.utils import secure_filename
from flask import current_app
import requests
from ..models.pet import Pet, db
from ..models.medical_record import MedicalRecord, Prescription, ExamResult


class MedicalService:

    def __init__(self):
        self.allowed_extensions = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

    def allowed_file(self, filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    # =============== PET MANAGEMENT ===============

    def create_pet(self, pet_data):
        """Crear nueva mascota"""
        pet = Pet(
            owner_id=pet_data.get('owner_id'),
            name=pet_data.get('name'),
            species=pet_data.get('species'),
            breed=pet_data.get('breed'),
            birth_date=datetime.strptime(pet_data.get('birth_date'), '%Y-%m-%d').date() if pet_data.get(
                'birth_date') else None,
            weight=pet_data.get('weight'),
            gender=pet_data.get('gender'),
            microchip_number=pet_data.get('microchip_number'),
            allergies=pet_data.get('allergies'),
            medical_notes=pet_data.get('medical_notes'),
            vaccination_status=pet_data.get('vaccination_status')
        )

        db.session.add(pet)
        db.session.commit()
        return pet

    def get_pet_by_id(self, pet_id):
        """Obtener mascota por ID"""
        return Pet.query.get(pet_id)

    def get_pets_by_owner(self, owner_id):
        """Obtener mascotas de un propietario"""
        return Pet.get_by_owner(owner_id)

    def update_pet(self, pet_id, pet_data):
        """Actualizar información de mascota"""
        pet = Pet.query.get(pet_id)
        if not pet:
            return None

        # Actualizar campos permitidos
        for key, value in pet_data.items():
            if key == 'birth_date' and value:
                pet.birth_date = datetime.strptime(value, '%Y-%m-%d').date()
            elif hasattr(pet, key) and key != 'id':
                setattr(pet, key, value)

        db.session.commit()
        return pet

    def search_pets(self, search_term):
        """Buscar mascotas por nombre, microchip, especie o raza"""
        return Pet.search_pets(search_term)

    def upload_pet_photo(self, pet_id, file):
        """Subir foto de mascota"""
        if not file or not self.allowed_file(file.filename):
            return None

        # Crear directorio si no existe
        upload_folder = current_app.config['UPLOAD_FOLDER']
        pet_folder = os.path.join(upload_folder, 'pets', pet_id)
        os.makedirs(pet_folder, exist_ok=True)

        # Generar nombre único para el archivo
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(pet_folder, unique_filename)

        # Guardar archivo
        file.save(filepath)

        # Actualizar URL en la base de datos
        pet = Pet.query.get(pet_id)
        if pet:
            pet.photo_url = f"/uploads/pets/{pet_id}/{unique_filename}"
            db.session.commit()
            return pet.photo_url

        return None

    # =============== MEDICAL RECORDS ===============

    def create_medical_record(self, record_data):
        """Crear nueva historia clínica"""
        medical_record = MedicalRecord(
            pet_id=record_data.get('pet_id'),
            veterinarian_id=record_data.get('veterinarian_id'),
            appointment_id=record_data.get('appointment_id'),
            symptoms_description=record_data.get('symptoms_description'),
            physical_examination=record_data.get('physical_examination'),
            diagnosis=record_data.get('diagnosis'),
            treatment=record_data.get('treatment'),
            medications_prescribed=record_data.get('medications_prescribed'),
            exams_requested=record_data.get('exams_requested'),
            observations=record_data.get('observations'),
            next_appointment_recommendation=record_data.get('next_appointment_recommendation'),
            weight_at_visit=record_data.get('weight_at_visit'),
            temperature=record_data.get('temperature'),
            pulse=record_data.get('pulse'),
            respiratory_rate=record_data.get('respiratory_rate'),
            is_emergency=record_data.get('is_emergency', False),
            status='draft'
        )

        db.session.add(medical_record)
        db.session.commit()
        return medical_record

    def get_medical_record_by_id(self, record_id):
        """Obtener historia clínica por ID"""
        return MedicalRecord.query.get(record_id)

    def get_medical_records_by_pet(self, pet_id):
        """Obtener historias clínicas de una mascota"""
        return MedicalRecord.get_by_pet(pet_id)

    def update_medical_record(self, record_id, record_data):
        """Actualizar historia clínica"""
        medical_record = MedicalRecord.query.get(record_id)
        if not medical_record:
            return None

        # Actualizar campos permitidos
        for key, value in record_data.items():
            if hasattr(medical_record, key) and key != 'id':
                setattr(medical_record, key, value)

        db.session.commit()
        return medical_record

    def complete_medical_record(self, record_id):
        """Marcar historia clínica como completada"""
        medical_record = MedicalRecord.query.get(record_id)
        if medical_record:
            medical_record.status = 'completed'
            db.session.commit()

            # Marcar cita como completada si existe
            if medical_record.appointment_id:
                self._complete_appointment(medical_record.appointment_id)

            return medical_record
        return None

    def _complete_appointment(self, appointment_id):
        """Marcar cita como completada en el appointment service"""
        try:
            url = f"{current_app.config['APPOINTMENT_SERVICE_URL']}/appointments/complete/{appointment_id}"
            response = requests.put(url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"Error completando cita: {e}")
            return False

    # =============== PRESCRIPTIONS ===============

    def add_prescription(self, prescription_data):
        """Agregar prescripción a historia clínica"""
        prescription = Prescription(
            medical_record_id=prescription_data.get('medical_record_id'),
            medication_id=prescription_data.get('medication_id'),
            medication_name=prescription_data.get('medication_name'),
            dosage=prescription_data.get('dosage'),
            frequency=prescription_data.get('frequency'),
            duration=prescription_data.get('duration'),
            quantity_prescribed=prescription_data.get('quantity_prescribed'),
            instructions=prescription_data.get('instructions')
        )

        db.session.add(prescription)
        db.session.commit()

        # Actualizar inventario si se proporciona medication_id
        if prescription_data.get('medication_id') and prescription_data.get('quantity_prescribed'):
            self._update_medication_stock(
                prescription_data.get('medication_id'),
                prescription_data.get('quantity_prescribed')
            )

        return prescription

    def _update_medication_stock(self, medication_id, quantity_used):
        """Actualizar stock de medicamento en inventory service"""
        try:
            url = f"{current_app.config['INVENTORY_SERVICE_URL']}/inventory/update-stock"
            data = {
                'medication_id': medication_id,
                'quantity_change': -quantity_used,  # Reducir stock
                'reason': 'prescription'
            }
            response = requests.put(url, json=data, timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"Error actualizando stock: {e}")
            return False

    # =============== EXAM RESULTS ===============

    def add_exam_result(self, exam_data, file=None):
        """Agregar resultado de examen"""
        exam_result = ExamResult(
            medical_record_id=exam_data.get('medical_record_id'),
            exam_id=exam_data.get('exam_id'),
            exam_name=exam_data.get('exam_name'),
            observations=exam_data.get('observations'),
            date_performed=datetime.strptime(exam_data.get('date_performed'), '%Y-%m-%d').date() if exam_data.get(
                'date_performed') else None,
            performed_by=exam_data.get('performed_by')
        )

        # Subir archivo si se proporciona
        if file and self.allowed_file(file.filename):
            file_url = self._save_exam_file(exam_data.get('medical_record_id'), file)
            exam_result.result_file_url = file_url

        db.session.add(exam_result)
        db.session.commit()
        return exam_result

    def _save_exam_file(self, medical_record_id, file):
        """Guardar archivo de resultado de examen"""
        # Crear directorio si no existe
        upload_folder = current_app.config['UPLOAD_FOLDER']
        exam_folder = os.path.join(upload_folder, 'exams', medical_record_id)
        os.makedirs(exam_folder, exist_ok=True)

        # Generar nombre único para el archivo
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(exam_folder, unique_filename)

        # Guardar archivo
        file.save(filepath)

        return f"/uploads/exams/{medical_record_id}/{unique_filename}"

    # =============== REPORTS ===============

    def get_medical_summary(self, pet_id):
        """Obtener resumen médico de una mascota"""
        pet = Pet.query.get(pet_id)
        if not pet:
            return None

        medical_records = MedicalRecord.get_by_pet(pet_id)

        return {
            'pet': pet.to_dict(),
            'total_visits': len(medical_records),
            'last_visit': medical_records[0].created_at.isoformat() if medical_records else None,
            'recent_records': [record.to_dict() for record in medical_records[:5]],
            'allergies': pet.allergies,
            'vaccination_status': pet.vaccination_status
        }