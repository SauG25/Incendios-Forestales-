-- =========================================
-- ENRIQUECIMIENTO DEL CUBO OLAP
-- =========================================

--  Nuevas columnas
ALTER TABLE olap.fact_incendios ADD COLUMN IF NOT EXISTS superficie_total FLOAT;
ALTER TABLE olap.fact_incendios ADD COLUMN IF NOT EXISTS superficie_arbolado FLOAT;
ALTER TABLE olap.fact_incendios ADD COLUMN IF NOT EXISTS superficie_herbacea FLOAT;
ALTER TABLE olap.fact_incendios ADD COLUMN IF NOT EXISTS duracion_dias INTEGER;
ALTER TABLE olap.fact_incendios ADD COLUMN IF NOT EXISTS indice_severidad FLOAT;

--  Poblar datos
UPDATE olap.fact_incendios f
SET 
    superficie_arbolado = d.arbolado_adulto,
    superficie_herbacea = d.herbaceo,
    superficie_total = COALESCE(d.arbolado_adulto,0) 
                     + COALESCE(d.herbaceo,0)
                     + COALESCE(d.arbustivo,0),
    duracion_dias = o.duracion_dias
FROM main.danos d
LEFT JOIN main.operaciones o 
    ON d.id_clave_inc = o.id_clave_inc
WHERE f.id_clave_inc = d.id_clave_inc;

--  Índice de severidad
UPDATE olap.fact_incendios
SET indice_severidad =
    (COALESCE(superficie_total,0) * 0.6) +
    (COALESCE(duracion_dias,0) * 0.4);