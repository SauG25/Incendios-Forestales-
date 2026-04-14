import duckdb
import pandas as pd

# ==========================================
# FASE 1: MIGRACION Y TRANSFORMACION (ETL)
# ==========================================
def unificar_municipios(con):
    print("   [1/7] Migrando Municipios (Unificando a 5 digitos)...")
    con.execute("INSERT INTO main.municipios SELECT * FROM source_db.municipios WHERE LENGTH(id_cvegeo) = 5 ON CONFLICT DO NOTHING")
    con.execute("""
        INSERT INTO main.municipios (id_cvegeo, id_clave_ent, nombre_municipio)
        SELECT '15' || LPAD(SUBSTR(id_cvegeo, 1, LENGTH(id_cvegeo)-2), 3, '0'), 15, nombre_municipio
        FROM source_db.municipios WHERE LENGTH(id_cvegeo) < 5 ON CONFLICT DO NOTHING
    """)
    con.execute("""
        INSERT INTO main.municipios (id_cvegeo, id_clave_ent, nombre_municipio)
        SELECT DISTINCT CASE WHEN LENGTH(id_cvegeo) < 5 THEN '15' || LPAD(SUBSTR(id_cvegeo, 1, LENGTH(id_cvegeo)-2), 3, '0') ELSE id_cvegeo END,
        15, 'MUNICIPIO POR REVISAR' FROM source_db.incendios
        WHERE CASE WHEN LENGTH(id_cvegeo) < 5 THEN '15' || LPAD(SUBSTR(id_cvegeo, 1, LENGTH(id_cvegeo)-2), 3, '0') ELSE id_cvegeo END 
        NOT IN (SELECT id_cvegeo FROM main.municipios) ON CONFLICT DO NOTHING
    """)

def migrar_incendios_corregidos(con):
    print("   [1/7] Migrando Incendios desde source_db...")
    con.execute("""
        INSERT INTO main.incendios
        SELECT id_clave_inc, CASE WHEN LENGTH(id_cvegeo) < 5 THEN '15' || LPAD(SUBSTR(id_cvegeo, 1, LENGTH(id_cvegeo)-2), 3, '0') ELSE id_cvegeo END,
        id_causa, id_vegetacion, latitud, longitud, fecha_inicio, tipo_de_incendio, anio
        FROM source_db.incendios ON CONFLICT DO NOTHING
    """)

# ==========================================
# FASE 2: CORRECCION GEOGRAFICA PROFUNDA
# ==========================================
def corregir_geografia_invertida(con):
    print("   [2/7] Corrigiendo claves invertidas (Ej: 10215 -> 15102)...")
    
    con.execute("""
        INSERT INTO main.municipios (id_cvegeo, id_clave_ent, nombre_municipio)
        SELECT SUBSTR(id_cvegeo, 4, 2) || LPAD(SUBSTR(id_cvegeo, 1, 3), 3, '0'), id_clave_ent, nombre_municipio
        FROM main.municipios
        WHERE id_cvegeo LIKE '%15' AND id_cvegeo NOT LIKE '15%' AND LENGTH(id_cvegeo) = 5
        ON CONFLICT DO NOTHING;
    """)

    con.execute("""
        UPDATE main.incendios SET id_cvegeo = SUBSTR(id_cvegeo, 4, 2) || LPAD(SUBSTR(id_cvegeo, 1, 3), 3, '0')
        WHERE id_cvegeo LIKE '%15' AND id_cvegeo NOT LIKE '15%' AND LENGTH(id_cvegeo) = 5;
        
        UPDATE main.demografia SET id_cvegeo = SUBSTR(id_cvegeo, 4, 2) || LPAD(SUBSTR(id_cvegeo, 1, 3), 3, '0')
        WHERE id_cvegeo LIKE '%15' AND id_cvegeo NOT LIKE '15%' AND LENGTH(id_cvegeo) = 5;
    """)

