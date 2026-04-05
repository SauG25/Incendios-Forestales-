import pandas as pd
import duckdb
import os

# --- RUTAS AUTOMÁTICAS ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))

# Configuración de rutas hacia la carpeta data y el CSV de CONAFOR
DB_PATH = os.path.join(ROOT_DIR, 'data', 'BaseDeDatos.db')
SQL_SCHEMA = os.path.join(ROOT_DIR, 'data', 'scripts', 'CorreccionCodigo.sql')
CSV_PATH = os.path.join(ROOT_DIR, '01_ExtraccionDeDatos', 'DatosConafor', 'raw', 'incendios_forestales_2015_2025.csv')

def iniciar_arquitectura_y_cargar():
    print(f"Conectando a la base de datos real en: {DB_PATH}")
    con = duckdb.connect(DB_PATH)

    # 1. EJECUTAR EL SQL AUTOMÁTICAMENTE
    if os.path.exists(SQL_SCHEMA):
        print("Leyendo archivo SQL para reconstruir las tablas...")
        with open(SQL_SCHEMA, 'r', encoding='utf-8') as f:
            con.execute(f.read())
        print("Tablas creadas correctamente con BIGINT.")
    else:
        print(f"Error: No se encontro el archivo SQL en {SQL_SCHEMA}")
        con.close()
        return

    # 2. CARGAR LOS DATOS
    print("\nCargando datos de CONAFOR...")
    if not os.path.exists(CSV_PATH):
        print(f"Error: No se encontro el archivo CSV en {CSV_PATH}")
        con.close()
        return

    df = pd.read_csv(CSV_PATH, dtype=str)
    # Filtro para el Estado de México
    df_edomex = df[df['Estado'] == 'México'].copy()
    print(f"Registros del Estado de Mexico encontrados: {len(df_edomex)}")
    
    # Limpieza de datos
    df_edomex['Latitud'] = pd.to_numeric(df_edomex['Latitud'], errors='coerce')
    df_edomex['Longitud'] = pd.to_numeric(df_edomex['Longitud'], errors='coerce')
    df_edomex['Fecha Inicio'] = pd.to_datetime(df_edomex['Fecha Inicio'], errors='coerce')
    
    # Eliminación de nulos en columnas críticas
    df_edomex = df_edomex.dropna(subset=['Fecha Inicio', 'Latitud', 'Longitud'])
    df_edomex['Fecha Inicio'] = df_edomex['Fecha Inicio'].dt.strftime('%Y-%m-%d')
    
    # Normalización de columnas numéricas
    cols_num = ['Año', 'Arbolado Adulto', 'Renuevo', 'Arbustivo', 'Herbáceo', 'Hojarasca', 'Total hectáreas']
    for col in cols_num:
        df_edomex[col] = pd.to_numeric(df_edomex[col], errors='coerce').fillna(0)

    con.register('df_temp', df_edomex)

    # Inserción en catálogos y tablas de hechos
    print("Guardando catalogos e incendios...")
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

    con.close()
    print("Terminado. La base de datos ha sido actualizada correctamente.")

if __name__ == "__main__":
    iniciar_arquitectura_y_cargar()