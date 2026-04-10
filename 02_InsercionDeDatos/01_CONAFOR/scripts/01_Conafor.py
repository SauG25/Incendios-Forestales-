import pandas as pd
import duckdb
import os

# --- RUTAS AUTOMÁTICAS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))

DB_PATH = os.path.join(ROOT_DIR, 'data', 'BaseDeDatos_Raw.db')
SQL_SCHEMA = os.path.join(ROOT_DIR, 'data', 'scripts', 'CorreccionCodigo.sql')
CSV_PATH = os.path.join(ROOT_DIR, '01_ExtraccionDeDatos', 'DatosConafor', 'raw', 'incendios_forestales_2015_2025.csv')

def iniciar_arquitectura_y_cargar():
    print(f"Conectando a la base de datos en: {DB_PATH}")
    con = duckdb.connect(DB_PATH)

    # 1. EJECUTAR EL SQL CON PRECAUCIÓN
    if os.path.exists(SQL_SCHEMA):
        print("Verificando estructura de tablas...")
        with open(SQL_SCHEMA, 'r', encoding='utf-8') as f:
            con.execute(f.read())
    else:
        print(f"Error: No se encontró el archivo SQL en {SQL_SCHEMA}")
        con.close()
        return

    # 2. CARGAR Y FILTRAR DATOS
    print("\nLeyendo CSV de CONAFOR...")
    df = pd.read_csv(CSV_PATH, dtype=str)
    
    # --- LIMPIEZA BLINDADA ---
    df.columns = df.columns.str.strip()
    if 'Estado' in df.columns:
        df['Estado'] = df['Estado'].str.strip()
        
    # Filtro EXACTO para 'México' (Ignora 'Ciudad de México')
    df_edomex = df[df['Estado'] == 'México'].copy()
    
    # --- LIMPIEZA DE FECHAS ANTI-ERRORES ---
    # Quitamos la hora si la trae (el " 00:00:00") para evitar advertencias
    fechas_crudas = df_edomex['Fecha Inicio'].astype(str).str.split(' ').str[0].str.strip()
    
    # Intentamos primero el formato Año-Mes-Día (ISO)
    df_edomex['Fecha Inicio'] = pd.to_datetime(fechas_crudas, format='%Y-%m-%d', errors='coerce')
    
    # Si alguna falló (NaT), intentamos el formato Día/Mes/Año para esos casos específicos
    mask_nulos = df_edomex['Fecha Inicio'].isna()
    df_edomex.loc[mask_nulos, 'Fecha Inicio'] = pd.to_datetime(fechas_crudas[mask_nulos], format='%d/%m/%Y', errors='coerce')
    
    # --- LIMPIEZA DE COORDENADAS ---
    df_edomex['Latitud'] = df_edomex['Latitud'].astype(str).str.replace(',', '.').str.strip()
    df_edomex['Longitud'] = df_edomex['Longitud'].astype(str).str.replace(',', '.').str.strip()
    
    df_edomex['Latitud'] = pd.to_numeric(df_edomex['Latitud'], errors='coerce')
    df_edomex['Longitud'] = pd.to_numeric(df_edomex['Longitud'], errors='coerce')

    # --- EL DETECTIVE (Diagnóstico específico para 2025) ---
    df_2025 = df_edomex[df_edomex['Año'] == '2025']
    total_2025_antes = len(df_2025)
    
    print("\n--- DIAGNÓSTICO 2025 ---")
    print(f"Total registros 2025 antes de limpiar: {total_2025_antes}")
    print(f"Fallos o vacíos en Fecha: {df_2025['Fecha Inicio'].isna().sum()}")
    print(f"Fallos o vacíos en Latitud: {df_2025['Latitud'].isna().sum()}")
    print(f"Fallos o vacíos en Longitud: {df_2025['Longitud'].isna().sum()}")
    print("------------------------\n")

    # Eliminación de nulos críticos
    df_edomex = df_edomex.dropna(subset=['Fecha Inicio', 'Latitud', 'Longitud'])
    
    total_2025_despues = len(df_edomex[df_edomex['Año'] == '2025'])
    print(f"Registros de 2025 que pasaron el filtro y están listos: {total_2025_despues}")

    # Formatear fecha final para SQL
    df_edomex['Fecha Inicio'] = df_edomex['Fecha Inicio'].dt.strftime('%Y-%m-%d')
    
    # Normalización numérica del resto de datos
    cols_num = ['Año', 'Arbolado Adulto', 'Renuevo', 'Arbustivo', 'Herbáceo', 'Hojarasca', 'Total hectáreas']
    for col in cols_num:
        df_edomex[col] = pd.to_numeric(df_edomex[col], errors='coerce').fillna(0)

    # 3. INSERCIÓN SEGURA (ON CONFLICT DO NOTHING)
    con.register('df_temp', df_edomex)
    print("\nSincronizando catálogos e incendios...")

    con.execute("INSERT INTO estado (id_clave_ent, region, estado) SELECT DISTINCT CAST(CVE_ENT AS INTEGER), Región, Estado FROM df_temp ON CONFLICT DO NOTHING;")
    con.execute("INSERT INTO municipios (id_cvegeo, id_clave_ent, nombre_municipio) SELECT DISTINCT CVEGEO, CAST(CVE_ENT AS INTEGER), Municipio FROM df_temp ON CONFLICT DO NOTHING;")
    
    con.execute("INSERT INTO causa (causa, causa_especifica) SELECT DISTINCT Causa, \"Causa especifica\" FROM df_temp EXCEPT SELECT causa, causa_especifica FROM causa;")
    con.execute("INSERT INTO vegetacion (regimen_del_fuego, tipo_de_vegetacion) SELECT DISTINCT \"Régimen de fuego\", \"Tipo Vegetación\" FROM df_temp EXCEPT SELECT regimen_del_fuego, tipo_de_vegetacion FROM vegetacion;")

    con.execute("""
        INSERT INTO incendios (id_clave_inc, id_cvegeo, id_causa, id_vegetacion, latitud, longitud, fecha_inicio, tipo_de_incendio, anio)
        SELECT t."Clave del incendio", t.CVEGEO, c.id_causa, v.id_vegetacion, t.Latitud, t.Longitud, CAST(t."Fecha Inicio" AS DATE), t."Tipo de incendio", CAST(t.Año AS INTEGER)
        FROM df_temp t
        JOIN causa c ON t.Causa = c.causa AND t."Causa especifica" = c.causa_especifica
        JOIN vegetacion v ON t."Régimen de fuego" = v.regimen_del_fuego AND t."Tipo Vegetación" = v.tipo_de_vegetacion
        ON CONFLICT DO NOTHING;
    """)

    con.execute("""
        INSERT INTO danos (id_clave_inc, hojarasca, arbustivo, herbaceo, arbolado_adulto, renuevo, tamanio)
        SELECT "Clave del incendio", Hojarasca, Arbustivo, Herbáceo, "Arbolado Adulto", Renuevo, Tamaño FROM df_temp ON CONFLICT DO NOTHING;
    """)

    # Verificación final
    conteo_total = con.execute("SELECT COUNT(*) FROM incendios").fetchone()[0]
    conteo_2025 = con.execute("SELECT COUNT(*) FROM incendios WHERE anio = 2025").fetchone()[0]
    
    con.close()
    print(f"\n--- REPORTE FINAL ---")
    print(f"Total de incendios históricos blindados en la base: {conteo_total}")
    print(f"Incendios del año 2025 cargados exitosamente: {conteo_2025}")
    print("Proceso terminado.")

if __name__ == "__main__":
    iniciar_arquitectura_y_cargar()