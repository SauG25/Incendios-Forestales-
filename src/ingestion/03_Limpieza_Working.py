# src/ingestion/02b_Limpieza_Working.py
"""
Aplica limpieza de datos sobre el esquema 'working' de IncendiosForestales_V2.db.

REGLA PRINCIPAL: Los valores incorrectos se convierten a NULL, nunca a 0 ni a otro valor.
  - NULL = "no sé" → honesto, el motor lo ignora en cálculos
  - 0    = "cero"  → miente, contamina promedios y el modelo aprende mal

Orden de limpieza:
  1. Textos categóricos  → normalización (minúsculas, sin acentos, sin espacios extra)
  2. Incendios           → coordenadas fuera del EdoMex, año inconsistente
  3. Operaciones         → fechas y horas imposibles
  4. Daños               → hectáreas negativas
  5. Demografía          → población negativa (rangos de edad se imputan en el pipeline)
  6. Climatología        → ruido -999.0

No modifica el esquema 'raw'.
"""

import sys
import os
import duckdb

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from config.config import V2_DB

# -------------------------------------------------------------------
# UTILIDAD: ejecutar un UPDATE e imprimir cuántas filas se afectaron
# -------------------------------------------------------------------
def _aplicar_regla(con, descripcion: str, query: str) -> int:
    """Ejecuta un UPDATE y reporta filas afectadas. Retorna el conteo."""
    resultado = con.execute(query).fetchone()
    n = resultado[0] if resultado and resultado[0] else 0
    if n > 0:
        print(f"   ✓ {descripcion}: {n:,} registros corregidos.")
    return n


# -------------------------------------------------------------------
# 1. TEXTOS CATEGÓRICOS
#    Aplica: minúsculas, quita acentos, recorta espacios, colapsa dobles espacios
# -------------------------------------------------------------------
def limpiar_textos_categoricos(con):
    print("\n1. Normalizando variables categóricas...")

    columnas = [
        ('estado',      'region'),
        ('estado',      'estado'),
        ('vegetacion',  'regimen_del_fuego'),
        ('vegetacion',  'tipo_de_vegetacion'),
        ('causa',       'causa'),
        ('causa',       'causa_especifica'),
        ('municipios',  'nombre_municipio'),
        ('incendios',   'tipo_de_incendio'),
        ('danos',       'tamanio'),
        ('demografia',  'sexo'),
        ('diccionario', 'fuente'),
        ('diccionario', 'nombre_completo'),
        # 'diccionario.unidad_de_medida' excluida intencionalmente
    ]

    # Expresión de normalización reutilizable
    def expr_normalizar(col):
        return f"""
            LOWER(TRIM(
                REGEXP_REPLACE(
                    STRIP_ACCENTS("{col}"),
                    ' +', ' ', 'g'
                )
            ))
        """

    total = 0
    for tabla, col in columnas:
        norm = expr_normalizar(col)
        n = _aplicar_regla(
            con,
            f"{tabla}.{col}",
            f"""
                UPDATE working.{tabla}
                SET "{col}" = {norm}
                WHERE "{col}" IS NOT NULL
                  AND "{col}" <> {norm}
            """
        )
        total += n

    print(f"   Total registros normalizados: {total:,}")


# -------------------------------------------------------------------
# 2. INCENDIOS
#    - Coordenadas fuera del Estado de México → NULL
#    - Coordenadas en (0, 0) → NULL  (error de sensor frecuente)
#    - Año inconsistente con fecha_inicio → se corrige (no se anula)
# -------------------------------------------------------------------
def limpiar_incendios(con):
    print("\n2. Limpiando tabla incendios...")

    # Coordenadas fuera del EdoMex o en el origen (0,0)
    # Latitud válida:  18.7° – 20.3° N
    # Longitud válida: -100.6° – -98.4° O
    _aplicar_regla(con, "Coordenadas fuera del EdoMex o en (0,0)", """
        UPDATE working.incendios
        SET latitud  = NULL,
            longitud = NULL
        WHERE latitud  IS NOT NULL
          AND (
                latitud  NOT BETWEEN 18.7 AND 20.3
             OR longitud NOT BETWEEN -100.6 AND -98.4
             OR latitud  = 0
             OR longitud = 0
          )
    """)

    # Año que no coincide con fecha_inicio → corregir, no anular
    # (el año correcto siempre se puede derivar de la fecha)
    _aplicar_regla(con, "Año inconsistente con fecha_inicio (corregido)", """
        UPDATE working.incendios
        SET anio = EXTRACT(YEAR FROM fecha_inicio)::INTEGER
        WHERE anio <> EXTRACT(YEAR FROM fecha_inicio)::INTEGER
    """)