# ==========================================
# FASE 3: DEDUPLICACION SISTEMICA
# ==========================================
def deduplicar_sistemico(con):
    print("   [3/7] Eliminando duplicados logicos y fisicos en cascada...")
    
    for tabla, cols in {'causa': ['causa', 'causa_especifica'], 'vegetacion': ['regimen_del_fuego', 'tipo_de_vegetacion']}.items():
        id_col = f"id_{tabla}"
        cols_sql = ", ".join(cols)
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE mapeo AS 
            SELECT {id_col} as id_malo, FIRST_VALUE({id_col}) OVER (PARTITION BY {cols_sql} ORDER BY {id_col}) as id_bueno 
            FROM main.{tabla};
            
            UPDATE main.incendios SET {id_col} = m.id_bueno 
            FROM mapeo m WHERE main.incendios.{id_col} = m.id_malo AND m.id_malo != m.id_bueno;
            
            DELETE FROM main.{tabla} WHERE {id_col} NOT IN (SELECT id_bueno FROM mapeo);
        """)

    con.execute("""
        CREATE OR REPLACE TEMP TABLE ids_a_borrar AS 
        SELECT id_clave_inc, rowid FROM (
            SELECT id_clave_inc, rowid, ROW_NUMBER() OVER (PARTITION BY id_clave_inc ORDER BY rowid) as n
            FROM main.incendios
        ) WHERE n > 1;
    """)

    tablas_hijas = ['danos', 'operaciones', 'climatologia']
    for t in tablas_hijas:
        try:
            con.execute(f"DELETE FROM main.{t} WHERE id_clave_inc IN (SELECT id_clave_inc FROM ids_a_borrar)")
        except:
            pass

    con.execute("DELETE FROM main.incendios WHERE rowid IN (SELECT rowid FROM ids_a_borrar)")
    con.execute("DELETE FROM main.demografia WHERE rowid NOT IN (SELECT min(rowid) FROM main.demografia GROUP BY id_cvegeo, anio, sexo)")

# ==========================================
# FASE 4: ESTANDARIZACION DE TEXTO
# ==========================================
def estandarizar_y_limpiar_texto(con):
    print("   [4/7] Normalizando texto (Acentos, minusculas, nulos)...")
    mapeo_estandarizar = {
        'diccionario': ['fuente', 'nombre_completo', 'unidad_de_medida'], 'estado': ['region', 'estado'],
        'vegetacion': ['regimen_del_fuego', 'tipo_de_vegetacion'], 'causa': ['causa', 'causa_especifica'],
        'municipios': ['nombre_municipio'], 'incendios': ['tipo_de_incendio'], 'demografia': ['sexo'], 'danos': ['tamanio']
    }
    for tabla, columnas in mapeo_estandarizar.items():
        for col in columnas:
            try:
                con.execute(f"""
                    UPDATE main.{tabla} SET "{col}" = LOWER(TRIM(regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace(regexp_replace("{col}", '[áÁ]', 'a', 'g'), '[éÉ]', 'e', 'g'), '[íÍ]', 'i', 'g'), '[óÓ]', 'o', 'g'), '[úÚüÜ]', 'u', 'g'), '[ñÑ]', 'n', 'g'))) WHERE "{col}" IS NOT NULL;
                    UPDATE main.{tabla} SET "{col}" = 'no especificado' WHERE "{col}" IS NULL;
                """)
            except Exception as e:
                print(f"      - [Warning] No se pudo limpiar {tabla}.{col}: {e}")

# ==========================================
# FASE 5: NEUTRALIZACION DE INCONSISTENCIAS
# ============
def neutralizar_inconsistencias(con):
    print("   [5/7] Neutralizando valores ilogicos (Filtro Exclusivo Edomex)...")
    
    # 1. Identificamos incendios que mienten: Dicen ser del Edomex (15) pero el GPS dice otro lado
    con.execute("""
        CREATE OR REPLACE TEMP TABLE incendios_mal_ubicados AS
        -- Caso 1: Incendios con clave 15XXX que estan fuera del cuadro del Edomex
        SELECT id_clave_inc FROM main.incendios 
        WHERE id_cvegeo LIKE '15%' 
          AND (latitud NOT BETWEEN 18.35 AND 20.25 OR longitud NOT BETWEEN -100.6 AND -98.55)
        UNION
        -- Caso 2: Incendios que NO pertenecen al Estado de México (Claves que no empiezan con 15)
        SELECT id_clave_inc FROM main.incendios 
        WHERE id_cvegeo NOT LIKE '15%'
        UNION
        -- Caso 3: Errores de GPS en cero
        SELECT id_clave_inc FROM main.incendios WHERE latitud = 0 OR longitud = 0;
    """)

    # 2. Purgamos el clima falso de esos errores
    print("         * Eliminando datos climaticos de coordenadas invalidas o ajenas...")
    con.execute("DELETE FROM main.climatologia WHERE id_clave_inc IN (SELECT id_clave_inc FROM incendios_mal_ubicados)")

    # 3. Anulamos el GPS mentiroso (Salvando el registro para el conteo de hectareas municipales)
    print("         * Resguardando estadistica municipal (Anulando solo GPS corrupto)...")
    con.execute("UPDATE main.incendios SET latitud = NULL, longitud = NULL WHERE id_clave_inc IN (SELECT id_clave_inc FROM incendios_mal_ubicados)")

    # 4. Limpieza de datos negativos en Daños
    con.execute("""
        UPDATE main.danos SET hojarasca = CASE WHEN hojarasca < 0 THEN 0 ELSE hojarasca END, 
        arbustivo = CASE WHEN arbustivo < 0 THEN 0 ELSE arbustivo END, 
        herbaceo = CASE WHEN herbaceo < 0 THEN 0 ELSE herbaceo END, 
        arbolado_adulto = CASE WHEN arbolado_adulto < 0 THEN 0 ELSE arbolado_adulto END, 
        renuevo = CASE WHEN renuevo < 0 THEN 0 ELSE renuevo END;
    """)

# ==========================================
# FASE 6: PROCESAMIENTO NASA (17 Millones)
# ==========================================
def procesar_climatologia(con):
    print("   [6/7] Procesando Climatologia Satelital (Bypass de Foreign Keys)...")
    
    # 1. Neutralizar ruido NASA (-999.0 a NULL)
    con.execute("UPDATE main.climatologia SET resultado_numerico = NULL WHERE resultado_numerico = -999.0")

    # 2. Identificar variables muertas en la tabla de 17 millones
    con.execute("""
        CREATE OR REPLACE TEMP TABLE variables_a_eliminar AS 
        SELECT id_variable 
        FROM main.climatologia 
        GROUP BY id_variable 
        HAVING COUNT(resultado_numerico) = 0
    """)

    # 3. ELIMINA EL ERROR: Solo borramos los registros basura de la tabla hija.
    # Al no tocar la tabla 'diccionario', DuckDB jamas lanzara el Constraint Error.
    print("         * Eliminando registros vacios de Climatologia...")
    con.execute("""
        DELETE FROM main.climatologia 
        WHERE id_variable IN (SELECT id_variable FROM variables_a_eliminar)
    """)

    # 4. Deduplicacion fisica
    print("         * Eliminando duplicados fisicos...")
    con.execute("""
        DELETE FROM main.climatologia 
        WHERE rowid NOT IN (
            SELECT min(rowid) 
            FROM main.climatologia 
            GROUP BY id_variable, id_clave_inc, fecha_de_observacion
        )
    """)

    # 5. Interpolacion de series temporales
    print("         * Interpolando series temporales rescatables (< 10% nulos)...")
    rescatables = con.execute("""
        SELECT id_variable 
        FROM main.climatologia 
        GROUP BY id_variable 
        HAVING (COUNT(*) - COUNT(resultado_numerico)) > 0 
           AND (COUNT(*) - COUNT(resultado_numerico)) * 100.0 / COUNT(*) < 10
    """).fetchall() 
    
    for (var,) in rescatables:
        df_var = con.execute(f"SELECT * FROM main.climatologia WHERE id_variable = '{var}' ORDER BY id_clave_inc, fecha_de_observacion").df()
        
        # Interpolacion lineal por grupo de incendio
        df_var['resultado_numerico'] = df_var.groupby('id_clave_inc')['resultado_numerico'].transform(
            lambda x: x.interpolate(method='linear', limit_direction='both')
        )
        
        con.execute(f"DELETE FROM main.climatologia WHERE id_variable = '{var}'")
        con.execute("INSERT INTO main.climatologia SELECT * FROM df_var")
# ==========================================
# FASE 7: INTEGRIDAD REFERENCIAL FINAL
# ==========================================
def limpiar_huerfanos(con):
    print("   [7/7] Sello de Calidad: Eliminando registros huerfanos...")
    for t in ['danos', 'operaciones', 'climatologia']:
        try:
            con.execute(f"DELETE FROM main.{t} WHERE id_clave_inc NOT IN (SELECT id_clave_inc FROM main.incendios)")
        except:
            pass
    con.execute("DELETE FROM main.municipios WHERE id_cvegeo NOT IN (SELECT id_cvegeo FROM main.incendios) AND id_cvegeo NOT IN (SELECT id_cvegeo FROM main.demografia)")