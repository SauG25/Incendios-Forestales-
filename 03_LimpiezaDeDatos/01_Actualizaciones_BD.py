import duckdb
import os
import sys

# --- CONFIGURACION DE RUTAS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

RAW_DB = os.path.join(ROOT_DIR, 'data', 'BaseDeDatos_Raw.db')
WORKING_DB = os.path.join(ROOT_DIR, 'data', 'BaseDeDatos_Working.db')
SCHEMA_SQL = os.path.join(ROOT_DIR, 'data', 'scripts', 'CorreccionCodigo.sql')

def aplicar_limpieza_datos(con):
    """
    Espacio reservado para los metodos de limpieza logica.
    Se ejecuta despues de la migracion de datos.
    """
    print("\n--- Etapa de Limpieza ---")
    print("Aviso: No se han programado metodos de limpieza aun.")
    print("La base Working mantiene los datos originales de la base Raw.")
    pass

def ejecutar_migracion_completa():
    print("\nIniciando proceso de actualizacion de la base Working...")

    if not os.path.exists(RAW_DB):
        print(f"Error: No se encuentra la base Raw en {RAW_DB}")
        return
    if not os.path.exists(SCHEMA_SQL):
        print(f"Error: No se encuentra el SQL de estructura en {SCHEMA_SQL}")
        return

    try:
        # 1. Eliminar base de trabajo anterior
        if os.path.exists(WORKING_DB):
            os.remove(WORKING_DB)
            print("Base Working anterior eliminada. Generando copia limpia...")

        con = duckdb.connect(WORKING_DB)
        print(f"Aplicando estructura desde: {os.path.basename(SCHEMA_SQL)}")
        
        # 2. Crear estructura (Tablas y Llaves)
        with open(SCHEMA_SQL, 'r') as f:
            sql_script = f.read()
            con.execute(sql_script)

        # 3. Vincular la base Raw (Solo lectura)
        con.execute(f"ATTACH '{RAW_DB}' AS source_db (READ_ONLY)")

        # 4. Transferir datos respetando el orden de dependencia (Niveles)
        orden_migracion = [
            'diccionario', 'estado', 'vegetacion', 'causa', # Nivel 1: Padres
            'municipios',                                   # Nivel 2: Depende de estado
            'incendios',                                    # Nivel 3: Depende de minicipios, causa y veg
            'danos', 'climatologia'                         # Nivel 4: Dependen de incendios y diccionario
        ]

        print("Transfiriendo datos respetando la jerarquia de relaciones...")
        for tabla in orden_migracion:
            # CORRECCION: Usar el catalog global para buscar la tabla en source_db
            query_existe = f"SELECT count(*) FROM information_schema.tables WHERE table_catalog = 'source_db' AND table_name = '{tabla}'"
            existe = con.execute(query_existe).fetchone()[0]
            
            if existe > 0:
                con.execute(f"INSERT INTO main.{tabla} SELECT * FROM source_db.{tabla}")
                num_filas = con.execute(f"SELECT count(*) FROM main.{tabla}").fetchone()[0]
                print(f"   - Entidad migrada: '{tabla}' ({num_filas} registros).")
            else:
                print(f"   - Advertencia: La tabla '{tabla}' no se encontro en la base Raw (Saltando).")

        # 5. Ejecutar la funcion de limpieza (Placeholder)
        aplicar_limpieza_datos(con)

        con.close()
        print(f"\nSincronizacion finalizada exitosamente en: {WORKING_DB}")

    except Exception as e:
        print(f"\nError critico durante el proceso: {e}")

def menu():
    print("\n" + "="*55)
    print("   SISTEMA DE ACTUALIZACION DE DATOS (REPLICACION)")
    print("="*55)
    print("1. Actualizar Limpieza (Re-procesar datos locales)")
    print("2. Actualizar Datos (Git + DVC + Re-procesar)")
    print("3. Salir")
    
    op = input("\n¿Que quieres hacer? Selecciona una opcion: ")
    
    if op == "1":
        ejecutar_migracion_completa()
    elif op == "2":
        print("\n[RECUERDA]: Antes de continuar, debes haber ejecutado:")
        print("   1. git pull origin main")
        print("   2. dvc pull")
        confirmar = input("\n¿Los comandos previos se ejecutaron con exito? (s/n): ")
        if confirmar.lower() == 's':
            ejecutar_migracion_completa()
        else:
            print("Operacion cancelada. Sincroniza los archivos primero.")
    elif op == "3":
        print("Cerrando sistema.")
        sys.exit()
    else:
        print("Opcion no valida.")

if __name__ == "__main__":
    menu()