import duckdb
import json
import os

# --- RUTAS AUTOMATICAS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))

DB_PATH = os.path.join(ROOT_DIR, 'data', 'BaseDeDatos.db')
JSON_VERIFICADO = os.path.join(ROOT_DIR, '01_ExtraccionDeDatos', 'DatosNASA', 'raw', 'diccionario_verificado.json')

def sincronizar_catalogo():
    # 1. Verificacion de seguridad
    if not os.path.exists(JSON_VERIFICADO):
        print(f"Error: No se encontro el archivo en {JSON_VERIFICADO}")
        print("Asegurate de haber corrido el Depurador primero.")
        return

    if not os.path.exists(DB_PATH):
        print(f"Error: No se encontro la base de datos en {DB_PATH}")
        return

    # 2. Conexion
    print(f"Conectando a la base de datos: {DB_PATH}")
    con = duckdb.connect(DB_PATH)
    
    try:
        # 3. Leer el diccionario depurado
        with open(JSON_VERIFICADO, 'r', encoding='utf-8') as f:
            variables_reales = json.load(f)

        print(f"Sincronizando {len(variables_reales)} variables verificadas...")

        # 4. Limpiar la tabla actual (para evitar duplicados o basura)
        con.execute("DELETE FROM diccionario;")

        # 5. Insertar los datos verificados
        for var in variables_reales:
            # Usamos .get() para que si falta algun campo, el script no truene
            con.execute("""
                INSERT INTO diccionario (id_variable, fuente, nombre_completo, unidad_de_medida)
                VALUES (?, ?, ?, ?)
            """, (
                var.get('id'), 
                'NASA', 
                var.get('nombre', 'Sin nombre'), 
                var.get('unidades', 'N/A')
            ))

        total = con.execute("SELECT COUNT(*) FROM diccionario").fetchone()[0]
        print(f"Sincronizacion finalizada. Variables en catalogo: {total}")

    except Exception as e:
        print(f"Error durante la sincronizacion: {e}")
    
    finally:
        con.close()
        print("Conexion cerrada.")

if __name__ == "__main__":
    sincronizar_catalogo()