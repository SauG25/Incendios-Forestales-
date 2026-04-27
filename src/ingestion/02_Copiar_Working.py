# src/ingestion/02a_Copiar_Crudo_a_Working.py
import sys
import os
import duckdb

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config.config import V2_DB

def copiar_raw_a_working():
    con = duckdb.connect(V2_DB)
    con.execute("SET memory_limit = '4GB'")
    con.execute("SET threads TO 2;")

    print("Copiando de raw a working...")
    orden = [
        'diccionario', 'estado', 'vegetacion', 'causa', 'municipios',
        'incendios', 'demografia', 'danos', 'operaciones', 'climatologia'
    ]
    for tabla in orden:
        con.execute(f"INSERT INTO working.{tabla} SELECT * FROM raw.{tabla}")
        cnt = con.execute(f"SELECT COUNT(*) FROM working.{tabla}").fetchone()[0]
        print(f"   {tabla}: {cnt} filas copiadas")

    # Recrear secuencias para que empiecen después del último ID usado
    secuencias = [
        ('working.seq_vegetacion', 'working.vegetacion', 'id_vegetacion'),
        ('working.seq_causa',      'working.causa',      'id_causa'),
        ('working.seq_registro',   'working.climatologia','id_registro')
    ]
    for seq_nombre, tabla, col_id in secuencias:
        max_id = con.execute(f"SELECT COALESCE(MAX({col_id}), 0) FROM {tabla}").fetchone()[0]
        con.execute(f"DROP SEQUENCE IF EXISTS {seq_nombre}")
        con.execute(f"CREATE SEQUENCE {seq_nombre} START WITH {max_id + 1}")
        print(f"   Secuencia {seq_nombre} reiniciada en {max_id + 1}")

    con.close()
    print("\nCopia raw -> working completada. working es ahora una réplica exacta de raw.\n")

if __name__ == "__main__":
    copiar_raw_a_working()