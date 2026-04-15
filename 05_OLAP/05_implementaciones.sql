-- asegurar esquema base
CREATE SCHEMA IF NOT EXISTS olap;

-- dim_tiempo


ALTER TABLE olap.dim_tiempo ADD COLUMN IF NOT EXISTS trimestre INTEGER;
ALTER TABLE olap.dim_tiempo ADD COLUMN IF NOT EXISTS nombre_mes VARCHAR;
ALTER TABLE olap.dim_tiempo ADD COLUMN IF NOT EXISTS estacion VARCHAR;
ALTER TABLE olap.dim_tiempo ADD COLUMN IF NOT EXISTS es_fin_semana BOOLEAN;

-- solo recalcular columnas derivadas
UPDATE olap.dim_tiempo
SET 
    trimestre = ((mes - 1) / 3) + 1,
    nombre_mes = CASE mes
        WHEN 1 THEN 'Enero'
        WHEN 2 THEN 'Febrero'
        WHEN 3 THEN 'Marzo'
        WHEN 4 THEN 'Abril'
        WHEN 5 THEN 'Mayo'
        WHEN 6 THEN 'Junio'
        WHEN 7 THEN 'Julio'
        WHEN 8 THEN 'Agosto'
        WHEN 9 THEN 'Septiembre'
        WHEN 10 THEN 'Octubre'
        WHEN 11 THEN 'Noviembre'
        WHEN 12 THEN 'Diciembre'
    END,
    estacion = CASE 
        WHEN mes IN (12,1,2) THEN 'Invierno'
        WHEN mes IN (3,4,5) THEN 'Primavera'
        WHEN mes IN (6,7,8) THEN 'Verano'
        ELSE 'Otoño'
    END
WHERE mes BETWEEN 1 AND 12;



-- dim_ubicacion

ALTER TABLE olap.dim_ubicacion ADD COLUMN IF NOT EXISTS estado VARCHAR;
ALTER TABLE olap.dim_ubicacion ADD COLUMN IF NOT EXISTS region VARCHAR;

UPDATE olap.dim_ubicacion u
SET estado = e.estado,
    region = e.region
FROM (
    SELECT id_cvegeo, MAX(id_clave_ent) AS id_clave_ent
    FROM main.municipios
    GROUP BY id_cvegeo
) m
JOIN main.estado e 
    ON m.id_clave_ent = e.id_clave_ent
WHERE u.id_cvegeo = m.id_cvegeo;



-- dim_vegetacion

ALTER TABLE olap.dim_vegetacion ADD COLUMN IF NOT EXISTS riesgo_vegetacion FLOAT;

UPDATE olap.dim_vegetacion
SET riesgo_vegetacion =
    CASE 
        WHEN LOWER(tipo_de_vegetacion) LIKE '%bosque%' THEN 0.9
        WHEN LOWER(tipo_de_vegetacion) LIKE '%selva%' THEN 0.95
        WHEN LOWER(tipo_de_vegetacion) LIKE '%pastizal%' THEN 0.7
        ELSE 0.5
    END;


-- Índice de riesgo climático

UPDATE olap.fact_incendios f
SET riesgo = 
    CASE 
        WHEN c.temperatura_prom IS NULL 
         AND c.viento_prom IS NULL 
         AND c.humedad_prom IS NULL 
        THEN NULL
        ELSE 
            COALESCE(c.temperatura_prom,0) * 0.4 +
            COALESCE(c.viento_prom,0) * 0.3 -
            COALESCE(c.humedad_prom,0) * 0.2
    END
FROM olap.fact_clima c
WHERE f.id_clave_inc = c.id_clave_inc
AND f.riesgo IS NULL;

-- indice de severidad 

ALTER TABLE olap.fact_incendios ADD COLUMN IF NOT EXISTS indice_severidad FLOAT;

UPDATE olap.fact_incendios
SET indice_severidad =
    COALESCE(superficie_total, 0) * 0.5 +
    COALESCE(duracion_dias, 0) * 0.3 +
    COALESCE(superficie_arbolado, 0) * 0.2
WHERE indice_severidad IS NULL;

-- tiempo completo

DROP VIEW IF EXISTS olap.vw_cubo_tiempo;

CREATE OR REPLACE VIEW olap.vw_cubo_tiempo AS
SELECT 
    t.anio,
    t.trimestre,
    t.mes,
    t.nombre_mes,
    COUNT(*) AS incendios,
    AVG(f.indice_severidad) AS severidad,
    SUM(f.superficie_total) AS superficie
FROM olap.fact_incendios f
JOIN olap.dim_tiempo t 
    ON f.fecha_inicio = t.fecha
GROUP BY t.anio, t.trimestre, t.mes, t.nombre_mes
ORDER BY t.anio, t.mes;

-- cubo geografico

DROP VIEW IF EXISTS olap.vw_cubo_geografico;

CREATE OR REPLACE VIEW olap.vw_cubo_geografico AS
SELECT 
    u.estado,
    u.municipio,
    COUNT(*) AS incendios,
    AVG(f.indice_severidad) AS severidad,
    SUM(COALESCE(f.superficie_total,0)) AS superficie
FROM olap.fact_incendios f
JOIN olap.dim_ubicacion u 
    ON f.id_cvegeo = u.id_cvegeo
GROUP BY u.estado, u.municipio
ORDER BY incendios DESC;

-- clima contra incendios

DROP VIEW IF EXISTS olap.vw_clima_riesgo;

CREATE OR REPLACE VIEW olap.vw_clima_riesgo AS
SELECT 
    ROUND(c.temperatura_prom) AS temp,
    ROUND(c.viento_prom,1) AS viento,
    COUNT(*) AS incendios,
    AVG(f.indice_severidad) AS severidad
FROM olap.fact_incendios f
JOIN olap.fact_clima c 
    ON f.id_clave_inc = c.id_clave_inc
GROUP BY temp, viento
ORDER BY incendios DESC;

-- Impacto poblacional 

DROP VIEW IF EXISTS olap.vw_impacto_poblacion;

CREATE OR REPLACE VIEW olap.vw_impacto_poblacion AS
SELECT 
    u.municipio,
    AVG(d.pob_total) AS poblacion,
    COUNT(f.id_clave_inc) AS incendios,
    COUNT(f.id_clave_inc) * 1000.0 / NULLIF(AVG(d.pob_total),0) AS impacto
FROM olap.fact_incendios f
JOIN olap.dim_ubicacion u ON f.id_cvegeo = u.id_cvegeo
LEFT JOIN main.demografia d ON f.id_cvegeo = d.id_cvegeo
GROUP BY u.municipio
ORDER BY impacto DESC;