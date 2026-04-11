import duckdb
import os
import sys
import subprocess

# Importamos nuestras piezas de código modulares
# ¡AQUÍ AGREGAMOS LAS NUEVAS IMPORTACIONES!
from scripts.config import RAW_DB, WORKING_DB, SCHEMA_SQL, CSV_POBLACION, ARCHIVO_CONAFOR
from scripts.transform import unificar_municipios, migrar_incendios_corregidos
from scripts.enrichment import cargar_demografia, cargar_operaciones

def ejecutar_migracion_completa():
    print("\nIniciando proceso de actualizacion de la base Working...")

    if not os.path.exists(RAW_DB):
        print(f"Error: No se encuentra la base Raw en {RAW_DB}")
        return
    if not os.path.exists(SCHEMA_SQL):
        print(f"Error: No se encuentra el SQL en {SCHEMA_SQL}")
        return

    try:
        if os.path.exists(WORKING_DB):
            os.remove(WORKING_DB)
            print("Base Working anterior eliminada. Generando copia limpia...")

        con = duckdb.connect(WORKING_DB)
        
        # 1. Crear Estructura
        with open(SCHEMA_SQL, 'r') as f:
            con.execute(f.read())

        con.execute(f"ATTACH '{RAW_DB}' AS source_db (READ_ONLY)")

        print("Transfiriendo datos con unificación y blindaje en tiempo real...")
        
        # 2. Migrar Catálogos Simples (Nivel 1)
        for tabla in ['diccionario', 'estado', 'vegetacion', 'causa']:
            con.execute(f"INSERT INTO main.{tabla} SELECT * FROM source_db.{tabla}")
            filas = con.execute(f"SELECT count(*) FROM main.{tabla}").fetchone()[0]
            print(f"   - {tabla} lista ({filas} registros).")

        # 3. Transformaciones (Nivel 2 y 3)
        unificar_municipios(con)
        cargar_demografia(con, CSV_POBLACION) 
        migrar_incendios_corregidos(con)

        # ¡AQUÍ ENCIENDES TUS OPERACIONES!
        cargar_operaciones(con, ARCHIVO_CONAFOR)

        # 4. Migrar Tablas Hijas Pesadas (Nivel 4)
        for tabla in ['danos', 'climatologia']:
            con.execute(f"INSERT INTO main.{tabla} SELECT * FROM source_db.{tabla}")
            filas = con.execute(f"SELECT count(*) FROM main.{tabla}").fetchone()[0]
            print(f"   - {tabla} lista ({filas} registros).")

        con.close()
        print(f"\nSincronizacion exitosa en: {WORKING_DB}")

    except Exception as e:
        print(f"\nError critico durante el proceso: {e}")

def actualizar_desde_repositorio():
    print("\n--- Ejecutando Sincronización Automática (Git + DVC) ---")
    try:
        # ROOT_DIR para Git/DVC es el directorio base del proyecto
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        print("1. Descargando cambios de código (git pull origin main)...")
        subprocess.run(["git", "pull", "origin", "main"], cwd=base_dir, check=True)
        
        print("\n2. Descargando última versión de los datos (dvc pull)...")
        subprocess.run(["dvc", "pull"], cwd=base_dir, check=True)
        
        print("\n¡Descarga completada! Procediendo a generar la base Working...")
        ejecutar_migracion_completa()
        
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Falló la sincronización con el servidor.")
        print(f"Detalle del error: {e}")

def menu():
    print("\n" + "="*55)
    print("   SISTEMA DE ACTUALIZACION DE DATOS (REPLICACION)")
    print("="*55)
    print("1. Actualizar Limpieza (Re-procesar datos locales)")
    print("2. Sincronizar y Re-procesar (Automatizado Git+DVC)")
    print("3. Salir")
    
    op = input("\n¿Que quieres hacer? Selecciona una opcion: ")
    
    if op == "1":
        ejecutar_migracion_completa()
    elif op == "2":
        actualizar_desde_repositorio()
    elif op == "3":
        print("Cerrando sistema.")
        sys.exit()
    else:
        print("Opcion no valida.")

if __name__ == "__main__":
    menu()