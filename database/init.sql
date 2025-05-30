-- database/init.sql
-- Estructura completa y corregida de la base de datos para clínica veterinaria

-- Crear extensión para UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Crear enums
CREATE TYPE user_role_enum AS ENUM ('client', 'veterinarian', 'receptionist', 'auxiliary', 'admin');
CREATE TYPE appointment_status_enum AS ENUM ('scheduled', 'confirmed', 'completed', 'cancelled');
CREATE TYPE notification_type_enum AS ENUM ('appointment_reminder', 'new_appointment', 'inventory_alert', 'general');
CREATE TYPE payment_status_enum AS ENUM ('pending', 'paid', 'partial', 'refunded');
CREATE TYPE medical_record_status AS ENUM ('draft', 'completed', 'reviewed');
CREATE TYPE movement_type_enum AS ENUM ('in', 'out', 'adjustment');

-- Tabla de usuarios
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role user_role_enum NOT NULL DEFAULT 'client',
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(15),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Tabla de mascotas (actualizada con campos adicionales)
CREATE TABLE pets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    species VARCHAR(50) NOT NULL,
    breed VARCHAR(100),
    birth_date DATE,
    weight DECIMAL(5,2),
    gender VARCHAR(10),
    microchip_number VARCHAR(50),
    photo_url TEXT,
    allergies TEXT,
    medical_notes TEXT,
    vaccination_status TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de horarios de veterinarios
CREATE TABLE veterinarian_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    veterinarian_id UUID REFERENCES users(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_available BOOLEAN DEFAULT TRUE
);

-- Tabla de citas
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pet_id UUID REFERENCES pets(id) ON DELETE CASCADE,
    veterinarian_id UUID REFERENCES users(id) ON DELETE SET NULL,
    client_id UUID REFERENCES users(id) ON DELETE CASCADE,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status appointment_status_enum DEFAULT 'scheduled',
    reason TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de historias clínicas (actualizada)
CREATE TABLE medical_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pet_id UUID REFERENCES pets(id) ON DELETE CASCADE,
    veterinarian_id UUID REFERENCES users(id) ON DELETE SET NULL,
    appointment_id UUID REFERENCES appointments(id) ON DELETE SET NULL,
    symptoms_description TEXT,
    physical_examination TEXT,
    diagnosis TEXT,
    treatment TEXT,
    medications_prescribed TEXT,
    exams_requested TEXT,
    observations TEXT,
    next_appointment_recommendation TEXT,
    weight_at_visit DECIMAL(5,2),
    temperature DECIMAL(4,1),
    pulse INTEGER,
    respiratory_rate INTEGER,
    status medical_record_status DEFAULT 'draft',
    is_emergency BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de medicamentos (actualizada con campos adicionales)
CREATE TABLE medications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    unit_price DECIMAL(10,2) NOT NULL,
    expiration_date DATE,
    supplier VARCHAR(255),
    minimum_stock_alert INTEGER DEFAULT 10,
    category VARCHAR(100),
    presentation VARCHAR(100),
    concentration VARCHAR(50),
    laboratory VARCHAR(255),
    batch_number VARCHAR(50),
    storage_conditions TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de movimientos de stock (NUEVA - esta faltaba)
CREATE TABLE stock_movements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    medication_id UUID REFERENCES medications(id) ON DELETE CASCADE,
    movement_type movement_type_enum NOT NULL,
    quantity INTEGER NOT NULL,
    previous_stock INTEGER NOT NULL,
    new_stock INTEGER NOT NULL,
    reason VARCHAR(255),
    reference_id UUID,
    user_id UUID,
    unit_cost DECIMAL(10,2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de prescripciones (actualizada)
CREATE TABLE prescriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    medical_record_id UUID REFERENCES medical_records(id) ON DELETE CASCADE,
    medication_id UUID REFERENCES medications(id) ON DELETE SET NULL,
    medication_name VARCHAR(255) NOT NULL,
    dosage VARCHAR(100),
    frequency VARCHAR(100),
    duration VARCHAR(100),
    quantity_prescribed INTEGER,
    instructions TEXT
);

-- Tabla de exámenes
CREATE TABLE exams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    category VARCHAR(100)
);

-- Tabla de resultados de exámenes (actualizada)
CREATE TABLE exam_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    medical_record_id UUID REFERENCES medical_records(id) ON DELETE CASCADE,
    exam_id UUID REFERENCES exams(id) ON DELETE SET NULL,
    exam_name VARCHAR(255) NOT NULL,
    result_file_url TEXT,
    observations TEXT,
    date_performed DATE,
    performed_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de facturas
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    appointment_id UUID REFERENCES appointments(id) ON DELETE SET NULL,
    client_id UUID REFERENCES users(id) ON DELETE CASCADE,
    total_amount DECIMAL(10,2) NOT NULL,
    consultation_fee DECIMAL(10,2),
    medications_cost DECIMAL(10,2),
    exams_cost DECIMAL(10,2),
    payment_status payment_status_enum DEFAULT 'pending',
    payment_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de notificaciones (actualizada)
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type notification_type_enum NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP,
    email_sent BOOLEAN DEFAULT FALSE,
    sms_sent BOOLEAN DEFAULT FALSE,
    email_sent_at TIMESTAMP,
    sms_sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para mejorar performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_pets_owner_id ON pets(owner_id);
