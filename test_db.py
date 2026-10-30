import os
import psycopg2

# Tu URL externa de Render
DATABASE_URL = "postgresql://qr_attendance_db_rih4_user:lgg4UlNdjSSpGnaLmkniCgKHMtBnH8xk@dpg-dbi5psifngtc73cck770-a.oregon-postgres.render.com/qr_attendance_db_rih4"

try:
    print("Intentando conectar a PostgreSQL en Render...")
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = conn.cursor()
    
    # Probar una consulta simple
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print(f" ¡Conexión exitosa!")
    print(f" Versión de la base de datos: {db_version[0]}")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ Error al conectar: {e}")