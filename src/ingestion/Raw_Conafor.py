# src/ingestion/Raw_COnAfor.py
import pandas as pd
import duckdb
import os
from config.config import V2_DB, CSV_CONAFOR

def iniciar_ingesta_conafor():
    if not os.path.exists(CSV_CONAFOR):
        print(f" No se encuentra el CSV: {CSV_CONAFOR}")
        return

    print(f"Conectando a la base V2: {V2_DB}")
    con = duckdb.connect(V2_DB)

    # 1. Lectura y limpieza del CSV (todos los años, solo Estado de México)
    df = pd.read_csv(CSV_CONAFOR, dtype=str)
    df.columns = df.columns.str.strip()
    df['Estado'] = df['Estado'].str.strip()
    df_edomex = df[df['Estado'] == 'México'].copy()

    # Limpieza de fechas (intenta formato ISO y luego D/M/Y)
    fechas_crudas = df_edomex['Fecha Inicio'].astype(str).str.split(' ').str[0].str.strip()
    df_edomex['Fecha Inicio'] = pd.to_datetime(fechas_crudas, format='%Y-%m-%d', errors='coerce')
    mask_nulos = df_edomex['Fecha Inicio'].isna()
    df_edomex.loc[mask_nulos, 'Fecha Inicio'] = pd.to_datetime(
        fechas_crudas[mask_nulos], format='%d/%m/%Y', errors='coerce'
    )

    # Limpieza de coordenadas
    for col in ['Latitud', 'Longitud']:
        df_edomex[col] = df_edomex[col].astype(str).str.replace(',', '.').str.strip()
    df_edomex['Latitud'] = pd.to_numeric(df_edomex['Latitud'], errors='coerce')
    df_edomex['Longitud'] = pd.to_numeric(df_edomex['Longitud'], errors='coerce')

    # Eliminar filas sin datos geoespaciales válidos
    df_validos = df_edomex.dropna(subset=['Fecha Inicio', 'Latitud', 'Longitud']).copy()

    # Formateo final de fecha
    df_validos['Fecha Inicio'] = df_validos['Fecha Inicio'].dt.strftime('%Y-%m-%d')

    # Normalización de columnas numéricas
    columnas_numericas = ['Año', 'Arbolado Adulto', 'Renuevo', 'Arbustivo',
                          'Herbáceo', 'Hojarasca', 'Total hectáreas']
    for col in columnas_numericas:
        df_validos[col] = pd.to_numeric(df_validos[col], errors='coerce').fillna(0)

    # 2. Inserción en el esquema raw
    print("\nInsertando datos en el esquema raw...")
    con.register('df_temp', df_validos)

    # Catálogos
    con.execute("""
        INSERT INTO raw.estado (id_clave_ent, region, estado)
        SELECT DISTINCT CAST(CVE_ENT AS INTEGER), Región, Estado
        FROM df_temp ON CONFLICT DO NOTHING
    """)

    # ----- MUNICIPIOS con código normalizado -----
    con.execute("""
        INSERT INTO raw.municipios (id_cvegeo, id_clave_ent, nombre_municipio)
        SELECT DISTINCT
            CASE
                -- código invertido (larga 5, termina en '15' y no empieza por '15')
                WHEN LENGTH(CVEGEO) = 5 AND CVEGEO LIKE '%15' AND CVEGEO NOT LIKE '15%'
                THEN SUBSTR(CVEGEO, 4, 2) || LPAD(SUBSTR(CVEGEO, 1, 3), 3, '0')
                -- código corto (<5 dígitos)
                WHEN LENGTH(CVEGEO) < 5
                THEN '15' || LPAD(SUBSTR(CVEGEO, 1, LENGTH(CVEGEO)-2), 3, '0')
                -- ya está en formato correcto
                ELSE CVEGEO
            END AS id_cvegeo_normalizado,
            CAST(CVE_ENT AS INTEGER),
            Municipio
        FROM df_temp
        ON CONFLICT DO NOTHING
    """)

    con.execute("""
        INSERT INTO raw.causa (causa, causa_especifica)
        SELECT DISTINCT Causa, "Causa especifica" FROM df_temp
        EXCEPT SELECT causa, causa_especifica FROM raw.causa
    """)
    con.execute("""
        INSERT INTO raw.vegetacion (regimen_del_fuego, tipo_de_vegetacion)
        SELECT DISTINCT "Régimen de fuego", "Tipo Vegetación" FROM df_temp
        EXCEPT SELECT regimen_del_fuego, tipo_de_vegetacion FROM raw.vegetacion
    """)

    # ----- INCENDIOS con código normalizado -----
    con.execute("""
        INSERT INTO raw.incendios (id_clave_inc, id_cvegeo, id_causa, id_vegetacion,
                                   latitud, longitud, fecha_inicio, tipo_de_incendio, anio)
        SELECT
            t."Clave del incendio",
            CASE
                WHEN LENGTH(t.CVEGEO) = 5 AND t.CVEGEO LIKE '%15' AND t.CVEGEO NOT LIKE '15%'
                THEN SUBSTR(t.CVEGEO, 4, 2) || LPAD(SUBSTR(t.CVEGEO, 1, 3), 3, '0')
                WHEN LENGTH(t.CVEGEO) < 5
                THEN '15' || LPAD(SUBSTR(t.CVEGEO, 1, LENGTH(t.CVEGEO)-2), 3, '0')
                ELSE t.CVEGEO
            END AS cvegeo_normalizado,
            c.id_causa,
            v.id_vegetacion,
            t.Latitud,
            t.Longitud,
            CAST(t."Fecha Inicio" AS DATE),
            t."Tipo de incendio",
            CAST(t.Año AS INTEGER)
        FROM df_temp t
        JOIN raw.causa c ON t.Causa = c.causa AND t."Causa especifica" = c.causa_especifica
        JOIN raw.vegetacion v ON t."Régimen de fuego" = v.regimen_del_fuego AND t."Tipo Vegetación" = v.tipo_de_vegetacion
        ON CONFLICT DO NOTHING
    """)

    # Daños
    con.execute("""
        INSERT INTO raw.danos (id_clave_inc, hojarasca, arbustivo, herbaceo, arbolado_adulto, renuevo, tamanio)
        SELECT
            "Clave del incendio",
            Hojarasca,
            Arbustivo,
            Herbáceo,
            "Arbolado Adulto",
            Renuevo,
            Tamaño
        FROM df_temp
        ON CONFLICT DO NOTHING
    """)

    # Operaciones (solo clave primaria)
    con.execute("""
        INSERT OR IGNORE INTO raw.operaciones (id_clave_inc)
        SELECT DISTINCT "Clave del incendio" FROM df_temp
    """)

    # 3. Resumen final
    total_incendios = con.execute("SELECT COUNT(*) FROM raw.incendios").fetchone()[0]
    total_2025 = con.execute("SELECT COUNT(*) FROM raw.incendios WHERE anio = 2025").fetchone()[0]
    total_operaciones = con.execute("SELECT COUNT(*) FROM raw.operaciones").fetchone()[0]
    con.close()

    print("\n Datos de CONAFOR insertados correctamente en el esquema raw.")
    print(f"   - Incendios totales: {total_incendios}")
    print(f"   - Incendios 2025: {total_2025}")
    print(f"   - Operaciones vinculadas: {total_operaciones}")

if __name__ == "__main__":
    iniciar_ingesta_conafor()