-- ==========================================
-- 0. CREACIÓN SEGURA (Sin borrar datos históricos)
-- ==========================================

CREATE SEQUENCE IF NOT EXISTS seq_vegetacion;
CREATE SEQUENCE IF NOT EXISTS seq_causa;
CREATE SEQUENCE IF NOT EXISTS seq_registro;

-- ==========================================
-- NIVEL 1: ENTIDADES PADRE (INDEPENDIENTES)
-- ==========================================

CREATE TABLE IF NOT EXISTS diccionario ( 
    id_variable VARCHAR PRIMARY KEY, 
    fuente VARCHAR NOT NULL,
    nombre_completo VARCHAR NOT NULL,
    unidad_de_medida VARCHAR        
);

CREATE TABLE IF NOT EXISTS estado (
    id_clave_ent INTEGER PRIMARY KEY, 
    region VARCHAR,
    estado VARCHAR 
);

CREATE TABLE IF NOT EXISTS vegetacion (
    id_vegetacion INTEGER PRIMARY KEY DEFAULT nextval('seq_vegetacion'),
    regimen_del_fuego VARCHAR NOT NULL,
    tipo_de_vegetacion VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS causa (
    id_causa INTEGER PRIMARY KEY DEFAULT nextval('seq_causa'),
    causa VARCHAR NOT NULL,
    causa_especifica VARCHAR NOT NULL
);

-- ==========================================
-- NIVEL 2: ENTIDADES DE SEGUNDO NIVEL
-- ==========================================

CREATE TABLE IF NOT EXISTS municipios (
    id_cvegeo VARCHAR PRIMARY KEY,    
    id_clave_ent INTEGER NOT NULL, 
    nombre_municipio VARCHAR NOT NULL,
    FOREIGN KEY (id_clave_ent) REFERENCES estado(id_clave_ent)
);

-- ==========================================
-- NIVEL 3: LA ENTIDAD CENTRAL (INCENDIOS)
-- ==========================================

CREATE TABLE IF NOT EXISTS incendios (
    id_clave_inc VARCHAR PRIMARY KEY, 
    id_cvegeo VARCHAR NOT NULL,       
    id_causa INTEGER NOT NULL, 
    id_vegetacion INTEGER NOT NULL, 
    latitud FLOAT,    -- MODIFICADO: Ahora permite NULL para limpieza
    longitud FLOAT,   -- MODIFICADO: Ahora permite NULL para limpieza
    fecha_inicio DATE NOT NULL,
    tipo_de_incendio VARCHAR NOT NULL,
    anio INTEGER NOT NULL,            
    
    FOREIGN KEY (id_cvegeo) REFERENCES municipios(id_cvegeo),
    FOREIGN KEY (id_causa) REFERENCES causa(id_causa),
    FOREIGN KEY (id_vegetacion) REFERENCES vegetacion(id_vegetacion)
);

-- ==========================================
-- NIVEL 3.5: ENTIDAD DEMOGRÁFICA
-- ==========================================

CREATE TABLE IF NOT EXISTS demografia (
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
    FOREIGN KEY (id_cvegeo) REFERENCES municipios(id_cvegeo)
);

-- ==========================================
-- NIVEL 4: TABLAS HIJAS (DEPENDEN DE INCENDIOS)
-- ==========================================

CREATE TABLE IF NOT EXISTS danos (                  
    id_clave_inc VARCHAR PRIMARY KEY, 
    hojarasca FLOAT,        -- MODIFICADO: Permite NULL
    arbustivo FLOAT,        -- MODIFICADO: Permite NULL
    herbaceo FLOAT,         -- MODIFICADO: Permite NULL
    arbolado_adulto FLOAT,  -- MODIFICADO: Permite NULL
    renuevo FLOAT,          -- MODIFICADO: Permite NULL
    tamanio VARCHAR NOT NULL,         
    FOREIGN KEY (id_clave_inc) REFERENCES incendios(id_clave_inc)
);

-- NUEVA TABLA: Operaciones (Relación 1 a 1)
CREATE TABLE IF NOT EXISTS operaciones (
    id_clave_inc VARCHAR PRIMARY KEY,  
    fecha_termino DATE,
    hora_deteccion TIME,
    hora_llegada TIME,
    duracion_hhmm INTERVAL,            
    duracion_dias INTEGER,
    
    FOREIGN KEY (id_clave_inc) REFERENCES incendios(id_clave_inc)
);

-- Modelo EAV para clima satelital (Manejo de Series Temporales)
CREATE TABLE IF NOT EXISTS climatologia (
    id_registro BIGINT PRIMARY KEY DEFAULT nextval('seq_registro'),
    id_variable VARCHAR NOT NULL,     
    id_clave_inc VARCHAR NOT NULL,    
    fecha_de_observacion DATE NOT NULL,
    resultado_numerico FLOAT NOT NULL,
    
    FOREIGN KEY (id_variable) REFERENCES diccionario(id_variable), 
    FOREIGN KEY (id_clave_inc) REFERENCES incendios(id_clave_inc) 
);