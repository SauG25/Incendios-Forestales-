import pandas as pd
import os

def cargar_demografia(con, csv_path):
    if not os.path.exists(csv_path):
        print(f"   - [Enrichment] Advertencia: No se encontró el CSV en {csv_path}. Saltando carga.")
        return

    print("   - [Enrichment] Cargando y formateando datos demográficos...")
    try:
        # 1. Leer el CSV y formatear
        df = pd.read_csv(csv_path)
        df['id_cvegeo'] = df['CLAVE'].astype(str).str.zfill(5)
        con.register('df_demo_temp', df)

        # 2. EL SALVAVIDAS: Crear municipios que vienen en el CSV pero no están en la BD
        con.execute("""
            INSERT INTO main.municipios (id_cvegeo, id_clave_ent, nombre_municipio)
            SELECT DISTINCT 
                id_cvegeo, 
                15, 
                'MUNICIPIO DESDE CSV POR REVISAR'
            FROM df_demo_temp
            WHERE id_cvegeo NOT IN (SELECT id_cvegeo FROM main.municipios)
        """)

        # 3. Insertar Demografía (ahora sí, todos los municipios existen)
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
        print(f"   - [Enrichment] Demografía insertada con éxito ({filas} registros).")
    
    except Exception as e:
        print(f"   - [Enrichment] Error al procesar la demografía: {e}")