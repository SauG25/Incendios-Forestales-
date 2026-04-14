import pandas as pd
import os

def cargar_demografia(con, csv_path):
    if not os.path.exists(csv_path):
        print(f"   - [Enrichment] Advertencia: No se encontro el CSV en {csv_path}. Saltando carga.")
        return

    print("   - [Enrichment] Cargando y formateando datos demograficos...")
    try:
        # 1. Leer el CSV y formatear
        df = pd.read_csv(csv_path)
        # Aseguramos limpieza y formato de 5 digitos para el municipio
        df['id_cvegeo'] = df['CLAVE'].astype(str).str.strip().str.zfill(5)
        con.register('df_demo_temp', df)

        # 2. EL SALVAVIDAS: Crear municipios que vienen en el CSV pero no estan en la BD
        con.execute("""
            INSERT INTO main.municipios (id_cvegeo, id_clave_ent, nombre_municipio)
            SELECT DISTINCT 
                id_cvegeo, 
                15, 
                'MUNICIPIO DESDE CSV POR REVISAR'
            FROM df_demo_temp
            WHERE id_cvegeo NOT IN (SELECT id_cvegeo FROM main.municipios)
            ON CONFLICT DO NOTHING
        """)

        # 3. Insertar Demografia
        con.execute("""
            INSERT INTO main.demografia 
            SELECT 
                id_cvegeo, Fecha as anio, SEXO as sexo, POB_TOTAL as pob_total,
                POB_00_04 as r_00_04, POB_05_09 as r_05_09, POB_010_014 as r_10_14, 
                POB_015_019 as r_15_19, POB_20_24 as r_20_24, POB_25_29 as r_25_29, 
                POB_30_34 as r_30_34, POB_35_39 as r_35_39, POB_40_44 as r_40_44, 
                POB_45_49 as r_45_49, POB_50_54 as r_50_54, POB_55_59 as r_55_59, 
                POB_60_64 as r_60_64, POB_65_69 as r_65_69, POB_70_74 as r_70_74, 
                POB_75_79 as r_75_79, POB_80_84 as r_80_84, POB_85_mm as r_85_mm
            FROM df_demo_temp
            ON CONFLICT DO NOTHING;
        """)
        
        filas = con.execute("SELECT count(*) FROM main.demografia").fetchone()[0]
        print(f"   - [Enrichment] Demografia insertada con exito ({filas} registros).")
    
    except Exception as e:
        print(f"   - [Enrichment] Error al procesar la demografia: {e}")

def cargar_operaciones(con, archivo_operaciones):
    if not os.path.exists(archivo_operaciones):
        print(f"   - [Enrichment] Advertencia: No se encontro el archivo en {archivo_operaciones}.")
        return

    print("   - [Enrichment] Cargando datos de operaciones desde CSV original...")
    try:
        df_ops = pd.read_csv(archivo_operaciones, dtype=str)
        df_ops.columns = df_ops.columns.str.strip()
            
        con.register('df_ops_temp', df_ops)

        # Aplicamos TRIM a la clave del incendio para evitar el error de Foreing Key
        con.execute("""
            INSERT INTO main.operaciones (
                id_clave_inc, 
                fecha_termino, 
                hora_deteccion, 
                hora_llegada, 
                duracion_hhmm, 
                duracion_dias
            )
            SELECT 
                TRIM("Clave del incendio"),
                TRY_CAST(strptime("Fecha Termino", '%d/%m/%Y') AS DATE),
                TRY_CAST("Detección" AS TIME),
                TRY_CAST("Llegada" AS TIME),
                TRY_CAST("Duración" AS INTERVAL),
                TRY_CAST("Duración días" AS INTEGER)
            FROM df_ops_temp
            WHERE TRIM("Clave del incendio") IN (SELECT id_clave_inc FROM main.incendios)
            ON CONFLICT DO NOTHING;
        """)
        
        filas = con.execute("SELECT count(*) FROM main.operaciones").fetchone()[0]
        print(f"   - [Enrichment] Operaciones insertadas con exito ({filas} registros).")
    
    except Exception as e:
        print(f"   - [Enrichment] Error al procesar operaciones: {e}")