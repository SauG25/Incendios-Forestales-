# src/ingestion/Raw_Operaciones.py
import pandas as pd
import duckdb
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config.config import V2_DB, CSV_CONAFOR

def completar_operaciones():
    if not os.path.exists(CSV_CONAFOR):
        print("Error: CSV CONAFOR no encontrado")
        return

    con = duckdb.connect(V2_DB)
    
    nulos = con.execute("SELECT COUNT(*) FROM raw.operaciones WHERE fecha_termino IS NULL").fetchone()[0]
    total = con.execute("SELECT COUNT(*) FROM raw.operaciones").fetchone()[0]
    
    if nulos == total and total > 0:
        print("Columnas de operaciones vacias. Rellenando desde CSV...")
        
        df = pd.read_csv(CSV_CONAFOR, dtype=str)
        df.columns = df.columns.str.strip()
        df['Clave del incendio'] = df['Clave del incendio'].str.strip()
        con.register('df_ops', df)
        
        con.execute("""
            UPDATE raw.operaciones
            SET
                fecha_termino = TRY_CAST(strptime(df."Fecha Termino", '%d/%m/%Y') AS DATE),
                hora_deteccion = TRY_CAST(df."Detección" AS TIME),
                hora_llegada = TRY_CAST(df."Llegada" AS TIME),
                duracion_hhmm = TRY_CAST(df."Duración" AS INTERVAL),
                duracion_dias = TRY_CAST(df."Duración días" AS INTEGER)
            FROM df_ops df
            WHERE raw.operaciones.id_clave_inc = df."Clave del incendio"
                AND raw.operaciones.fecha_termino IS NULL
        """)
        
        # Línea DETACH eliminada
        con.close()
        print("Operaciones actualizadas correctamente.")
    else:
        print("Operaciones ya contienen datos. No se requiere accion.")
        con.close()

if __name__ == "__main__":
    completar_operaciones()