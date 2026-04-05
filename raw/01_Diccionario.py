import json
import duckdb
import os

# 1. Configuracion de rutas relativas universales
# Ubicacion: /IncendiosForestales/02_InsercionDeDatos/02_NASA/scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Subimos tres niveles para llegar a la raiz del proyecto
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))

# Definicion de rutas absolutas para evitar duplicados de base de datos
DB_PATH = os.path.join(ROOT_DIR, 'data', 'BaseDeDatos.db')
JSON_PATH = os.path.join(ROOT_DIR, '01_ExtraccionDeDatos', 'DatosNASA', 'raw', 'diccionario_limpio.json')

def cargar_diccionario():
    # Verificacion de existencia de archivos
    if not os.path.exists(JSON_PATH):
        print(f"Error: Archivo JSON no encontrado en {JSON_PATH}")
        return

    # Conexion a la base de datos central
    print(f"Conectando a base de datos en: {DB_PATH}")
    con = duckdb.connect(DB_PATH)
    
    # 2. Limpieza preventiva
    # Al igual que con CONAFOR, limpiamos para asegurar que el catalogo sea fiel al JSON
    print("Limpiando tabla diccionario...")
    try:
        con.execute("DELETE FROM diccionario;")
    except Exception as e:
        print(f"Aviso al limpiar: {e}")

    # 3. Lectura del archivo JSON
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            variables = json.load(f)
    except Exception as e:
        print(f"Error al leer el JSON: {e}")
        return

    print(f"Iniciando carga de {len(variables)} variables...")

    # 4. Insercion de datos
    for var in variables:
        con.execute("""
            INSERT INTO diccionario (id_variable, fuente, nombre_completo, unidad_de_medida)
            VALUES (?, ?, ?, ?)
        """, (
            var.get('id'), 
            var.get('fuente', 'NASA'), 
            var.get('nombre', 'Sin nombre'), 
            var.get('unidades', 'Por definir')
        ))

    # Validacion final
    total = con.execute("SELECT COUNT(*) FROM diccionario").fetchone()[0]
    print(f"Carga finalizada. Total de registros en diccionario: {total}")
    
    con.close()

if __name__ == "__main__":
    cargar_diccionario()