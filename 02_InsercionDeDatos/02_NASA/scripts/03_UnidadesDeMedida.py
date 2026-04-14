import duckdb
import json
import os
import requests
import time

# --- CONFIGURACIÓN DE RUTAS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))

DB_PATH = os.path.join(ROOT_DIR, 'data', 'BaseDeDatos_Raw.db')
JSON_PATH = os.path.join(ROOT_DIR, '01_ExtraccionDeDatos', 'DatosNASA', 'raw', 'diccionario_verificado.json')

def restaurar_y_limpiar_diccionario():
    if not os.path.exists(JSON_PATH):
        print("Error: No se encuentra el JSON.")
        return

    con = duckdb.connect(DB_PATH)
    
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            variables_json = json.load(f)

        print(f"Restaurando nombres para {len(variables_json)} variables...")

        for var in variables_json:
            v_id = var.get('id')
            v_nombre = var.get('nombre') # El nombre que SÍ tienes en el JSON
            
            # 1. Restauramos el nombre del JSON para que ya no salga vacío
            con.execute("""
                UPDATE diccionario 
                SET nombre_completo = ? 
                WHERE id_variable = ?
            """, (v_nombre, v_id))

        print("✅ Nombres restaurados desde el JSON.")

        # 2. Solo si las unidades están en 'Por definir', le preguntamos a la NASA
        # Pero esta vez con cuidado de NO tocar el nombre completo
        print("Buscando unidades faltantes en la NASA...")
        ids_nasa = [v['id'] for v in variables_json if v.get('fuente') != 'geosit'] # Solo NASA
        paquetes = [ids_nasa[i:i + 20] for i in range(0, len(ids_nasa), 20)]

        for bloque in paquetes:
            bundle = ",".join(bloque)
            url = f"https://power.larc.nasa.gov/api/temporal/daily/point?start=20230101&end=20230101&latitude=19.4&longitude=-99.1&community=ag&parameters={bundle}&format=json"
            
            try:
                res = requests.get(url, timeout=20)
                if res.status_code == 200:
                    meta = res.json().get('parameters', {}) or res.json().get('header', {}).get('parameter', {})
                    for vid, info in meta.items():
                        unidad = info.get('units', 'n/a')
                        # CRUCIAL: Solo actualizamos la unidad, NO el nombre
                        con.execute("UPDATE diccionario SET unidad_de_medida = ? WHERE id_variable = ?", (unidad, vid))
                    print(f"   [OK] Paquete de unidades procesado.")
                    time.sleep(0.6)
            except:
                print(f"   [!] Error en paquete, saltando...")

    finally:
        con.close()
        print("\n--- PROCESO TERMINADO ---")
        print("Verifica de nuevo con: SELECT * FROM diccionario LIMIT 5;")

if __name__ == "__main__":
    restaurar_y_limpiar_diccionario()