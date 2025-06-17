# update_database.py - Ejecutar desde la raíz del proyecto
import psycopg2
import os


def update_appointments_table():
    """Actualizar la tabla appointments con las columnas faltantes"""
    try:
        # Configuración de la base de datos
        host = os.environ.get('POSTGRES_HOST', 'localhost')
        port = os.environ.get('POSTGRES_PORT', '5432')
        database = os.environ.get('POSTGRES_DB', 'veterinary-system')
        user = os.environ.get('POSTGRES_USER', 'postgres')
        password = os.environ.get('POSTGRES_PASSWORD', 'bocato0731')

        print(f"🔌 Conectando a PostgreSQL: {user}@{host}:{port}/{database}")

        # Conectar a la base de datos
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        conn.autocommit = True
        cur = conn.cursor()

        print("✅ Conexión exitosa")

        # 1. Verificar columnas existentes
        print("\n📊 Verificando estructura actual de la tabla appointments...")
        cur.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'appointments' 
            ORDER BY ordinal_position;
        """)

        current_columns = cur.fetchall()
        print("Columnas actuales:")
        for col in current_columns:
            print(f"  - {col[0]} ({col[1]}) - Nullable: {col[2]}")

        # 2. Agregar columnas faltantes
        print("\n🔧 Agregando columnas faltantes...")

        columns_to_add = [
            ("appointment_type", "VARCHAR(50) DEFAULT 'consultation'"),
            ("pet_name", "VARCHAR(100)"),
            ("pet_species", "VARCHAR(50)"),
            ("owner_name", "VARCHAR(200)")
        ]

        for col_name, col_definition in columns_to_add:
            try:
                cur.execute(f"ALTER TABLE appointments ADD COLUMN IF NOT EXISTS {col_name} {col_definition};")
                print(f"  ✅ Columna {col_name} agregada")
            except Exception as e:
                print(f"  ⚠️ Error agregando {col_name}: {e}")

        # 3. Crear enum para appointment_type
        print("\n🎭 Creando enum para appointment_type...")
        try:
            cur.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_type_enum') THEN
                        CREATE TYPE appointment_type_enum AS ENUM ('consultation', 'surgery', 'vaccination', 'emergency', 'control');
                        RAISE NOTICE 'Enum appointment_type_enum creado';
                    ELSE
                        RAISE NOTICE 'Enum appointment_type_enum ya existe';
                    END IF;
                END $$;
            """)
            print("  ✅ Enum appointment_type_enum verificado/creado")
        except Exception as e:
            print(f"  ⚠️ Error con enum: {e}")

        # 4. Actualizar appointment_type para usar el enum
        print("\n🔄 Actualizando tipo de columna appointment_type...")
        try:
            cur.execute("""
                ALTER TABLE appointments 
                ALTER COLUMN appointment_type TYPE appointment_type_enum 
                USING appointment_type::appointment_type_enum;
            """)
            print("  ✅ Columna appointment_type actualizada al enum")
        except Exception as e:
            print(f"  ⚠️ Error actualizando tipo de appointment_type: {e}")

        # 5. Crear índices
        print("\n📈 Creando índices...")
        indices = [
            ("idx_appointments_type", "appointments(appointment_type)"),
            ("idx_appointments_pet_name", "appointments(pet_name)")
        ]

        for idx_name, idx_definition in indices:
            try:
                cur.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_definition};")
                print(f"  ✅ Índice {idx_name} creado")
            except Exception as e:
                print(f"  ⚠️ Error creando índice {idx_name}: {e}")

        # 6. Verificar estructura final
        print("\n✅ Verificando estructura final...")
        cur.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'appointments' 
            ORDER BY ordinal_position;
        """)

        final_columns = cur.fetchall()
        print("Columnas finales:")
        for col in final_columns:
            print(f"  - {col[0]} ({col[1]}) - Nullable: {col[2]}")

        # 7. Verificar datos
        cur.execute("SELECT COUNT(*) FROM appointments;")
        count = cur.fetchone()[0]
        print(f"\n📊 Total de registros en appointments: {count}")

        cur.close()
        conn.close()

        print("\n🎉 ¡Actualización de base de datos completada exitosamente!")
        return True

    except psycopg2.Error as e:
        print(f"❌ Error de PostgreSQL: {e}")
        return False
    except Exception as e:
        print(f"❌ Error general: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Iniciando actualización de la base de datos...")
    success = update_appointments_table()

    if success:
        print("\n✅ La base de datos ha sido actualizada correctamente.")
        print("Ahora puedes reiniciar el Appointment Service:")
        print("  cd microservices/appointment_service")
        print("  python main.py")
    else:
        print("\n❌ Hubo errores actualizando la base de datos.")
        print("Verifica la configuración de PostgreSQL y vuelve a intentar.")