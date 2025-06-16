# microservices/auth_service/app/services/auth_service.py
import jwt
import uuid
from datetime import datetime, timedelta
from flask import current_app
from ..models.user import User, db


class AuthService:
    def generate_token(self, user):
        payload = {
            'user_id': str(user.id),  # ← FIX: Convertir UUID a string
            'email': user.email,
            'role': user.role,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        return token

    def verify_token(self, token):
        try:
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            # Convertir string de vuelta a UUID para la consulta
            user_id = uuid.UUID(payload['user_id']) if isinstance(payload['user_id'], str) else payload['user_id']
            user = User.query.get(user_id)
            return user
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except (ValueError, TypeError):  # Error de conversión UUID
            return None

    def create_user(self, user_data):
        user = User(
            email=user_data.get('email'),
            first_name=user_data.get('first_name'),
            last_name=user_data.get('last_name'),
            phone=user_data.get('phone'),
            address=user_data.get('address'),
            role=user_data.get('role', 'client')
        )
        user.set_password(user_data.get('password'))

        db.session.add(user)
        db.session.commit()
        return user

    def authenticate_user(self, email, password):
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.is_active:
            return user
        return None

    def change_password(self, user_id, old_password, new_password):
        # Convertir string a UUID si es necesario
        if isinstance(user_id, str):
            try:
                user_id = uuid.UUID(user_id)
            except ValueError:
                return False

        user = User.query.get(user_id)
        if user and user.check_password(old_password):
            user.set_password(new_password)
            db.session.commit()
            return True
        return False

    def get_user_by_id(self, user_id):
        """Obtener usuario por ID"""
        try:
            conn = self.get_connection()
            if not conn:
                return None

            cur = conn.cursor()

            # Convertir a UUID si es string
            if isinstance(user_id, str):
                try:
                    import uuid
                    user_uuid = uuid.UUID(user_id)
                except ValueError:
                    print(f"❌ ID de usuario inválido: {user_id}")
                    return None
            else:
                user_uuid = user_id

            cur.execute("""
                SELECT id, email, first_name, last_name, phone, address, 
                       role, is_active, created_at, updated_at
                FROM users 
                WHERE id = %s
            """, (user_uuid,))

            row = cur.fetchone()
            cur.close()
            conn.close()

            if row:
                from ..models.user import User
                return User(
                    id=row[0],
                    email=row[1],
                    first_name=row[2],
                    last_name=row[3],
                    phone=row[4],
                    address=row[5],
                    role=row[6],
                    is_active=row[7],
                    created_at=row[8],
                    updated_at=row[9]
                )

            return None

        except Exception as e:
            print(f"❌ Error obteniendo usuario por ID: {e}")
            return None

    def update_user(self, user_id, user_data):
        # Convertir string a UUID si es necesario
        if isinstance(user_id, str):
            try:
                user_id = uuid.UUID(user_id)
            except ValueError:
                return None

        user = User.query.get(user_id)
        if user:
            for key, value in user_data.items():
                if hasattr(user, key) and key not in ['id', 'password', 'password_hash']:
                    setattr(user, key, value)
            db.session.commit()
            return user
        return None