CREATE INDEX idx_pets_microchip ON pets(microchip_number);
CREATE INDEX idx_appointments_date ON appointments(appointment_date);
CREATE INDEX idx_appointments_veterinarian ON appointments(veterinarian_id);
CREATE INDEX idx_appointments_client ON appointments(client_id);
CREATE INDEX idx_appointments_status ON appointments(status);
CREATE INDEX idx_medical_records_pet ON medical_records(pet_id);
CREATE INDEX idx_medical_records_vet ON medical_records(veterinarian_id);
CREATE INDEX idx_medical_records_status ON medical_records(status);
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read);
CREATE INDEX idx_medications_stock ON medications(stock_quantity);
CREATE INDEX idx_medications_expiration ON medications(expiration_date);
CREATE INDEX idx_medications_active ON medications(is_active);
CREATE INDEX idx_stock_movements_medication ON stock_movements(medication_id);
CREATE INDEX idx_stock_movements_date ON stock_movements(created_at);
CREATE INDEX idx_prescriptions_record ON prescriptions(medical_record_id);
CREATE INDEX idx_exam_results_record ON exam_results(medical_record_id);

-- Triggers para updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pets_updated_at BEFORE UPDATE ON pets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_appointments_updated_at BEFORE UPDATE ON appointments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_medical_records_updated_at BEFORE UPDATE ON medical_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_medications_updated_at BEFORE UPDATE ON medications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insertar usuario administrador por defecto
INSERT INTO users (email, password_hash, role, first_name, last_name, phone)
VALUES (
    'admin@veterinariaclinic.com',
    '$2b$12$8.5E1Q7ZJZeOSMDJfK0XhOyVQ8PzDVqKqP0Lm4UzKUJ5zRzJZeOSM', -- password: admin123
    'admin',
    'Administrador',
    'Sistema',
    '+1234567890'
);

-- Insertar veterinario de ejemplo
INSERT INTO users (email, password_hash, role, first_name, last_name, phone)
VALUES (
    'vet@veterinariaclinic.com',
    '$2b$12$8.5E1Q7ZJZeOSMDJfK0XhOyVQ8PzDVqKqP0Lm4UzKUJ5zRzJZeOSM', -- password: admin123
    'veterinarian',
    'Dr. Juan',
    'Pérez',
    '+1234567891'
);

-- Insertar recepcionista de ejemplo
INSERT INTO users (email, password_hash, role, first_name, last_name, phone)
VALUES (
    'recepcion@veterinariaclinic.com',
    '$2b$12$8.5E1Q7ZJZeOSMDJfK0XhOyVQ8PzDVqKqP0Lm4UzKUJ5zRzJZeOSM', -- password: admin123
    'receptionist',
    'María',
    'García',
    '+1234567892'
);

-- Insertar horarios para el veterinario
INSERT INTO veterinarian_schedules (veterinarian_id, day_of_week, start_time, end_time)
SELECT
    u.id,
    day_num,
    '08:00'::time,
    CASE
        WHEN day_num = 5 THEN '16:00'::time  -- Viernes hasta las 4 PM
        ELSE '17:00'::time                   -- Otros días hasta las 5 PM
    END
FROM users u, generate_series(1, 5) AS day_num  -- Lunes a Viernes
WHERE u.email = 'vet@veterinariaclinic.com';

-- Insertar algunos datos de ejemplo para exámenes básicos
INSERT INTO exams (name, description, price, category) VALUES
('Hemograma Completo', 'Análisis completo de sangre', 45000, 'Laboratorio'),
('Radiografía Torácica', 'Rayos X del tórax', 80000, 'Imagenología'),
('Ultrasonido Abdominal', 'Ecografía del abdomen', 120000, 'Imagenología'),
('Perfil Renal', 'Análisis de función renal', 60000, 'Laboratorio'),
('Perfil Hepático', 'Análisis de función hepática', 70000, 'Laboratorio'),
('Coprológico', 'Examen de heces', 25000, 'Laboratorio'),
('Uroanálisis', 'Examen de orina', 30000, 'Laboratorio'),
('Radiografía Abdominal', 'Rayos X del abdomen', 75000, 'Imagenología');

