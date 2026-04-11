import os

# --- CÁLCULO DE RUTAS ABSOLUTAS ---
# SCRIPT_DIR es 03_LimpiezaDeDatos/scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# BASE_DIR es la raíz del proyecto (IncendiosForestales/)
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# --- RUTAS DE BASES DE DATOS ---
RAW_DB = os.path.join(BASE_DIR, 'data', 'BaseDeDatos_Raw.db')
WORKING_DB = os.path.join(BASE_DIR, 'data', 'BaseDeDatos_Working.db')

# --- RUTAS DE ARCHIVOS EXTERNOS ---
SCHEMA_SQL = os.path.join(BASE_DIR, 'data', 'scripts', 'CorreccionCodigo.sql')
CSV_POBLACION = os.path.join(BASE_DIR, '01_ExtraccionDeDatos', 'DatosPoblacion', 'raw', 'Edomx_poblacion.csv')