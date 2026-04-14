import duckdb
import os
import sys
import subprocess

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

def ejecutar_migracion_completa():
    print("\nIniciando migracion jerarquica con limpieza agresiva en origen...")

    if not os.path.exists(RAW_DB) or not os.path.exists(SCHEMA_SQL):
        print("[Error] Archivos base no encontrados.")
        return

    try:
        if os.path.exists(WORKING_DB):
            os.remove(WORKING_DB)
            print("Base Working reiniciada.")

        con = duckdb.connect(WORKING_DB)
        
        # --- PASO 0: CREACION DE ESTRUCTURA ---
        with open(SCHEMA_SQL, 'r') as f:
            con.execute(f.read())
        con.execute(f"ATTACH '{RAW_DB}' AS source_db (READ_ONLY)")

        # --- NIVEL 1: ENTIDADES PADRE ---
        print("\nNivel 1: Migrando diccionarios con eliminacion de caracteres invisibles...")
        # Usamos doble diagonal invertida para evitar el SyntaxWarning de Python
        con.execute("""
            INSERT INTO main.diccionario 
            SELECT regexp_replace(id_variable, '[\\s\\t\\n\\r]', '', 'g'), fuente, nombre_completo, unidad_de_medida 
            FROM source_db.diccionario
        """)
        
        for tabla in ['estado', 'vegetacion', 'causa']:
            con.execute(f"INSERT INTO main.{tabla} SELECT * FROM source_db.{tabla}")

        # --- NIVEL 2 Y 3: GEOGRAFIA E INCENDIOS ---
        print("\nNivel 2 y 3: Migrando municipios e incendios...")
        unificar_municipios(con)
        migrar_incendios_corregidos(con)
        cargar_demografia(con, CSV_POBLACION)

        # --- FASE A: LIMPIEZA DE PADRES ---
        print("\nFASE A: Sincronizando catalogos maestros...")
        con.execute("BEGIN TRANSACTION")
        corregir_geografia_invertida(con)
        deduplicar_sistemico(con)
        con.execute("COMMIT")

        # --- NIVEL 4: ENTIDADES HIJAS ---
        print("\nNivel 4: Migrando datos dependientes con limpieza de llaves foraneas...")
        # Limpieza con doble diagonal invertida en id_variable e id_clave_inc
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
        
        con.execute("""
            INSERT INTO main.danos (id_clave_inc, hojarasca, arbustivo, herbaceo, arbolado_adulto, renuevo, tamanio)
            SELECT regexp_replace(id_clave_inc, '[\\s\\t\\n\\r]', '', 'g'), hojarasca, arbustivo, herbaceo, arbolado_adulto, renuevo, tamanio
            FROM source_db.danos 
            WHERE regexp_replace(id_clave_inc, '[\\s\\t\\n\\r]', '', 'g') IN (SELECT id_clave_inc FROM main.incendios)
        """)
        
        cargar_operaciones(con, ARCHIVO_CONAFOR)

        # --- FASE B: LIMPIEZA FINAL ---
        print("\nFASE B: Procesamiento final y limpieza de variables NASA...")
        con.execute("BEGIN TRANSACTION")
        estandarizar_y_limpiar_texto(con)
        neutralizar_inconsistencias(con)
        procesar_climatologia(con)
        limpiar_huerfanos(con)
        con.execute("COMMIT")

        con.execute("DETACH source_db") 
        con.close()
        print("\nSincronizacion exitosa.")

    except Exception as e:
        try: con.execute("ROLLBACK")
        except: pass
        print(f"\nError en el Pipeline: {e}")

def actualizar_desde_repositorio():
    print("\n--- Ejecutando Sincronizacion Automatica (Git + DVC) ---")
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        subprocess.run(["git", "pull", "origin", "main"], cwd=base_dir, check=True)
        subprocess.run(["dvc", "pull", "-f"], cwd=base_dir, check=True)
        ejecutar_migracion_completa()
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Fallo la sincronizacion.")

def menu():
    print("\n" + "="*55)
    print("   SISTEMA DE ACTUALIZACION Y LIMPIEZA (EDOMEX/TLAXCALA)")
    print("="*55)
    print("1. Re-procesar y Limpiar datos locales")
    print("2. Sincronizar (Git+DVC) y Limpiar")
    print("3. Salir")
    op = input("\nQue quieres hacer? ")
    if op == "1": ejecutar_migracion_completa()
    elif op == "2": actualizar_desde_repositorio()
    elif op == "3": sys.exit()
    else: print("Opcion no valida.")

if __name__ == "__main__":
    menu()