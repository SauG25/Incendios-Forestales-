-- Vista 1 Resumen anual
CREATE OR REPLACE VIEW olap.vw_resumen_anual AS
SELECT 
    t.anio,
    COUNT(*) AS total_incendios,
    AVG(f.indice_severidad) AS severidad_promedio,
    SUM(f.superficie_total) AS superficie_total_quemada
FROM olap.fact_incendios f
JOIN olap.dim_tiempo t 
    ON f.fecha_inicio = t.fecha
GROUP BY t.anio
ORDER BY t.anio;

-- Vista 2 Municipios Criticos 
CREATE OR REPLACE VIEW olap.vw_resumen_anual AS
SELECT 
    t.anio,
    COUNT(*) AS total_incendios,
    AVG(f.indice_severidad) AS severidad_promedio,
    SUM(f.superficie_total) AS superficie_total_quemada
FROM olap.fact_incendios f
JOIN olap.dim_tiempo t 
    ON f.fecha_inicio = t.fecha
GROUP BY t.anio
ORDER BY t.anio;

-- Vista 3 Clima contra incendio

CREATE OR REPLACE VIEW olap.vw_clima_impacto AS
SELECT 
    ROUND(c.temperatura_prom) AS temp,
    ROUND(c.viento_prom,1) AS viento,
    COUNT(*) AS incendios,
    AVG(f.indice_severidad) AS severidad
FROM olap.fact_incendios f
LEFT JOIN olap.fact_clima c 
    ON f.id_clave_inc = c.id_clave_inc
GROUP BY temp, viento
ORDER BY incendios DESC;