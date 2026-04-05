import pandas as pd
import duckdb
import requests
import time
import json
import os
from datetime import timedelta

# --- CONFIGURACION DE RUTAS BLINDADAS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))

DB_PATH = os.path.join(ROOT_DIR, 'data', 'BaseDeDatos.db')
JSON_PATH = os.path.join(ROOT_DIR, '01_ExtraccionDeDatos', 'DatosNASA', 'raw', 'diccionario_verificado.json')

# Ventana de tiempo: 10 dias en total (Dia del incendio + 9 anteriores)
DIAS_HISTORIA = 10 

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

        # 2. Buscar incendios sin registros de clima
        pendientes = con.execute("""
            SELECT i.id_clave_inc, i.latitud, i.longitud, i.fecha_inicio 
            FROM incendios i
            LEFT JOIN climatologia c ON i.id_clave_inc = c.id_clave_inc
            WHERE c.id_clave_inc IS NULL
            LIMIT 5
        """).df()

        if pendientes.empty:
            print("Todo al dia. No hay incendios pendientes de procesar.")
            return

        pendientes['fecha_inicio'] = pd.to_datetime(pendientes['fecha_inicio'])

        # 3. Iteracion y Mineria (Sin limpieza)
        for _, inc in pendientes.iterrows():
            id_inc = inc['id_clave_inc']
            fecha_fin = inc['fecha_inicio']
            fecha_ini = fecha_fin - timedelta(days=DIAS_HISTORIA - 1)
            
            f_start = fecha_ini.strftime('%Y%m%d')
            f_end = fecha_fin.strftime('%Y%m%d')

            print(f"\nExtrayendo serie temporal para incendio: {id_inc}")
            print(f"Rango: {f_start} al {f_end} ({DIAS_HISTORIA} dias)")

            for i in paquetes:
                bundle = ",".join(ids_variables[i:i+15])
                url = (f"https://power.larc.nasa.gov/api/temporal/daily/point?"
                       f"start={f_start}&end={f_end}&latitude={inc['latitud']}&longitude={inc['longitud']}"
                       f"&community=ag&parameters={bundle}&format=json")
                
                try:
                    res = requests.get(url, timeout=30)
                    if res.status_code == 200:
                        data = res.json()
                        parametros = data.get('properties', {}).get('parameter', {})
                        
                        for var_id, serie_temporal in parametros.items():
                            for fecha_str, valor in serie_temporal.items():
                                val_float = float(valor)
                                
                                # Convertir '20150119' a formato DATE '2015-01-19'
                                fecha_obj = f"{fecha_str[:4]}-{fecha_str[4:6]}-{fecha_str[6:]}"
                                
                                # INSERCION DIRECTA (Se admite el -999.0)
                                con.execute("""
                                    INSERT INTO climatologia (id_variable, id_clave_inc, fecha_de_observacion, resultado_numerico)
                                    VALUES (?, ?, ?, ?)
                                """, (var_id, id_inc, fecha_obj, val_float))
                    
                    # Pausa tecnica
                    time.sleep(0.6) 

                except Exception as e:
                    print(f"Error procesando paquete {bundle[:20]}... : {e}")

    finally:
        # Cierre garantizado
        con.close()
        print("\nSincronizacion de series temporales completada. Conexion cerrada.")

if __name__ == "__main__":
    ejecutar_minero_series_temporales()