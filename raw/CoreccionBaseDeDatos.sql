-- ==========================================
-- NIVEL 1: ENTIDADES PADRE (INDEPENDIENTES)
-- ==========================================

CREATE TABLE diccionario ( 
    id_variable VARCHAR PRIMARY KEY, -- Es VARCHAR porque usamos 'T2M', 'NDVI', etc.
    fuente VARCHAR NOT NULL,
    nombre_completo VARCHAR NOT NULL,
    unidad_de_medida VARCHAR         -- Es VARCHAR porque guarda '°C', '%', etc.
);

CREATE TABLE estado (
    id_clave_ent INTEGER PRIMARY KEY, -- Se queda INT porque viene en tu CSV (ej. 29 para Tlaxcala)
    region VARCHAR,
    estado VARCHAR 
);

CREATE TABLE vegetacion (
    id_vegetacion SERIAL PRIMARY KEY, -- SERIAL hace que sea autoincremental (1, 2, 3...)
    regimen_del_fuego VARCHAR NOT NULL,
    tipo_de_vegetacion VARCHAR NOT NULL
);

CREATE TABLE causa (
    id_causa SERIAL PRIMARY KEY,      -- SERIAL para que se genere solo
    causa VARCHAR NOT NULL,
    causa_especifica VARCHAR NOT NULL
);

-- ==========================================
-- NIVEL 2: ENTIDADES DE SEGUNDO NIVEL
-- ==========================================

CREATE TABLE municipios (
    id_cvegeo VARCHAR PRIMARY KEY,    -- VARCHAR para no perder los ceros a la izquierda (ej. '09002')
    id_clave_ent INTEGER NOT NULL, 
    nombre_municipio VARCHAR NOT NULL,
    
    FOREIGN KEY (id_clave_ent) REFERENCES estado(id_clave_ent)
);

-- ==========================================
-- NIVEL 3: LA ENTIDAD CENTRAL (INCENDIOS)
-- ==========================================

CREATE TABLE incendios (
    id_clave_inc VARCHAR PRIMARY KEY, -- VARCHAR porque tus claves son del tipo '15-01-0001'
    id_cvegeo VARCHAR NOT NULL,       -- Debe coincidir con el tipo de la tabla municipios
    id_causa INTEGER NOT NULL, 
    id_vegetacion INTEGER NOT NULL, 
    latitud FLOAT NOT NULL,
    longitud FLOAT NOT NULL,
    fecha_inicio DATE NOT NULL,
    tipo_de_incendio VARCHAR NOT NULL,
    anio INTEGER NOT NULL,            -- Evitamos la 'ñ' en bases de datos
    
    FOREIGN KEY (id_cvegeo) REFERENCES municipios(id_cvegeo),
    FOREIGN KEY (id_causa) REFERENCES causa(id_causa),
    FOREIGN KEY (id_vegetacion) REFERENCES vegetacion(id_vegetacion)
);

-- ==========================================
-- NIVEL 4: TABLAS HIJAS (DEPENDEN DE INCENDIOS)
-- ==========================================

-- Tabla 1:1 (Extensión del Incendio)
CREATE TABLE danos (                  -- Evitamos la 'ñ'
    id_clave_inc VARCHAR PRIMARY KEY, -- Es PK y FK al mismo tiempo (1 a 1)
    hojarasca FLOAT NOT NULL,
    arbustivo FLOAT NOT NULL,
    herbaceo FLOAT NOT NULL,
    arbolado_adulto FLOAT NOT NULL,
    renuevo FLOAT NOT NULL,
    tamanio VARCHAR NOT NULL,         -- Evitamos la 'ñ'
    
    FOREIGN KEY (id_clave_inc) REFERENCES incendios(id_clave_inc)
);

-- Tabla 1:N (Modelo EAV para clima y vegetación satelital)
CREATE TABLE climatologia (
    id_registro SERIAL PRIMARY KEY,   -- SERIAL para que cada registro tenga un ID único automático
    id_variable VARCHAR NOT NULL,     -- Debe ser VARCHAR para coincidir con el diccionario
    id_clave_inc VARCHAR NOT NULL,    -- Debe ser VARCHAR para coincidir con la tabla incendios
    fecha_de_observacion DATE NOT NULL,
    resultado_numerico FLOAT NOT NULL,
    
    FOREIGN KEY (id_variable) REFERENCES diccionario(id_variable), 
    FOREIGN KEY (id_clave_inc) REFERENCES incendios(id_clave_inc) 
);