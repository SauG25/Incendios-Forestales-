# src/ingestion/01_Raw_Insercion.py
import sys
import os
import duckdb

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from config.config import V2_DB
from src.ingestion.Raw_Conafor import iniciar_ingesta_conafor
from src.ingestion.Raw_Operaciones import completar_operaciones
from src.ingestion.Raw_Climatologia import iniciar_migracion_climatologia
from src.ingestion.Raw_Demografia import iniciar_ingesta_demografia

def obtener_conteos(con):
    tablas = ['diccionario', 'estado', 'vegetacion', 'causa', 'municipios',
              'incendios', 'demografia', 'danos', 'operaciones', 'climatologia']
    conteos = {}
    for t in tablas:
        try:
            cnt = con.execute(f"SELECT COUNT(*) FROM raw.{t}").fetchone()[0]
            conteos[t] = cnt
        except Exception:
            conteos[t] = 'ERROR'
    return conteos

def main():
    if not os.path.exists(V2_DB):
        print(f"Error: Base V2 no encontrada en {V2_DB}")
        return

    con = duckdb.connect(V2_DB)
    print("Inicio de ingesta raw\n")

    # Paso 1: CONAFOR – Siempre se ejecuta, ON CONFLICT evita duplicados
    print("Paso 1/5: CONAFOR")
    iniciar_ingesta_conafor()

    # Paso 2: Operaciones – Solo actualiza si hay nulos
    print("\nPaso 2/5: Completar Operaciones")
    completar_operaciones()

    # Paso 3: Climatología – Solo se ejecuta si está vacía (evita reintentar 18M)
    print("\nPaso 3/5: Climatologia")
    count_clima = con.execute("SELECT COUNT(*) FROM raw.climatologia").fetchone()[0]
    if count_clima == 0:
        iniciar_migracion_climatologia()
    else:
        print("Climatologia ya presente. Sin datos nuevos.")

    # Paso 4: Demografía – Siempre se ejecuta (ON CONFLICT DO NOTHING protege)
    print("\nPaso 4/5: Demografia")
    iniciar_ingesta_demografia()

    # Paso 5: Conteos finales
    print("\nPaso 5/5: Conteos finales")
    conteos = obtener_conteos(con)
    con.close()

    for tabla, cantidad in conteos.items():
        print(f"raw.{tabla}: {cantidad}")
    print("\nIngesta raw finalizada.")

if __name__ == "__main__":
    main()