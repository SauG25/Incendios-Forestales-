import duckdb
import os

# Rutas universales (igual que en tu minero)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Retrocedemos 3 niveles hasta llegar a IncendiosForestales
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..")) 
DB_PATH = os.path.join(ROOT_DIR, 'data', 'BaseDeDatos.db')

try:
    print(f"Buscando base de datos en: {DB_PATH}") # Un print extra para confirmar
    con = duckdb.connect(DB_PATH, read_only=True)
    
    total_clima = con.execute("SELECT COUNT(*) FROM climatologia").fetchone()[0]
    
    ultimos = con.execute("""
        SELECT id_clave_inc, fecha_de_observacion, resultado_numerico 
        FROM climatologia 
        ORDER BY id_registro DESC 
        LIMIT 5
    """).df()
    
    print(f"\n🔥 ¡El minero lleva {total_clima:,} registros insertados!")
    print("\nÚltimos datos capturados:")
    print(ultimos)
    
    con.close()
except Exception as e:
    print(f"\nError al conectar: {e}")