-- Insertar medicamentos básicos de ejemplo
INSERT INTO medications (name, description, stock_quantity, unit_price, supplier, minimum_stock_alert, category, presentation, concentration, laboratory) VALUES
('Amoxicilina 500mg', 'Antibiótico para infecciones bacterianas', 100, 2500, 'Laboratorios Veterinarios SA', 20, 'Antibiótico', 'Comprimidos', '500mg', 'LabVet'),
('Meloxicam 5mg', 'Antiinflamatorio no esteroideo', 50, 3200, 'VetPharma Ltda', 15, 'Antiinflamatorio', 'Comprimidos', '5mg', 'VetPharma'),
('Furosemida 40mg', 'Diurético para insuficiencia cardíaca', 30, 4100, 'Laboratorios Veterinarios SA', 10, 'Diurético', 'Comprimidos', '40mg', 'LabVet'),
('Prednisona 20mg', 'Corticoesteroide antiinflamatorio', 25, 1800, 'VetPharma Ltda', 10, 'Corticoesteroide', 'Comprimidos', '20mg', 'VetPharma'),
('Tramadol 50mg', 'Analgésico para dolor moderado a severo', 40, 5500, 'Analgésicos Vet SA', 15, 'Analgésico', 'Comprimidos', '50mg', 'AnalgVet'),
('Ivermectina 1%', 'Antiparasitario externo e interno', 20, 8500, 'Laboratorios Veterinarios SA', 8, 'Antiparasitario', 'Solución inyectable', '1%', 'LabVet'),
('Dexametasona 4mg', 'Corticoesteroide potente', 15, 6200, 'VetPharma Ltda', 5, 'Corticoesteroide', 'Ampolla', '4mg/ml', 'VetPharma'),
('Enrofloxacina 50mg', 'Antibiótico fluoroquinolona', 35, 4800, 'Laboratorios Veterinarios SA', 12, 'Antibiótico', 'Comprimidos', '50mg', 'LabVet');

-- Crear vista para reportes de stock
CREATE VIEW v_medication_stock_status AS
SELECT
    m.id,
    m.name,
    m.category,
    m.stock_quantity,
    m.minimum_stock_alert,
    m.expiration_date,
    CASE
        WHEN m.stock_quantity <= 0 THEN 'Sin Stock'
        WHEN m.stock_quantity <= m.minimum_stock_alert THEN 'Stock Bajo'
        ELSE 'En Stock'
    END as stock_status,
    CASE
        WHEN m.expiration_date IS NULL THEN NULL
        WHEN m.expiration_date <= CURRENT_DATE THEN 'Vencido'
        WHEN m.expiration_date <= CURRENT_DATE + INTERVAL '30 days' THEN 'Por Vencer'
        ELSE 'Vigente'
    END as expiration_status,
    (m.expiration_date - CURRENT_DATE) as days_to_expiration
FROM medications m
WHERE m.is_active = true;

-- Crear vista para resumen de citas por veterinario
CREATE VIEW v_appointment_summary AS
SELECT
    u.id as veterinarian_id,
    u.first_name || ' ' || u.last_name as veterinarian_name,
    COUNT(a.id) as total_appointments,
    COUNT(CASE WHEN a.status = 'scheduled' THEN 1 END) as scheduled_count,
    COUNT(CASE WHEN a.status = 'completed' THEN 1 END) as completed_count,
    COUNT(CASE WHEN a.status = 'cancelled' THEN 1 END) as cancelled_count
FROM users u
LEFT JOIN appointments a ON u.id = a.veterinarian_id
WHERE u.role = 'veterinarian' AND u.is_active = true
GROUP BY u.id, u.first_name, u.last_name;

-- Comentarios para documentación
COMMENT ON TABLE users IS 'Tabla principal de usuarios del sistema';
COMMENT ON TABLE pets IS 'Tabla de mascotas/pacientes de la clínica';
COMMENT ON TABLE appointments IS 'Tabla de citas médicas agendadas';
COMMENT ON TABLE medical_records IS 'Historias clínicas de las mascotas';
COMMENT ON TABLE medications IS 'Inventario de medicamentos';
COMMENT ON TABLE stock_movements IS 'Registro de movimientos de inventario';
COMMENT ON TABLE notifications IS 'Sistema de notificaciones del sistema';

COMMENT ON COLUMN users.role IS 'Rol del usuario: client, veterinarian, receptionist, auxiliary, admin';
COMMENT ON COLUMN appointments.status IS 'Estado de la cita: scheduled, confirmed, completed, cancelled';
COMMENT ON COLUMN medical_records.status IS 'Estado del registro médico: draft, completed, reviewed';
COMMENT ON COLUMN stock_movements.movement_type IS 'Tipo de movimiento: in (entrada), out (salida), adjustment (ajuste)';

-- Función para limpiar notificaciones antiguas (ejecutar periódicamente)
CREATE OR REPLACE FUNCTION cleanup_old_notifications()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM notifications
    WHERE created_at < CURRENT_DATE - INTERVAL '90 days'
    AND is_read = true;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Función para obtener estadísticas del sistema
CREATE OR REPLACE FUNCTION get_system_stats()
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'total_users', (SELECT COUNT(*) FROM users WHERE is_active = true),
        'total_pets', (SELECT COUNT(*) FROM pets WHERE is_active = true),
        'total_appointments_today', (SELECT COUNT(*) FROM appointments WHERE appointment_date = CURRENT_DATE),
        'total_medications', (SELECT COUNT(*) FROM medications WHERE is_active = true),
        'low_stock_medications', (SELECT COUNT(*) FROM medications WHERE stock_quantity <= minimum_stock_alert AND is_active = true),
        'expired_medications', (SELECT COUNT(*) FROM medications WHERE expiration_date < CURRENT_DATE AND is_active = true)
    ) INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql;