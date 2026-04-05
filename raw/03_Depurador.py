import json
import requests
import time
import os

# Rutas universales
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
JSON_PATH = os.path.join(ROOT_DIR, '01_ExtraccionDeDatos', 'DatosNASA', 'raw', 'diccionario_limpio.json')
OUT_PATH = os.path.join(ROOT_DIR, '01_ExtraccionDeDatos', 'DatosNASA', 'raw', 'diccionario_verificado.json')

def depurar_diccionario():
    with open(JSON_PATH, 'r') as f:
        diccionario = json.load(f)
    
    print(f"Iniciando depuracion de {len(diccionario)} variables...")
    variables_validas = []
    
    # Probaremos con una coordenada y fecha estandar (Edomex)
    test_lat, test_lon = 19.858, -99.251
    test_date = "20150128"

    for i, var in enumerate(diccionario):
        var_id = var['id']
        url = (f"https://power.larc.nasa.gov/api/temporal/daily/point?"
               f"start={test_date}&end={test_date}&latitude={test_lat}&longitude={test_lon}"
               f"&community=ag&parameters={var_id}&format=json")
        
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                print(f"[{i+1}/{len(diccionario)}] ✅ {var_id} es VALIDA")
                variables_validas.append(var)
            else:
                print(f"[{i+1}/{len(diccionario)}] ❌ {var_id} RECHAZADA (Error {res.status_code})")
        except:
            print(f"[{i+1}/{len(diccionario)}] ⚠️ {var_id} ERROR DE CONEXION")
        
        # Pausa minima para no saturar la API en la depuracion
        time.sleep(0.2)

    # Guardar el nuevo diccionario "limpio de verdad"
    with open(OUT_PATH, 'w') as f:
        json.dump(variables_validas, f, indent=4)
    
    print(f"\nDepuracion finalizada. Variables funcionales: {len(variables_validas)}")
    print(f"Nuevo diccionario guardado en: {OUT_PATH}")

if __name__ == "__main__":
    depurar_diccionario()