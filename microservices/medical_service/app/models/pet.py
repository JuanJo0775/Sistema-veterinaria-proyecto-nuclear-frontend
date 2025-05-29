# microservices/medical_service/app/models/pet.py
from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime, date

db = SQLAlchemy()


class Pet(db.Model):
    __tablename__ = 'pets'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = db.Column(db.String(36), nullable=False)  # FK a users
    name = db.Column(db.String(100), nullable=False)
    species = db.Column(db.String(50), nullable=False)
    breed = db.Column(db.String(100))
    birth_date = db.Column(db.Date)
    weight = db.Column(db.Numeric(5, 2))
    gender = db.Column(db.String(10))
    microchip_number = db.Column(db.String(50))
    photo_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Campos adicionales médicos
    allergies = db.Column(db.Text)
    medical_notes = db.Column(db.Text)
    vaccination_status = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    # Relaciones
    medical_records = db.relationship('MedicalRecord', backref='pet', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'name': self.name,
            'species': self.species,
            'breed': self.breed,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'weight': float(self.weight) if self.weight else None,
            'gender': self.gender,
            'microchip_number': self.microchip_number,
            'photo_url': self.photo_url,
            'allergies': self.allergies,
            'medical_notes': self.medical_notes,
            'vaccination_status': self.vaccination_status,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def get_age(self):
        """Calcular edad en años"""
        if self.birth_date:
            today = date.today()
            age = today.year - self.birth_date.year
            if today.month < self.birth_date.month or (
                    today.month == self.birth_date.month and today.day < self.birth_date.day):
                age -= 1
            return age
        return None

    @classmethod
    def get_by_owner(cls, owner_id):
        return cls.query.filter_by(owner_id=owner_id, is_active=True).order_by(cls.name).all()

    @classmethod
    def search_pets(cls, search_term):
        return cls.query.filter(
            cls.is_active == True,
            db.or_(
                cls.name.ilike(f'%{search_term}%'),
                cls.microchip_number.ilike(f'%{search_term}%'),
                cls.species.ilike(f'%{search_term}%'),
                cls.breed.ilike(f'%{search_term}%')
            )
        ).all()