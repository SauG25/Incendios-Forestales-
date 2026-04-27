-- ==========================================
-- ESQUEMA RAW (Versión sucia)
-- ==========================================

CREATE SCHEMA IF NOT EXISTS raw;

-- Secuencias dentro del esquema raw
CREATE SEQUENCE IF NOT EXISTS raw.seq_vegetacion;
CREATE SEQUENCE IF NOT EXISTS raw.seq_causa;
CREATE SEQUENCE IF NOT EXISTS raw.seq_registro;

-- Nivel 1: Entidades padre
CREATE TABLE IF NOT EXISTS raw.diccionario (
    id_variable VARCHAR PRIMARY KEY,
    fuente VARCHAR NOT NULL,
    nombre_completo VARCHAR NOT NULL,
    unidad_de_medida VARCHAR
);

CREATE TABLE IF NOT EXISTS raw.estado (
    id_clave_ent INTEGER PRIMARY KEY,
    region VARCHAR,
    estado VARCHAR
);

CREATE TABLE IF NOT EXISTS raw.vegetacion (
    id_vegetacion INTEGER PRIMARY KEY DEFAULT nextval('raw.seq_vegetacion'),
    regimen_del_fuego VARCHAR NOT NULL,
    tipo_de_vegetacion VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.causa (
    id_causa INTEGER PRIMARY KEY DEFAULT nextval('raw.seq_causa'),
    causa VARCHAR NOT NULL,
    causa_especifica VARCHAR NOT NULL
);

-- Nivel 2: Municipios (aquí los CVEGEO estarán sucios)
CREATE TABLE IF NOT EXISTS raw.municipios (
    id_cvegeo VARCHAR PRIMARY KEY,
    id_clave_ent INTEGER NOT NULL,
    nombre_municipio VARCHAR NOT NULL,
    FOREIGN KEY (id_clave_ent) REFERENCES raw.estado(id_clave_ent)
);

-- Nivel 3: Incendios (con CVEGEO sucio)
CREATE TABLE IF NOT EXISTS raw.incendios (
    id_clave_inc VARCHAR PRIMARY KEY,
    id_cvegeo VARCHAR NOT NULL,
    id_causa INTEGER NOT NULL,
    id_vegetacion INTEGER NOT NULL,
    latitud FLOAT,
    longitud FLOAT,
    fecha_inicio DATE NOT NULL,
    tipo_de_incendio VARCHAR NOT NULL,
    anio INTEGER NOT NULL,
    FOREIGN KEY (id_cvegeo) REFERENCES raw.municipios(id_cvegeo),
    FOREIGN KEY (id_causa) REFERENCES raw.causa(id_causa),
    FOREIGN KEY (id_vegetacion) REFERENCES raw.vegetacion(id_vegetacion)
);

-- Nivel 3.5: Demografía (columnas extra quedarán NULL hasta limpieza)
CREATE TABLE IF NOT EXISTS raw.demografia (
    id_cvegeo VARCHAR NOT NULL,
    anio INTEGER NOT NULL,
    sexo VARCHAR NOT NULL,
    pob_total INTEGER NOT NULL,
    r_00_04 INTEGER, r_05_09 INTEGER, r_10_14 INTEGER, r_15_19 INTEGER,
    r_20_24 INTEGER, r_25_29 INTEGER, r_30_34 INTEGER, r_35_39 INTEGER,
    r_40_44 INTEGER, r_45_49 INTEGER, r_50_54 INTEGER, r_55_59 INTEGER,
    r_60_64 INTEGER, r_65_69 INTEGER, r_70_74 INTEGER, r_75_79 INTEGER,
    r_80_84 INTEGER, r_85_mm INTEGER,
    PRIMARY KEY (id_cvegeo, anio, sexo),
    FOREIGN KEY (id_cvegeo) REFERENCES raw.municipios(id_cvegeo)
);

-- Nivel 4: Daños
CREATE TABLE IF NOT EXISTS raw.danos (
    id_clave_inc VARCHAR PRIMARY KEY,
    hojarasca FLOAT,
    arbustivo FLOAT,
    herbaceo FLOAT,
    arbolado_adulto FLOAT,
    renuevo FLOAT,
    tamanio VARCHAR NOT NULL,
    FOREIGN KEY (id_clave_inc) REFERENCES raw.incendios(id_clave_inc)
);

-- Operaciones (columnas extra vacías en sucio)
CREATE TABLE IF NOT EXISTS raw.operaciones (
    id_clave_inc VARCHAR PRIMARY KEY,
    fecha_termino DATE,
    hora_deteccion TIME,
    hora_llegada TIME,
    duracion_hhmm INTERVAL,
    duracion_dias INTEGER,
    FOREIGN KEY (id_clave_inc) REFERENCES raw.incendios(id_clave_inc)
);

-- Climatología (EAV)
CREATE TABLE IF NOT EXISTS raw.climatologia (
    id_registro BIGINT PRIMARY KEY DEFAULT nextval('raw.seq_registro'),
    id_variable VARCHAR NOT NULL,
    id_clave_inc VARCHAR NOT NULL,
    fecha_de_observacion DATE NOT NULL,
    resultado_numerico FLOAT,
    FOREIGN KEY (id_variable) REFERENCES raw.diccionario(id_variable),
    FOREIGN KEY (id_clave_inc) REFERENCES raw.incendios(id_clave_inc)
);