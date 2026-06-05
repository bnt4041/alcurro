"""
Migración fichaje v2: convierte clock_ins de dos registros (ENTRADA+SALIDA)
a un único registro por jornada con entrada_at / salida_at / work_summary.
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import psycopg
from app.config import get_settings


def run() -> None:
    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:

            # 1. Añadir columnas nuevas si no existen
            cur.execute("""
                ALTER TABLE clock_ins
                    ADD COLUMN IF NOT EXISTS entrada_at  TIMESTAMPTZ,
                    ADD COLUMN IF NOT EXISTS salida_at   TIMESTAMPTZ,
                    ADD COLUMN IF NOT EXISTS work_summary TEXT
            """)
            print("Columnas entrada_at / salida_at / work_summary añadidas.")

            # 2. Copiar recorded_at → entrada_at para los registros ENTRADA
            cur.execute("""
                UPDATE clock_ins
                   SET entrada_at = recorded_at
                 WHERE record_type = 'ENTRADA'
                   AND entrada_at IS NULL
            """)
            print(f"Entradas copiadas: {cur.rowcount}")

            # 3. Emparejar cada ENTRADA con su SALIDA más próxima posterior
            cur.execute("""
                UPDATE clock_ins AS e
                   SET salida_at = s.recorded_at
                  FROM (
                      SELECT DISTINCT ON (s.employee_id, e2.id)
                             e2.id      AS entrada_id,
                             s.recorded_at
                        FROM clock_ins e2
                        JOIN clock_ins s
                          ON s.employee_id = e2.employee_id
                         AND s.record_type  = 'SALIDA'
                         AND s.recorded_at  > e2.recorded_at
                       WHERE e2.record_type = 'ENTRADA'
                       ORDER BY s.employee_id, e2.id, s.recorded_at
                  ) s
                 WHERE e.id = s.entrada_id
            """)
            print(f"Salidas emparejadas: {cur.rowcount}")

            # 4. Reasignar work_breaks: apuntar al registro de ENTRADA correcto
            #    (ya que clock_in_id podía apuntar a un ENTRADA, que se conserva)
            cur.execute("""
                UPDATE work_breaks wb
                   SET clock_in_id = e.id
                  FROM clock_ins e
                 WHERE e.employee_id = wb.employee_id
                   AND e.record_type = 'ENTRADA'
                   AND e.recorded_at <= wb.recorded_at
                   AND (e.salida_at IS NULL OR e.salida_at >= wb.recorded_at)
                   AND wb.clock_in_id IS NULL
            """)
            print(f"WorkBreaks reasignados: {cur.rowcount}")

            # 5. Para work_breaks sin clock_in_id, asignar la entrada más reciente anterior
            cur.execute("""
                UPDATE work_breaks wb
                   SET clock_in_id = sub.id
                  FROM (
                      SELECT DISTINCT ON (wb2.id)
                             wb2.id  AS break_id,
                             e.id
                        FROM work_breaks wb2
                        JOIN clock_ins e
                          ON e.employee_id = wb2.employee_id
                         AND e.record_type  = 'ENTRADA'
                         AND e.recorded_at  <= wb2.recorded_at
                       WHERE wb2.clock_in_id IS NULL
                       ORDER BY wb2.id, e.recorded_at DESC
                  ) sub
                 WHERE wb.id = sub.break_id
            """)
            print(f"WorkBreaks sin FK reasignados: {cur.rowcount}")

            # 6. Eliminar los registros de SALIDA (ya absorbidos en entrada_at/salida_at)
            cur.execute("""
                DELETE FROM clock_ins WHERE record_type = 'SALIDA'
            """)
            print(f"Registros SALIDA eliminados: {cur.rowcount}")

            # 7. SET NOT NULL en entrada_at (todos los registros restantes son entradas)
            cur.execute("""
                UPDATE clock_ins SET entrada_at = recorded_at
                 WHERE entrada_at IS NULL AND recorded_at IS NOT NULL
            """)
            cur.execute("""
                ALTER TABLE clock_ins
                    ALTER COLUMN entrada_at SET NOT NULL
            """)
            print("entrada_at NOT NULL establecido.")

            # 8. Eliminar columnas antiguas
            for col in ("record_type", "recorded_at"):
                try:
                    cur.execute(f"ALTER TABLE clock_ins DROP COLUMN IF EXISTS {col}")
                    print(f"Columna {col} eliminada.")
                except Exception as e:
                    print(f"No se pudo eliminar {col}: {e}")
                    conn.rollback()
                    return

            # 9. work_breaks.clock_in_id NOT NULL
            # Primero eliminar huérfanos sin FK asignable
            cur.execute("""
                DELETE FROM work_breaks WHERE clock_in_id IS NULL
            """)
            print(f"WorkBreaks huérfanos eliminados: {cur.rowcount}")
            cur.execute("""
                ALTER TABLE work_breaks
                    ALTER COLUMN clock_in_id SET NOT NULL
            """)
            print("work_breaks.clock_in_id NOT NULL establecido.")

        conn.commit()
        print("Migración fichaje v2 completada.")


if __name__ == "__main__":
    run()
