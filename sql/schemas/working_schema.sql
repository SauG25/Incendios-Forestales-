-- ==========================================
-- ESQUEMA WORKING (Versión limpia)
-- ==========================================

CREATE SCHEMA IF NOT EXISTS working;

-- Secuencias dentro del esquema working
CREATE SEQUENCE IF NOT EXISTS working.seq_vegetacion;
CREATE SEQUENCE IF NOT EXISTS working.seq_causa;
CREATE SEQUENCE IF NOT EXISTS working.seq_registro;

-- Nivel 1: Entidades padre
CREATE TABLE IF NOT EXISTS working.diccionario (
    id_variable VARCHAR PRIMARY KEY,
    fuente VARCHAR NOT NULL,
    nombre_completo VARCHAR NOT NULL,
    unidad_de_medida VARCHAR
);

CREATE TABLE IF NOT EXISTS working.estado (
    id_clave_ent INTEGER PRIMARY KEY,
    region VARCHAR,
    estado VARCHAR
);

CREATE TABLE IF NOT EXISTS working.vegetacion (
    id_vegetacion INTEGER PRIMARY KEY DEFAULT nextval('working.seq_vegetacion'),
    regimen_del_fuego VARCHAR NOT NULL,
    tipo_de_vegetacion VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS working.causa (
    id_causa INTEGER PRIMARY KEY DEFAULT nextval('working.seq_causa'),
    causa VARCHAR NOT NULL,
    causa_especifica VARCHAR NOT NULL
);

-- Nivel 2: Municipios (aquí los CVEGEO estarán corregidos)
CREATE TABLE IF NOT EXISTS working.municipios (
    id_cvegeo VARCHAR PRIMARY KEY,
    id_clave_ent INTEGER NOT NULL,
    nombre_municipio VARCHAR NOT NULL,
    FOREIGN KEY (id_clave_ent) REFERENCES working.estado(id_clave_ent)
);

-- Nivel 3: Incendios (con CVEGEO corregido)
CREATE TABLE IF NOT EXISTS working.incendios (
    id_clave_inc VARCHAR PRIMARY KEY,
    id_cvegeo VARCHAR NOT NULL,
    id_causa INTEGER NOT NULL,
    id_vegetacion INTEGER NOT NULL,
    latitud FLOAT,
    longitud FLOAT,
    fecha_inicio DATE NOT NULL,
    tipo_de_incendio VARCHAR NOT NULL,
    anio INTEGER NOT NULL,
    FOREIGN KEY (id_cvegeo) REFERENCES working.municipios(id_cvegeo),
    FOREIGN KEY (id_causa) REFERENCES working.causa(id_causa),
    FOREIGN KEY (id_vegetacion) REFERENCES working.vegetacion(id_vegetacion)
);

-- Demografía (ya tendrá las columnas extra rellenas)
CREATE TABLE IF NOT EXISTS working.demografia (
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
    FOREIGN KEY (id_cvegeo) REFERENCES working.municipios(id_cvegeo)
);

-- Daños
CREATE TABLE IF NOT EXISTS working.danos (
    id_clave_inc VARCHAR PRIMARY KEY,
    hojarasca FLOAT,
    arbustivo FLOAT,
    herbaceo FLOAT,
    arbolado_adulto FLOAT,
    renuevo FLOAT,
    tamanio VARCHAR NOT NULL,
    FOREIGN KEY (id_clave_inc) REFERENCES working.incendios(id_clave_inc)
);

-- Operaciones (ya con duraciones y horas)
CREATE TABLE IF NOT EXISTS working.operaciones (
    id_clave_inc VARCHAR PRIMARY KEY,
    fecha_termino DATE,
    hora_deteccion TIME,
    hora_llegada TIME,
    duracion_hhmm INTERVAL,
    duracion_dias INTEGER,
    FOREIGN KEY (id_clave_inc) REFERENCES working.incendios(id_clave_inc)
);

-- Climatología
CREATE TABLE IF NOT EXISTS working.climatologia (
    id_registro BIGINT PRIMARY KEY DEFAULT nextval('working.seq_registro'),
    id_variable VARCHAR NOT NULL,
    id_clave_inc VARCHAR NOT NULL,
    fecha_de_observacion DATE NOT NULL,
    resultado_numerico FLOAT,
    FOREIGN KEY (id_variable) REFERENCES working.diccionario(id_variable),
    FOREIGN KEY (id_clave_inc) REFERENCES working.incendios(id_clave_inc)
);