# -------------------------------------------------------------------
# 3. OPERACIONES
#    Todos los errores → NULL (nunca borrar la fila del incendio)
# -------------------------------------------------------------------
def limpiar_operaciones(con):
    print("\n3. Limpiando tabla operaciones...")

    reglas = [
        (
            "Fecha de término anterior a fecha de inicio del incendio",
            """
            UPDATE working.operaciones
            SET fecha_termino = NULL
            WHERE id_clave_inc IN (
                SELECT o.id_clave_inc
                FROM working.operaciones o
                JOIN working.incendios i ON o.id_clave_inc = i.id_clave_inc
                WHERE o.fecha_termino < i.fecha_inicio
            )
            """
        ),
        (
            "Fecha de término en el futuro",
            """
            UPDATE working.operaciones
            SET fecha_termino = NULL
            WHERE fecha_termino > CURRENT_DATE
            """
        ),
        (
            "Hora de llegada anterior a hora de detección",
            """
            UPDATE working.operaciones
            SET hora_llegada = NULL
            WHERE hora_llegada < hora_deteccion
            """
        ),
        (
            "Duración en días negativa",
            """
            UPDATE working.operaciones
            SET duracion_dias = NULL
            WHERE duracion_dias < 0
            """
        ),
        (
            "Duración hhmm negativa",
            """
            UPDATE working.operaciones
            SET duracion_hhmm = NULL
            WHERE duracion_hhmm < INTERVAL '0' SECOND
            """
        ),
    ]

    for descripcion, query in reglas:
        _aplicar_regla(con, descripcion, query)


# -------------------------------------------------------------------
# 4. DAÑOS
#    Sin correcciones necesarias: análisis previo no encontró
#    valores negativos ni imposibles en las coberturas.
# -------------------------------------------------------------------
def limpiar_danos(con):
    print("\n4. Daños: sin valores imposibles detectados, se omite limpieza.")


# -------------------------------------------------------------------
# 5. DEMOGRAFÍA
#    Sin correcciones necesarias: análisis previo no encontró
#    valores negativos en pob_total ni en rangos de edad.
#    La imputación de NULLs se realizará en el pipeline.
# -------------------------------------------------------------------
def limpiar_demografia(con):
    print("\n5. Demografía: sin valores imposibles detectados, se omite limpieza.")


# -------------------------------------------------------------------
# 6. CLIMATOLOGÍA
#    -999.0 es el código universal de sensor roto → NULL
#    Las variables con alto % de NULL se descartan en el pipeline,
#    no aquí, porque esa es una decisión del modelo.
# -------------------------------------------------------------------
def limpiar_climatologia(con):
    print("\n6. Limpiando tabla climatología...")

    _aplicar_regla(
        con,
        "Ruido de sensor (-999.0)",
        """
        UPDATE working.climatologia
        SET resultado_numerico = NULL
        WHERE resultado_numerico = -999.0
        """
    )


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
def main():
    if not os.path.exists(V2_DB):
        print(f"Error: base de datos no encontrada en {V2_DB}")
        return

    con = duckdb.connect(V2_DB)
    print("=== INICIO DE LIMPIEZA — ESQUEMA WORKING ===")
    print("Regla: valores incorrectos → NULL. Nunca se borra una fila.")

    try:
        limpiar_textos_categoricos(con)
        limpiar_incendios(con)
        limpiar_operaciones(con)
        limpiar_danos(con)
        limpiar_demografia(con)
        limpiar_climatologia(con)

        con.execute("CHECKPOINT")
        print("\n=== LIMPIEZA COMPLETADA Y GUARDADA ===")
        print("Siguiente paso: análisis de outliers y anomalías sobre los valores reales.")

    except Exception as e:
        print(f"\nError durante la limpieza: {e}")
        raise
    finally:
        con.close()


if __name__ == "__main__":
    main()