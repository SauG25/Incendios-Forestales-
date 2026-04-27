# src/ingestion/Raw_Climatologia.py
"""
Copia diccionario y climatología desde BaseDeDatos_Raw.db al esquema raw de la V2.
No modifica la base original (solo lectura).
Respeta la integridad referencial: solo inserta registros de clima cuyo id_clave_inc
ya exista en raw.incendios (los que acaban de cargarse con CONAFOR).
"""
import duckdb
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config.config import V2_DB, RAW_DB  

def iniciar_migracion_climatologia():
    if not os.path.exists(RAW_DB):
        print(f"No se encuentra la base antigua en {RAW_DB}")
        return

    print(f"Conectando a la base V2: {V2_DB}")
    con_v2 = duckdb.connect(V2_DB)

    con_v2.execute(f"ATTACH '{RAW_DB}' AS old_raw (READ_ONLY)")


    con_v2.execute("""
        INSERT INTO raw.diccionario (id_variable, fuente, nombre_completo, unidad_de_medida)
        SELECT id_variable, fuente, nombre_completo, unidad_de_medida
        FROM old_raw.diccionario
        ON CONFLICT (id_variable) DO NOTHING
    """)
    var_count = con_v2.execute("SELECT COUNT(*) FROM raw.diccionario").fetchone()[0]
    print(f"   Diccionario migrado: {var_count} variables")

    con_v2.execute("""
        INSERT INTO raw.climatologia (id_registro, id_variable, id_clave_inc,
                                      fecha_de_observacion, resultado_numerico)
        SELECT c.id_registro, c.id_variable, c.id_clave_inc,
               c.fecha_de_observacion, c.resultado_numerico
        FROM old_raw.climatologia c
        WHERE c.id_clave_inc IN (SELECT id_clave_inc FROM raw.incendios)
    """)
    clima_count = con_v2.execute("SELECT COUNT(*) FROM raw.climatologia").fetchone()[0]
    print(f"   Climatología migrada: {clima_count} registros")

    con_v2.execute("DETACH old_raw")
    con_v2.close()
    print("  Migracion de climatología completada sin modificar la base original.")

if __name__ == "__main__":
    iniciar_migracion_climatologia()