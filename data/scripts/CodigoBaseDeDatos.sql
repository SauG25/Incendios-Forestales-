ATTACH 'BaseDeDatos_Raw.db' AS sucia;
ATTACH 'BaseDeDatos_Working.db' AS limpia;

CREATE SCHEMA IF NOT EXISTS cruda;       -- Para los 18M de datos sucios de la API
CREATE SCHEMA IF NOT EXISTS analitica; -- Para tus tablas finales y limpias

