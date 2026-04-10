import ee
import pandas as pd
import duckdb
import os
import time
from datetime import timedelta

# ==========================================
# 1. CONFIGURACIÓN DE RUTAS
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
DB_PATH = os.path.join(ROOT_DIR, 'data', 'BaseDeDatos_Raw.db')

MI_PROYECTO = 'forward-aura-491020-a0' # Tu proyecto de Google Cloud

def ejecutar_minero_vegetacion():
    # 2. VERIFICACIÓN Y AUTENTICACIÓN
    if not os.path.exists(DB_PATH):
        print(f"Error: No se encontró la base de datos en {DB_PATH}")
        return

    try:
        ee.Initialize(project=MI_PROYECTO)
        print(f"Conexión exitosa a Google Earth Engine (Proyecto: {MI_PROYECTO})")
    except Exception as e:
        print("Requiere autenticación...")
        ee.Authenticate()
        ee.Initialize(project=MI_PROYECTO)

    print(f"Conectando a base de datos: {DB_PATH}")
    con = duckdb.connect(DB_PATH)
    
    try:
        # 3. BÚSQUEDA AMBICIOSA: Incendios sin las 3 variables completas
        print("Calculando incendios sin datos completos de vegetación...")
        pendientes = con.execute("""
            SELECT i.id_clave_inc, i.latitud, i.longitud, i.fecha_inicio 
            FROM incendios i
            WHERE i.id_clave_inc NOT IN (
                SELECT id_clave_inc 
                FROM climatologia 
                WHERE id_variable IN ('NDVI', 'NDWI', 'NDMI')
                GROUP BY id_clave_inc 
                HAVING COUNT(DISTINCT id_variable) = 3
            )
            ORDER BY i.fecha_inicio ASC
        """).df()

        if pendientes.empty:
            print("¡Felicidades! Todos los incendios tienen sus índices de vegetación completos.")
            return

        print(f"Se encontraron {len(pendientes)} incendios pendientes de vegetación.")
        pendientes['fecha_inicio'] = pd.to_datetime(pendientes['fecha_inicio'])

        # 4. ITERACIÓN Y MINERÍA (GEE)
        for _, inc in pendientes.iterrows():
            id_inc = inc['id_clave_inc']
            lat, lon = inc['latitud'], inc['longitud']
            fecha_fin = inc['fecha_inicio']
            
            fecha_ini = fecha_fin - timedelta(days=30)
            f_start = fecha_ini.strftime('%Y-%m-%d')
            f_end = fecha_fin.strftime('%Y-%m-%d')

            print(f"\n--- Procesando vegetación para incendio: {id_inc} ---")

            exito = False
            intentos = 0
            
            while not exito and intentos < 5:
                try:
                    punto = ee.Geometry.Point([lon, lat])
                    coleccion = (ee.ImageCollection("MODIS/061/MOD09GA")
                                 .filterBounds(punto)
                                 .filterDate(f_start, f_end))
                    
                    # 4.1 Enseñar a Google a calcular índices para toda la historia
                    def calcular_indices(img):
                        ndvi = img.normalizedDifference(['sur_refl_b02', 'sur_refl_b01']).rename('NDVI')
                        ndwi = img.normalizedDifference(['sur_refl_b02', 'sur_refl_b06']).rename('NDWI')
                        ndmi = img.normalizedDifference(['sur_refl_b02', 'sur_refl_b07']).rename('NDMI')
                        return img.addBands([ndvi, ndwi, ndmi])
                        
                    col_indices = coleccion.map(calcular_indices).select(['NDVI', 'NDWI', 'NDMI'])
                    
                    # 4.2 Descargar la serie de tiempo completa de los 30 días
                    serie_tiempo = col_indices.getRegion(punto, 500).getInfo()
                    
                    if len(serie_tiempo) <= 1: # Solo trae el encabezado
                         print(f"  [AVISO] No hay cobertura satelital para estas fechas.")
                         exito = True 
                         continue

                    # 4.3 Limpiar y buscar el día más reciente sin nubes
                    header = serie_tiempo[0]
                    datos = serie_tiempo[1:]
                    
                    # Ordenar por fecha de más reciente a más viejo
                    idx_time = header.index('time')
                    datos.sort(key=lambda x: x[idx_time], reverse=True)
                    
                    mejor_dato = None
                    for fila in datos:
                        dicc = dict(zip(header, fila))
                        # Si encontramos un día donde el NDVI no sea None (es decir, está despejado)
                        if dicc['NDVI'] is not None:
                            mejor_dato = dicc
                            break
                            
                    # Si revisó los 30 días y todos tenían nubes
                    if mejor_dato is None:
                        print(f"  [AVISO] Los 30 días previos estuvieron completamente nublados. Saltando...")
                        exito = True
                        continue

                    # 4.4 Inserción en Base de Datos
                    # Convertir el tiempo de Google (milisegundos) a fecha normal
                    fecha_satelite_str = pd.to_datetime(mejor_dato['time'], unit='ms').strftime('%Y-%m-%d')

                    # --- EL ESCUDO ANTI-DUPLICADOS ---
                    # Borramos cualquier registro previo de vegetación de este incendio para evitar duplicados y conflictos
                    con.execute("""
                        DELETE FROM climatologia 
                        WHERE id_clave_inc = ? AND id_variable IN ('NDVI', 'NDWI', 'NDMI')
                    """, (id_inc,))

                    for var_id in ['NDVI', 'NDWI', 'NDMI']:
                        con.execute("""
                            INSERT INTO climatologia (id_variable, id_clave_inc, fecha_de_observacion, resultado_numerico)
                            VALUES (?, ?, ?, ?)
                        """, (var_id, id_inc, fecha_satelite_str, float(mejor_dato[var_id])))
                    
                    dias_desfase = (fecha_fin - pd.to_datetime(fecha_satelite_str)).days
                    print(f"  [ÉXITO] NDVI: {mejor_dato['NDVI']:.3f} | NDWI: {mejor_dato['NDWI']:.3f} | NDMI: {mejor_dato['NDMI']:.3f} | Desfase: {dias_desfase} días")
                    time.sleep(0.5) 
                    exito = True
                    
                except Exception as e:
                    print(f"  [ERROR] Falló la petición a GEE. Reintentando... (Intento {intentos+1}/5) - Detalle: {str(e)[:50]}")
                    time.sleep(5)
                    intentos += 1
            
            if not exito:
                print(f"  [ABORTADO] No se pudo procesar la vegetación para {id_inc} después de 5 intentos.")

    finally:
        con.close()
        print("\nSincronización de vegetación finalizada. Conexión cerrada.")

if __name__ == "__main__":
    ejecutar_minero_vegetacion()