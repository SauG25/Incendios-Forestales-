import duckdb
import os
import sys
import subprocess

# 1. Importaciones actualizadas con los nombres correctos de tus nuevas funciones
from scripts.config import RAW_DB, WORKING_DB, SCHEMA_SQL, CSV_POBLACION, ARCHIVO_CONAFOR
from scripts.transform import (
    unificar_municipios, 
    migrar_incendios_corregidos, 
    eliminar_duplicados_fisicos,
    estandarizar_categoricos,
    neutralizar_inconsistencias,
    ejecutar_limpieza_texto
)
from scripts.enrichment import cargar_demografia, cargar_operaciones

def ejecutar_migracion_completa():
    print("\nIniciando proceso de actualizacion y limpieza profunda...")

    if not os.path.exists(RAW_DB):
        print(f"[Error] No se encuentra la base Raw en {RAW_DB}")
        return
    if not os.path.exists(SCHEMA_SQL):
        print(f"[Error] No se encuentra el SQL en {SCHEMA_SQL}")
        return

    try:
        if os.path.exists(WORKING_DB):
            os.remove(WORKING_DB)
            print("Base Working anterior eliminada. Generando copia limpia...")

        con = duckdb.connect(WORKING_DB)
        
        # --- PASO 1: ESTRUCTURA Y CONEXION ---
        with open(SCHEMA_SQL, 'r') as f:
            con.execute(f.read())
        con.execute(f"ATTACH '{RAW_DB}' AS source_db (READ_ONLY)")

        # --- PASO 2: MIGRACION INICIAL (CATALOGOS) ---
        print("\nMigrando catalogos iniciales...")
        for tabla in ['diccionario', 'estado', 'vegetacion', 'causa']:
            con.execute(f"INSERT INTO main.{tabla} SELECT * FROM source_db.{tabla}")
            print(f"   - {tabla} migrada.")

        # --- PASO 3: TRANSFORMACIONES GEOGRAFICAS Y DEPURACION (EDOMEX) ---
        print("\nProcesando geografia del Estado de Mexico y depurando IDs...")
        unificar_municipios(con)
        migrar_incendios_corregidos(con)
        # Eliminamos duplicados inmediatamente despues de cargar la tabla principal
        eliminar_duplicados_fisicos(con)

        # --- PASO 4: MIGRACION DE TABLAS PESADAS ---
        print("\nMigrando datos masivos (Danos y Climatologia)...")
        for tabla in ['danos', 'climatologia']:
            con.execute(f"INSERT INTO main.{tabla} SELECT * FROM source_db.{tabla}")
            print(f"   - {tabla} migrada.")

        # --- PASO 5: LIMPIEZA DE CALIDAD (EDA PREP) ---
        print("\nEjecutando algoritmos de limpieza y estandarizacion logica...")
        estandarizar_categoricos(con)
        neutralizar_inconsistencias(con)
        ejecutar_limpieza_texto(con)

        # --- PASO 6: ENRIQUECIMIENTO (CSV EXTERNOS) ---
        print("\nEnriqueciendo base con datos externos...")
        cargar_demografia(con, CSV_POBLACION) 
        cargar_operaciones(con, ARCHIVO_CONAFOR)

        # --- PASO 7: CIERRE Y LIMPIEZA DE VISTA ---
        con.execute("DETACH source_db") 
        con.close()
        
        print(f"\nSincronizacion y limpieza exitosa.")
        print(f"Ubicacion: {WORKING_DB}")

    except Exception as e:
        print(f"\nError critico durante el proceso: {e}")

def actualizar_desde_repositorio():
    print("\n--- Ejecutando Sincronizacion Automatica (Git + DVC) ---")
    try:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        print("1. Descargando cambios de codigo (git pull origin main)...")
        subprocess.run(["git", "pull", "origin", "main"], cwd=base_dir, check=True)
        
        print("\n2. Descargando ultima version de los datos (dvc pull --force)...")
        subprocess.run(["dvc", "pull", "-f"], cwd=base_dir, check=True)
        
        print("\nDescarga completada. Procediendo a generar la base Working...")
        ejecutar_migracion_completa()
        
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Fallo la sincronizacion con el servidor.")
        print(f"Detalle del error: {e}")

def menu():
    print("\n" + "="*55)
    print("   SISTEMA DE ACTUALIZACION Y LIMPIEZA (EDOMEX)")
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