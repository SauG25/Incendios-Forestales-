-- ==========================================
-- 0. LIMPIEZA TOTAL (Prevención de duplicados y conflictos)
-- ==========================================
DROP TABLE IF EXISTS climatologia;
DROP TABLE IF EXISTS danos;
DROP TABLE IF EXISTS incendios;
DROP TABLE IF EXISTS municipios;
DROP TABLE IF EXISTS estado;
DROP TABLE IF EXISTS causa;
DROP TABLE IF EXISTS vegetacion;
DROP TABLE IF EXISTS diccionario;

DROP SEQUENCE IF EXISTS seq_vegetacion;
DROP SEQUENCE IF EXISTS seq_causa;
DROP SEQUENCE IF EXISTS seq_registro;

-- ==========================================
-- DEFINICIÓN DE SECUENCIAS (Para IDs autoincrementales)
-- ==========================================
CREATE SEQUENCE seq_vegetacion;
CREATE SEQUENCE seq_causa;
CREATE SEQUENCE seq_registro;

-- ==========================================
-- NIVEL 1: ENTIDADES PADRE (INDEPENDIENTES)
-- ==========================================

CREATE TABLE diccionario ( 
    id_variable VARCHAR PRIMARY KEY, 
    fuente VARCHAR NOT NULL,
    nombre_completo VARCHAR NOT NULL,
    unidad_de_medida VARCHAR        
);

CREATE TABLE estado (
    id_clave_ent INTEGER PRIMARY KEY, 
    region VARCHAR,
    estado VARCHAR 
);

CREATE TABLE vegetacion (
    id_vegetacion INTEGER PRIMARY KEY DEFAULT nextval('seq_vegetacion'),
    regimen_del_fuego VARCHAR NOT NULL,
    tipo_de_vegetacion VARCHAR NOT NULL
);

CREATE TABLE causa (
    id_causa INTEGER PRIMARY KEY DEFAULT nextval('seq_causa'),
    causa VARCHAR NOT NULL,
    causa_especifica VARCHAR NOT NULL
);

-- ==========================================
-- NIVEL 2: ENTIDADES DE SEGUNDO NIVEL
-- ==========================================

CREATE TABLE municipios (
    id_cvegeo VARCHAR PRIMARY KEY,    
    id_clave_ent INTEGER NOT NULL, 
    nombre_municipio VARCHAR NOT NULL,
    FOREIGN KEY (id_clave_ent) REFERENCES estado(id_clave_ent)
);

-- ==========================================
-- NIVEL 3: LA ENTIDAD CENTRAL (INCENDIOS)
-- ==========================================

CREATE TABLE incendios (
    id_clave_inc VARCHAR PRIMARY KEY, 
    id_cvegeo VARCHAR NOT NULL,       
    id_causa INTEGER NOT NULL, 
    id_vegetacion INTEGER NOT NULL, 
    latitud FLOAT NOT NULL,
    longitud FLOAT NOT NULL,
    fecha_inicio DATE NOT NULL,
    tipo_de_incendio VARCHAR NOT NULL,
    anio INTEGER NOT NULL,            
    
    FOREIGN KEY (id_cvegeo) REFERENCES municipios(id_cvegeo),
    FOREIGN KEY (id_causa) REFERENCES causa(id_causa),
    FOREIGN KEY (id_vegetacion) REFERENCES vegetacion(id_vegetacion)
);

-- ==========================================
-- NIVEL 4: TABLAS HIJAS (DEPENDEN DE INCENDIOS)
-- ==========================================

CREATE TABLE danos (                  
    id_clave_inc VARCHAR PRIMARY KEY, 
    hojarasca FLOAT NOT NULL,
    arbustivo FLOAT NOT NULL,
    herbaceo FLOAT NOT NULL,
    arbolado_adulto FLOAT NOT NULL,
    renuevo FLOAT NOT NULL,
    tamanio VARCHAR NOT NULL,         
    FOREIGN KEY (id_clave_inc) REFERENCES incendios(id_clave_inc)
);

-- Modelo EAV para clima satelital (Manejo de Series Temporales)
CREATE TABLE climatologia (
    id_registro BIGINT PRIMARY KEY DEFAULT nextval('seq_registro'),
    id_variable VARCHAR NOT NULL,     
    id_clave_inc VARCHAR NOT NULL,    
    fecha_de_observacion DATE NOT NULL,
    resultado_numerico FLOAT NOT NULL,
    
    FOREIGN KEY (id_variable) REFERENCES diccionario(id_variable), 
    FOREIGN KEY (id_clave_inc) REFERENCES incendios(id_clave_inc) 
);