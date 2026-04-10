import pandas as pd
import duckdb
import requests
import time
import json
import os
from datetime import timedelta

# --- CONFIGURACIÓN DE RUTAS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))

DB_PATH = os.path.join(ROOT_DIR, 'data', 'BaseDeDatos_Raw.db')
JSON_PATH = os.path.join(ROOT_DIR, '01_ExtraccionDeDatos', 'DatosNASA', 'raw', 'diccionario_verificado.json')

DIAS_HISTORIA = 10 
TOTAL_VARIABLES_OBJETIVO = 143 # 140 NASA + 3 GEE

def ejecutar_minero_series_temporales():
    if not os.path.exists(DB_PATH) or not os.path.exists(JSON_PATH):
        print(f"Error: Verifica las rutas de la DB ({DB_PATH}) o el Diccionario.")
        return

    print(f"Conectando a base de datos: {DB_PATH}")
    con = duckdb.connect(DB_PATH)
    
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            diccionario = json.load(f)
        
        ids_variables = [v['id'] for v in diccionario]
        # Agrupamos de 15 en 15 para no saturar la URL de la NASA
        paquetes = [ids_variables[i:i + 15] for i in range(0, len(ids_variables), 15)]

        # 1. BÚSQUEDA DE INCENDIOS INCOMPLETOS
        print("Buscando incendios que no llegan a las 143 variables...")
        pendientes = con.execute(f"""
            SELECT i.id_clave_inc, i.latitud, i.longitud, i.fecha_inicio 
            FROM incendios i
            WHERE i.id_clave_inc NOT IN (
                SELECT id_clave_inc 
                FROM climatologia 
                GROUP BY id_clave_inc 
                HAVING COUNT(DISTINCT id_variable) >= {TOTAL_VARIABLES_OBJETIVO}
            )
            ORDER BY i.fecha_inicio ASC
        """).df()

        if pendientes.empty:
            print("¡Felicidades! Todos los incendios están completos.")
            return

        print(f"Procesando {len(pendientes)} incendios pendientes.")
        pendientes['fecha_inicio'] = pd.to_datetime(pendientes['fecha_inicio'])

        # 2. PROCESAMIENTO
        for _, inc in pendientes.iterrows():
            id_inc = inc['id_clave_inc']
            fecha_fin = inc['fecha_inicio']
            fecha_ini = fecha_fin - timedelta(days=DIAS_HISTORIA - 1)
            
            f_start = fecha_ini.strftime('%Y%m%d')
            f_end = fecha_fin.strftime('%Y%m%d')

            print(f"\n--- Trabajando en incendio: {id_inc} ---")

            for vars_en_paquete in paquetes:
                bundle = ",".join(vars_en_paquete)
                
                # --- VERIFICACIÓN DE HUECOS ---
                # Contamos cuántas de estas 15 variables ya tenemos registradas
                marcador = con.execute(f"""
                    SELECT COUNT(DISTINCT id_variable) FROM climatologia 
                    WHERE id_clave_inc = ? AND id_variable IN ({','.join(['?']*len(vars_en_paquete))})
                """, (id_inc, *vars_en_paquete)).fetchone()[0]

                if marcador == len(vars_en_paquete):
                    continue # Paquete completo, saltar al siguiente

                url = (f"https://power.larc.nasa.gov/api/temporal/daily/point?"
                       f"start={f_start}&end={f_end}&latitude={inc['latitud']}&longitude={inc['longitud']}"
                       f"&community=ag&parameters={bundle}&format=json")
                
                exito = False
                intentos = 0
                while not exito and intentos < 5:
                    try:
                        res = requests.get(url, timeout=30)
                        
                        if res.status_code == 200:
                            data = res.json()
                            parametros = data.get('properties', {}).get('parameter', {})
                            
                            # --- EL ESCUDO ANTI-DUPLICADOS ---
                            # Borramos solo las variables de este paquete antes de insertar
                            con.execute(f"""
                                DELETE FROM climatologia 
                                WHERE id_clave_inc = ? AND id_variable IN ({','.join(['?']*len(vars_en_paquete))})
                            """, (id_inc, *vars_en_paquete))
                            
                            for var_id, serie_temporal in parametros.items():
                                for fecha_str, valor in serie_temporal.items():
                                    # Convertimos '20250101' -> '2025-01-01'
                                    fecha_sql = f"{fecha_str[:4]}-{fecha_str[4:6]}-{fecha_str[6:]}"
                                    
                                    con.execute("""
                                        INSERT INTO climatologia (id_variable, id_clave_inc, fecha_de_observacion, resultado_numerico)
                                        VALUES (?, ?, ?, ?)
                                    """, (var_id, id_inc, fecha_sql, float(valor)))
                            
                            print(f"    [OK] Paquete de {len(vars_en_paquete)} variables sincronizado.")
                            time.sleep(0.8) 
                            exito = True 
                            
                        elif res.status_code == 429:
                            print(f"  NASA saturada (429). Esperando 60s... (Intento {intentos+1}/5)")
                            time.sleep(60)
                            intentos += 1
                        else:
                            print(f"  Error HTTP {res.status_code}. Reintentando...")
                            time.sleep(10); intentos += 1
                            
                    except Exception as e:
                        print(f"  Fallo: {str(e)[:50]}. Reintentando...")
                        time.sleep(15); intentos += 1
                
                if not exito:
                    print(f"  [ALERTA] No se pudo recuperar el paquete: {bundle[:30]}...")

    finally:
        con.close()
        print("\nProceso terminado. Conexión cerrada con seguridad.")

if __name__ == "__main__":
    ejecutar_minero_series_temporales()