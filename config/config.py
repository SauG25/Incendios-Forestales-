# config/config.py
import os

# Directorio raíz del proyecto (subiendo dos niveles desde config/)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Bases de datos
RAW_DB = os.path.join(ROOT_DIR, 'data', 'BaseDeDatos_Raw.db')       # Antigua sucia
WORKING_DB = os.path.join(ROOT_DIR, 'data', 'BaseDeDatos_Working.db')  # Antigua limpia
V2_DB = os.path.join(ROOT_DIR, 'data', '02_interim', 'IncendiosForestales_V2.db')  # Nueva

# Archivos fuente
CSV_CONAFOR = os.path.join(ROOT_DIR, 'data', '01_raw', 'DatosConafor.csv')
CSV_DEMOGRAFIA = os.path.join(ROOT_DIR, 'data', '01_raw', 'DatosDemograficos.csv')


# Archivo con el catálogo de municipios (CLAVE, NOM_MUN)
CATALOGO_MUNICIPIOS = os.path.join(ROOT_DIR, 'data', '01_raw', 'Edomx_poblacion.csv')