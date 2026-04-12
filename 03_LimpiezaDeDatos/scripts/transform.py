def unificar_municipios(con):
    print("   - [Transform] Unificando catálogo de municipios (5 dígitos)...")
    
    # 1. Insertamos los que ya están correctos (5 dígitos)
    con.execute("""
        INSERT INTO main.municipios 
        SELECT * FROM source_db.municipios WHERE LENGTH(id_cvegeo) = 5 
        ON CONFLICT DO NOTHING
    """)
    
    # 2. Convertimos los de 4 dígitos a 5
    con.execute("""
        INSERT INTO main.municipios (id_cvegeo, id_clave_ent, nombre_municipio)
        SELECT '15' || LPAD(SUBSTR(id_cvegeo, 1, LENGTH(id_cvegeo)-2), 3, '0'), id_clave_ent, nombre_municipio
        FROM source_db.municipios WHERE LENGTH(id_cvegeo) < 5
        ON CONFLICT DO NOTHING
    """)
    
    # 3. EL SALVADOR: Crear placeholders para IDs huérfanos (como el 15033)
    con.execute("""
        INSERT INTO main.municipios (id_cvegeo, id_clave_ent, nombre_municipio)
        SELECT DISTINCT 
            CASE WHEN LENGTH(id_cvegeo) < 5 THEN '15' || LPAD(SUBSTR(id_cvegeo, 1, LENGTH(id_cvegeo)-2), 3, '0') ELSE id_cvegeo END,
            15, 'MUNICIPIO POR REVISAR'
        FROM source_db.incendios
        WHERE CASE WHEN LENGTH(id_cvegeo) < 5 THEN '15' || LPAD(SUBSTR(id_cvegeo, 1, LENGTH(id_cvegeo)-2), 3, '0') ELSE id_cvegeo END 
        NOT IN (SELECT id_cvegeo FROM main.municipios)
        ON CONFLICT DO NOTHING
    """)

def migrar_incendios_corregidos(con):
    print("   - [Transform] Remapeando incendios para asegurar conexión con Climatología...")
    con.execute("""
        INSERT INTO main.incendios
        SELECT 
            id_clave_inc, 
            CASE WHEN LENGTH(id_cvegeo) < 5 THEN '15' || LPAD(SUBSTR(id_cvegeo, 1, LENGTH(id_cvegeo)-2), 3, '0') ELSE id_cvegeo END,
            id_causa, id_vegetacion, latitud, longitud, fecha_inicio, tipo_de_incendio, anio
        FROM source_db.incendios
    """)

