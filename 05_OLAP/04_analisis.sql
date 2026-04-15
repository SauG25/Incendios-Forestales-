-- Jerarquias 

CREATE OR REPLACE VIEW olap.vw_jerarquia_tiempo AS
SELECT 
    t.anio,
    t.mes,
    COUNT(*) AS incendios
FROM olap.fact_incendios f
JOIN olap.dim_tiempo t 
    ON f.fecha_inicio = t.fecha
GROUP BY t.anio, t.mes
ORDER BY t.anio, t.mes;

-- Indice de riesgo

ALTER TABLE olap.fact_incendios 
ADD COLUMN riesgo FLOAT;

UPDATE olap.fact_incendios f
SET riesgo = (
    COALESCE(c.temperatura_prom,0) * 0.4 +
    COALESCE(c.viento_prom,0) * 0.3 +
    COALESCE(c.humedad_prom,0) * 0.3
)
FROM olap.fact_clima c
WHERE f.id_clave_inc = c.id_clave_inc;

-- Densidad de incendios por población

CREATE OR REPLACE VIEW olap.vw_riesgo_poblacional AS
SELECT 
    u.municipio,
    COUNT(f.id_clave_inc) AS incendios,
    AVG(d.pob_total) AS poblacion,
    COUNT(f.id_clave_inc) / NULLIF(AVG(d.pob_total),0) AS incendios_por_habitante
FROM olap.fact_incendios f
JOIN olap.dim_ubicacion u ON f.id_cvegeo = u.id_cvegeo
LEFT JOIN main.demografia d ON f.id_cvegeo = d.id_cvegeo
GROUP BY u.municipio
ORDER BY incendios_por_habitante DESC;

-- Municipios críticos

CREATE OR REPLACE VIEW olap.vw_top_riesgo AS
SELECT 
    u.municipio,
    COUNT(*) AS incendios,
    AVG(f.indice_severidad) AS severidad,
    AVG(c.temperatura_prom) AS temperatura
FROM olap.fact_incendios f
JOIN olap.dim_ubicacion u ON f.id_cvegeo = u.id_cvegeo
LEFT JOIN olap.fact_clima c ON f.id_clave_inc = c.id_clave_inc
GROUP BY u.municipio
HAVING COUNT(*) > 100
ORDER BY severidad DESC;
