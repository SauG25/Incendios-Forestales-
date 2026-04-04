#crear el cubito olap para el analisis predictivo 
import sqlite3

# 1. Crear la conexión a la base de datos
conexion = sqlite3.connect('incendios_tlaxcala.db')
# 2. Crear el objeto cursor
cursor = conexion.cursor()

# 3. Corregir execute y foreign_keys
cursor.execute("PRAGMA foreign_keys = ON;")

def crear_dimesiones():
    #TABLA DE HECHOS INCENDIO
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS INCENDIOS (
            id_incendio INTEGER PRIMARY KEY AUTOINCREMENT,
            anio INTEGER,
            clave_incendio TEXT,
            fecha_inicio TEXT,
            fecha_termino TEXT,
            duracion_dias INTEGER,
            tipo_vegetacion TEXT,
            causa TEXT,
            total_hectareas REAL
        )
    ''')
