import pandas as pd
import duckdb
import requests
import time
import json
import os
from datetime import timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))

DB_PATH = os.path.join(ROOT_DIR, 'data', 'BaseDeDatos.db')
JSON_PATH = os.path.join(ROOT_DIR, '01_ExtraccionDeDatos', 'DatosNASA', 'raw', 'diccionario_verificado.json')

DIAS_HISTORIA = 10 
TOTAL_VARIABLES_OBJETIVO = 143

def ejecutar_minero_series_temporales():
    # 1. Verificacion de existencia
    if not os.path.exists(DB_PATH):
        print(f"Error: No se encontro la base de datos en {DB_PATH}")
        return
    if not os.path.exists(JSON_PATH):
        print(f"Error: No se encontro el diccionario en {JSON_PATH}")
        return

    print(f"Conectando a base de datos: {DB_PATH}")
    con = duckdb.connect(DB_PATH)
    
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            diccionario = json.load(f)
        
        ids_variables = [v['id'] for v in diccionario]
        paquetes = list(range(0, len(ids_variables), 15)) 

        # 2. BUSQUEDA AMBICIOSA: Incendios que no tengan las 143 variables completas
        print("Calculando incendios con datos incompletos (esto puede tardar unos segundos)...")
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
            print("¡Felicidades! Todos los incendios tienen sus 143 variables completas.")
            return

        print(f"Se encontraron {len(pendientes)} incendios pendientes o incompletos.")
        pendientes['fecha_inicio'] = pd.to_datetime(pendientes['fecha_inicio'])

        # 3. Iteracion y Mineria
        for _, inc in pendientes.iterrows():
            id_inc = inc['id_clave_inc']
            fecha_fin = inc['fecha_inicio']
            fecha_ini = fecha_fin - timedelta(days=DIAS_HISTORIA - 1)
            
            f_start = fecha_ini.strftime('%Y%m%d')
            f_end = fecha_fin.strftime('%Y%m%d')

            print(f"\n--- Procesando incendio: {id_inc} ---")

            for i in paquetes:
                vars_en_paquete = ids_variables[i:i+15]
                bundle = ",".join(vars_en_paquete)
                
                # VERIFICACIÓN INTERNA: ¿Ya tenemos la primera variable de este paquete?
                # Si ya existe, saltamos este paquete para no duplicar ni perder tiempo
                check = con.execute("""
                    SELECT COUNT(*) FROM climatologia 
                    WHERE id_clave_inc = ? AND id_variable = ?
                """, (id_inc, vars_en_paquete[0])).fetchone()[0]

                if check > 0:
                    continue # Ya tenemos estos datos, saltar al siguiente paquete

                url = (f"https://power.larc.nasa.gov/api/temporal/daily/point?"
                       f"start={f_start}&end={f_end}&latitude={inc['latitud']}&longitude={inc['longitud']}"
                       f"&community=ag&parameters={bundle}&format=json")
                
                # --- MODO TERCO (RETRY) ---
                exito = False
                intentos = 0
                while not exito and intentos < 5:
                    try:
                        res = requests.get(url, timeout=30)
                        
                        if res.status_code == 200:
                            data = res.json()
                            parametros = data.get('properties', {}).get('parameter', {})
                            
                            for var_id, serie_temporal in parametros.items():
                                for fecha_str, valor in serie_temporal.items():
                                    val_float = float(valor)
                                    fecha_obj = f"{fecha_str[:4]}-{fecha_str[4:6]}-{fecha_str[6:]}"
                                    
                                    con.execute("""
                                        INSERT INTO climatologia (id_variable, id_clave_inc, fecha_de_observacion, resultado_numerico)
                                        VALUES (?, ?, ?, ?)
                                    """, (var_id, id_inc, fecha_obj, val_float))
                            
                            time.sleep(0.7) # Pausa técnica un poco más amplia para seguridad
                            exito = True 
                            
                        elif res.status_code == 429:
                            print(f"  NASA saturada (429). Pausa de 60s... (Intento {intentos+1}/5)")
                            time.sleep(60)
                            intentos += 1
                        else:
                            print(f" Error HTTP {res.status_code}. Reintentando... (Intento {intentos+1}/5)")
                            time.sleep(10)
                            intentos += 1
                            
                    except Exception as e:
                        print(f" Fallo de conexión: {e}. Reintentando... (Intento {intentos+1}/5)")
                        time.sleep(15)
                        intentos += 1
                
                if not exito:
                    print(f"  PAQUETE PERDIDO: {bundle[:30]}...")

    finally:
        con.close()
        print("\nSincronización finalizada. Conexión cerrada.")

if __name__ == "__main__":
    ejecutar_minero_series_temporales()