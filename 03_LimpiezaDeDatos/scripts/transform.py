import duckdb

def unificar_municipios(con):
    print("   - [Transform] Unificando catalogo de municipios para Edomex (Clave 15)...")
    
    # Insertar registros que ya cuentan con 5 digitos
    con.execute("""
        INSERT INTO main.municipios 
        SELECT * FROM source_db.municipios WHERE LENGTH(id_cvegeo) = 5 
        ON CONFLICT DO NOTHING
    """)
    
    # Estandarizar longitud a 5 digitos forzando la clave 15 (Edomex)
    con.execute("""
        INSERT INTO main.municipios (id_cvegeo, id_clave_ent, nombre_municipio)
        SELECT '15' || LPAD(SUBSTR(id_cvegeo, 1, LENGTH(id_cvegeo)-2), 3, '0'), 15, nombre_municipio
        FROM source_db.municipios WHERE LENGTH(id_cvegeo) < 5
        ON CONFLICT DO NOTHING
    """)
    
    # Crear placeholders para IDs huerfanos detectados en incendios
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
    print("   - [Transform] Migrando incendios con normalizacion de claves geograficas...")
    con.execute("""
        INSERT INTO main.incendios
        SELECT 
            id_clave_inc, 
            CASE WHEN LENGTH(id_cvegeo) < 5 THEN '15' || LPAD(SUBSTR(id_cvegeo, 1, LENGTH(id_cvegeo)-2), 3, '0') ELSE id_cvegeo END,
            id_causa, id_vegetacion, latitud, longitud, fecha_inicio, tipo_de_incendio, anio
        FROM source_db.incendios
        ON CONFLICT DO NOTHING
    """)

def eliminar_duplicados_fisicos(con):
    print("   - [Cleaning] Eliminando duplicados fisicos por id_clave_inc...")
    # Conservar unicamente el primer registro detectado por cada ID
    con.execute("""
        DELETE FROM main.incendios 
        WHERE rowid NOT IN (
            SELECT min(rowid) 
            FROM main.incendios 
            GROUP BY id_clave_inc
        )
    """)

def estandarizar_categoricos(con):
    print("   - [Cleaning] Estandarizando formato de etiquetas de texto...")
    
    mapeo_estandarizar = {
        'diccionario': ['fuente', 'nombre_completo', 'unidad_de_medida'],
        'estado': ['region', 'estado'],
        'vegetacion': ['regimen_del_fuego', 'tipo_de_vegetacion'],
        'causa': ['causa', 'causa_especifica'],
        'municipios': ['nombre_municipio'],
        'incendios': ['tipo_de_incendio'], 
        'demografia': ['sexo'],             
        'danos': ['tamanio']
    }

    for tabla, columnas in mapeo_estandarizar.items():
        for col in columnas:
            query = f"""
                UPDATE main.{tabla} SET "{col}" = 
                LOWER(TRIM(
                    regexp_replace(
                    regexp_replace(
                    regexp_replace(
                    regexp_replace(
                    regexp_replace(
                    regexp_replace("{col}", '[áÁ]', 'a', 'g'),
                                           '[éÉ]', 'e', 'g'),
                                           '[íÍ]', 'i', 'g'),
                                           '[óÓ]', 'o', 'g'),
                                           '[úÚüÜ]', 'u', 'g'),
                                           '[ñÑ]', 'n', 'g')
                ))
                WHERE "{col}" IS NOT NULL;
            """
            try:
                con.execute(query)
            except Exception as e:
                print(f"      - [Error] Falla en normalizacion de {tabla}.{col}: {e}")

def neutralizar_inconsistencias(con):
    print("   - [EDA Prep] Neutralizando valores ilogicos a NULL/0...")

    # A. Tiempos invalidos
    con.execute("""
        UPDATE main.operaciones 
        SET fecha_termino = NULL, hora_llegada = NULL, duracion_hhmm = NULL
        WHERE id_clave_inc IN (
            SELECT o.id_clave_inc FROM main.operaciones o
            JOIN main.incendios i ON o.id_clave_inc = i.id_clave_inc
            WHERE o.fecha_termino < i.fecha_inicio 
               OR (o.fecha_termino = i.fecha_inicio AND o.hora_llegada < o.hora_deteccion)
        )
    """)

    # B. Coordenadas fuera de rango nacional
    con.execute("""
        UPDATE main.incendios 
        SET latitud = NULL, longitud = NULL
        WHERE (latitud NOT BETWEEN 14 AND 33 OR longitud NOT BETWEEN -118 AND -86)
    """)

    # C. Hectareas con valores negativos
    con.execute("""
        UPDATE main.danos SET 
            hojarasca = CASE WHEN hojarasca < 0 THEN 0 ELSE hojarasca END,
            arbustivo = CASE WHEN arbustivo < 0 THEN 0 ELSE arbustivo END,
            herbaceo = CASE WHEN herbaceo < 0 THEN 0 ELSE herbaceo END,
            arbolado_adulto = CASE WHEN arbolado_adulto < 0 THEN 0 ELSE arbolado_adulto END,
            renuevo = CASE WHEN renuevo < 0 THEN 0 ELSE renuevo END
    """)

    # D. Poblacion inconsistente
    con.execute("UPDATE main.demografia SET pob_total = NULL WHERE pob_total <= 0")

def ejecutar_limpieza_texto(con):
    print("   - [Cleaning] Etiquetando nulos en variables de texto descriptivo...")
    
    plan_limpieza = {
        'causa': ['causa', 'causa_especifica'],
        'danos': ['tamanio'],
        'demografia': ['sexo'],
        'diccionario': ['fuente', 'nombre_completo', 'unidad_de_medida'],
        'estado': ['region', 'estado'],
        'incendios': ['tipo_de_incendio'],
        'municipios': ['nombre_municipio'],
        'vegetacion': ['regimen_del_fuego', 'tipo_de_vegetacion']
    }

    for tabla, columnas in plan_limpieza.items():
        for col in columnas:
            con.execute(f"""
                UPDATE main.{tabla} 
                SET "{col}" = 'no especificado' 
                WHERE "{col}" IS NULL
            """)