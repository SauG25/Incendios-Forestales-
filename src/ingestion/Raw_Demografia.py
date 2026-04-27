# src/ingestion/Raw_Demografia.py
"""
Carga de datos demográficos crudos en el esquema `raw`.
- Inserta los municipios que falten en raw.municipios usando el nombre real del catálogo.
- Inserta los registros con todas las columnas, dejando NULL los campos que no vengan.
"""

import pandas as pd
import duckdb
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config.config import V2_DB, CSV_DEMOGRAFIA, CATALOGO_MUNICIPIOS

def iniciar_ingesta_demografia():
    if not os.path.exists(CSV_DEMOGRAFIA):
        print(f"No se encuentra el CSV demográfico en {CSV_DEMOGRAFIA}. Se omite.")
        return

    print(f"Conectando a la base V2: {V2_DB}")
    con = duckdb.connect(V2_DB)

    # 1. Leer CSV de demografía
    df = pd.read_csv(CSV_DEMOGRAFIA, dtype=str)
    for col in ['CLAVE', 'SEXO']:
        if col in df.columns:
            df[col] = df[col].str.strip()

    df.rename(columns={'CLAVE': 'id_cvegeo'}, inplace=True)
    con.register('df_demo', df)

    # 2. Cargar el catálogo de nombres de municipios (si existe)
    nombres_municipios = None
    if os.path.exists(CATALOGO_MUNICIPIOS):
        df_catalogo = pd.read_csv(CATALOGO_MUNICIPIOS, dtype={'CLAVE': str, 'NOM_MUN': str})
        # Quedarse solo con los pares únicos CLAVE - NOM_MUN
        df_catalogo = df_catalogo[['CLAVE', 'NOM_MUN']].drop_duplicates()
        df_catalogo.columns = ['id_cvegeo', 'nombre_municipio']  # para que coincida con nuestro esquema
        con.register('catalogo_nombres', df_catalogo)
        nombres_municipios = True  # hay datos disponibles
        print(f"   Catálogo de municipios cargado: {len(df_catalogo)} registros")

    # 3. Insertar municipios nuevos que no existan en raw.municipios
    if nombres_municipios:
        # Usamos el nombre del catálogo si existe; si no, un marcador genérico
        con.execute("""
            INSERT INTO raw.municipios (id_cvegeo, id_clave_ent, nombre_municipio)
            SELECT DISTINCT
                d.id_cvegeo,
                15,
                COALESCE(c.nombre_municipio, 'MUNICIPIO POR CATALOGO REVISAR')
            FROM df_demo d
            LEFT JOIN catalogo_nombres c ON d.id_cvegeo = c.id_cvegeo
            WHERE d.id_cvegeo NOT IN (SELECT id_cvegeo FROM raw.municipios)
            ON CONFLICT DO NOTHING
        """)
    else:
        # Si no hay catálogo, insertamos con el marcador antiguo
        con.execute("""
            INSERT INTO raw.municipios (id_cvegeo, id_clave_ent, nombre_municipio)
            SELECT DISTINCT
                id_cvegeo,
                15,
                'MUNICIPIO SIN NOMBRE (REVISAR)'
            FROM df_demo
            WHERE id_cvegeo NOT IN (SELECT id_cvegeo FROM raw.municipios)
            ON CONFLICT DO NOTHING
        """)

    nuevos_muns = con.execute("SELECT COUNT(*) FROM raw.municipios").fetchone()[0]
    print(f"   Municipios en raw después de la carga: {nuevos_muns}")

    # 4. Insertar demografía (sin cambios)
    con.execute("""
        INSERT INTO raw.demografia (
            id_cvegeo, anio, sexo, pob_total,
            r_00_04, r_05_09, r_10_14, r_15_19, r_20_24,
            r_25_29, r_30_34, r_35_39, r_40_44, r_45_49,
            r_50_54, r_55_59, r_60_64, r_65_69, r_70_74,
            r_75_79, r_80_84, r_85_mm
        )
        SELECT
            id_cvegeo,
            TRY_CAST(Fecha AS INTEGER) AS anio,
            SEXO AS sexo,
            TRY_CAST(POB_TOTAL AS INTEGER) AS pob_total,
            TRY_CAST(POB_00_04 AS INTEGER), TRY_CAST(POB_05_09 AS INTEGER),
            TRY_CAST(POB_010_014 AS INTEGER), TRY_CAST(POB_015_019 AS INTEGER),
            TRY_CAST(POB_20_24 AS INTEGER), TRY_CAST(POB_25_29 AS INTEGER),
            TRY_CAST(POB_30_34 AS INTEGER), TRY_CAST(POB_35_39 AS INTEGER),
            TRY_CAST(POB_40_44 AS INTEGER), TRY_CAST(POB_45_49 AS INTEGER),
            TRY_CAST(POB_50_54 AS INTEGER), TRY_CAST(POB_55_59 AS INTEGER),
            TRY_CAST(POB_60_64 AS INTEGER), TRY_CAST(POB_65_69 AS INTEGER),
            TRY_CAST(POB_70_74 AS INTEGER), TRY_CAST(POB_75_79 AS INTEGER),
            TRY_CAST(POB_80_84 AS INTEGER), TRY_CAST(POB_85_mm AS INTEGER)
        FROM df_demo
        ON CONFLICT DO NOTHING
    """)

    total_demo = con.execute("SELECT COUNT(*) FROM raw.demografia").fetchone()[0]
    con.close()
    print(f"Demografía cruda cargada: {total_demo} registros.")

if __name__ == "__main__":
    iniciar_ingesta_demografia()