CREATE SCHEMA IF NOT EXISTS olap;

-- =========================
-- DIMENSION TIEMPO
-- =========================
CREATE OR REPLACE TABLE olap.dim_tiempo AS
SELECT DISTINCT
    fecha_de_observacion AS fecha,
    EXTRACT(year FROM fecha_de_observacion) AS anio,
    EXTRACT(month FROM fecha_de_observacion) AS mes,
    EXTRACT(quarter FROM fecha_de_observacion) AS trimestre
FROM main.climatologia;

-- =========================
-- DIMENSION UBICACION
-- =========================
CREATE OR REPLACE TABLE olap.dim_ubicacion AS
SELECT DISTINCT
    id_cvegeo,
    nombre_municipio AS municipio,
    SUBSTR(id_cvegeo, 1, 2) AS estado
FROM main.municipios;

-- =========================
-- DIMENSION CAUSA
-- =========================
CREATE OR REPLACE TABLE olap.dim_causa AS
SELECT
    id_causa,
    causa,
    causa_especifica
FROM main.causa;

-- =========================
-- DIMENSION VEGETACION
-- =========================
CREATE OR REPLACE TABLE olap.dim_vegetacion AS
SELECT
    id_vegetacion,
    tipo_de_vegetacion,
    regimen_del_fuego
FROM main.vegetacion;

-- =========================
-- DIMENSION TIPO INCENDIO
-- =========================
CREATE OR REPLACE TABLE olap.dim_tipo_incendio AS
SELECT DISTINCT
    tipo_de_incendio AS tipo
FROM main.incendios;

-- =========================
-- FACT INCENDIOS (principal)
-- =========================
CREATE OR REPLACE TABLE olap.fact_incendios AS
SELECT
    i.id_clave_inc,
    i.id_cvegeo,
    i.id_causa,
    i.id_vegetacion,
    i.tipo_de_incendio,
    i.fecha_inicio,
    i.anio,

    o.duracion_dias,

    d.hojarasca,
    d.arbustivo,
    d.herbaceo,
    d.arbolado_adulto,
    d.renuevo,

    1 AS num_incendios

FROM main.incendios i
LEFT JOIN main.operaciones o 
    ON i.id_clave_inc = o.id_clave_inc
LEFT JOIN main.danos d 
    ON i.id_clave_inc = d.id_clave_inc;

-- =========================
-- FACT CLIMA (AGREGADO)
-- =========================
CREATE OR REPLACE TABLE olap.fact_clima AS
SELECT
    id_clave_inc,

    AVG(CASE WHEN id_variable = 'T2M' THEN resultado_numerico END) AS temperatura_prom,
    AVG(CASE WHEN id_variable = 'WS2M' THEN resultado_numerico END) AS viento_prom,
    AVG(CASE WHEN id_variable = 'QV2M' THEN resultado_numerico END) AS humedad_prom,
    AVG(CASE WHEN id_variable LIKE '%SW%' THEN resultado_numerico END) AS radiacion_prom

FROM main.climatologia
GROUP BY id_clave_inc;