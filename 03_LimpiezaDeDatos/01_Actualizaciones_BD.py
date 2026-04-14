import duckdb
import os
import sys
import subprocess
import pandas as pd

from scripts.config import RAW_DB, WORKING_DB, SCHEMA_SQL, CSV_POBLACION, ARCHIVO_CONAFOR
from scripts.transform import (
    unificar_municipios, 
    migrar_incendios_corregidos, 
    corregir_geografia_invertida, 
    deduplicar_sistemico,
    estandarizar_y_limpiar_texto,
    neutralizar_inconsistencias,
    procesar_climatologia,
    limpiar_huerfanos
)
from scripts.enrichment import cargar_demografia, cargar_operaciones

def obtener_conteo(con, tabla):
    """Helper para contar registros rápidamente"""
    return con.execute(f"SELECT COUNT(*) FROM main.{tabla}").fetchone()[0]

def ejecutar_migracion_completa():
    print("\n" + "="*55)
    print("   INICIANDO MIGRACIÓN Y LIMPIEZA DE DATOS")
    print("="*55)

    if not os.path.exists(RAW_DB) or not os.path.exists(SCHEMA_SQL):
        print(f"[Error] No se encontró la DB Raw en: {RAW_DB}")
        return

    try:
        if os.path.exists(WORKING_DB):
            os.remove(WORKING_DB)
            print(">>> Base Working reiniciada (Disco limpio).")

        con = duckdb.connect(WORKING_DB)
        
        # --- PASO 0: ESTRUCTURA ---
        with open(SCHEMA_SQL, 'r') as f:
            con.execute(f.read())
        con.execute(f"ATTACH '{RAW_DB}' AS source_db (READ_ONLY)")

        # --- NIVEL 1: DICCIONARIOS ---
        print("\n[1/4] Migrando Catálogos Maestros...")
        con.execute("""
            INSERT INTO main.diccionario 
            SELECT regexp_replace(id_variable, '[\\s\\t\\n\\r]', '', 'g'), fuente, nombre_completo, unidad_de_medida 
            FROM source_db.diccionario
        """)
        
        for tabla in ['estado', 'vegetacion', 'causa']:
            con.execute(f"INSERT INTO main.{tabla} SELECT * FROM source_db.{tabla}")
        
        print(f"    -> Diccionario: {obtener_conteo(con, 'diccionario')} variables.")
        print(f"    -> Estados/Veg/Causas: Sincronizados.")

        # --- NIVEL 2 Y 3: GEOGRAFIA E INCENDIOS ---
        print("\n[2/4] Migrando Geografía e Incendios...")
        unificar_municipios(con)
        migrar_incendios_corregidos(con)
        
        cant_incendios = obtener_conteo(con, 'incendios')
        print(f"    -> Total Incendios traídos: {cant_incendios:,}")

        # --- FASE A: LIMPIEZA INTERMEDIA ---
        con.execute("BEGIN TRANSACTION")
        corregir_geografia_invertida(con)
        deduplicar_sistemico(con)
        con.execute("COMMIT")

        # --- NIVEL 4: CLIMATOLOGÍA (EL PESO PESADO) ---
        print("\n[3/4] Migrando Climatología (Series Temporales)...")
        # Aquí es donde veremos si el DVC trajo los datos de 2024/2025
        con.execute("""
            INSERT INTO main.climatologia (id_registro, id_variable, id_clave_inc, fecha_de_observacion, resultado_numerico)
            SELECT 
                id_registro, 
                regexp_replace(id_variable, '[\\s\\t\\n\\r]', '', 'g'), 
                regexp_replace(id_clave_inc, '[\\s\\t\\n\\r]', '', 'g'), 
                fecha_de_observacion, 
                resultado_numerico 
            FROM source_db.climatologia
            WHERE regexp_replace(id_clave_inc, '[\\s\\t\\n\\r]', '', 'g') IN (SELECT id_clave_inc FROM main.incendios)
        """)
        
        cant_clima = obtener_conteo(con, 'climatologia')
        print(f"    -> Total Registros de Clima: {cant_clima:,}")

        # --- DAÑOS Y OPERACIONES ---
        con.execute("""
            INSERT INTO main.danos (id_clave_inc, hojarasca, arbustivo, herbaceo, arbolado_adulto, renuevo, tamanio)
            SELECT regexp_replace(id_clave_inc, '[\\s\\t\\n\\r]', '', 'g'), hojarasca, arbustivo, herbaceo, arbolado_adulto, renuevo, tamanio
            FROM source_db.danos 
            WHERE regexp_replace(id_clave_inc, '[\\s\\t\\n\\r]', '', 'g') IN (SELECT id_clave_inc FROM main.incendios)
        """)
        
        cargar_demografia(con, CSV_POBLACION)
        cargar_operaciones(con, ARCHIVO_CONAFOR)

        # --- FASE B: LIMPIEZA FINAL ---
        print("\n[4/4] Ejecutando Limpieza Agresiva y Estandarización...")
        con.execute("BEGIN TRANSACTION")
        estandarizar_y_limpiar_texto(con)
        neutralizar_inconsistencias(con)
        procesar_climatologia(con)
        limpiar_huerfanos(con)
        con.execute("COMMIT")

        # --- REPORTE DE SALUD POR AÑO ---
        print("\n" + "-"*30)
        print(" RESUMEN DE DATOS POR AÑO (WORKING)")
        print("-"*30)
        resumen = con.execute("""
            SELECT anio, COUNT(DISTINCT i.id_clave_inc) as total_inc, COUNT(c.id_registro) as filas_clima
            FROM main.incendios i
            LEFT JOIN main.climatologia c ON i.id_clave_inc = c.id_clave_inc
            GROUP BY anio ORDER BY anio
        """).df()
        print(resumen.to_string(index=False))

        con.execute("DETACH source_db") 
        con.close()
        print("\n>>> Pipeline finalizado con éxito.")

    except Exception as e:
        print(f"\n[ERROR CRÍTICO]: {e}")

def actualizar_desde_repositorio():
    print("\n" + "="*55)
    print("   SINCRONIZANDO CON REPOSITORIO (GIT + DVC)")
    print("="*55)
    try:
        # Ir a la raíz del proyecto para los comandos de git/dvc
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        print("1. Pull de Git...")
        subprocess.run(["git", "pull", "origin", "main"], cwd=base_dir, check=True)
        
        print("2. Pull de DVC (trayendo bases de datos pesadas)...")
        subprocess.run(["dvc", "pull", "-f"], cwd=base_dir, check=True)
        
        print("\nSincronización de archivos completa. Iniciando migración...")
        ejecutar_migracion_completa()
        
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Falló la conexión con el servidor o DVC.")

def menu():
    print("\nSISTEMA DE GESTIÓN DE DATOS - TLAXCALA/EDOMEX")
    print("1. Re-procesar Working (Local)")
    print("2. Sincronizar Nube (Git+DVC) + Re-procesar")
    print("3. Salir")
    op = input("\nSelecciona una opción: ")
    if op == "1": ejecutar_migracion_completa()
    elif op == "2": actualizar_desde_repositorio()
    elif op == "3": sys.exit()
    else: print("Opción no válida.")

if __name__ == "__main__":
    menu()