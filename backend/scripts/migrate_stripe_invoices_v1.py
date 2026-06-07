"""Añade columnas de factura PDF a stripe_payments."""
import os
import psycopg

DB = os.environ.get("DATABASE_URL", "postgresql+psycopg://hrm:hrm@localhost:5432/hrm")
# psycopg usa DSN sin el prefijo sqlmodel
DSN = DB.replace("postgresql+psycopg://", "postgresql://")

STMTS = [
    "ALTER TABLE stripe_payments ADD COLUMN IF NOT EXISTS invoice_pdf_url TEXT",
    "ALTER TABLE stripe_payments ADD COLUMN IF NOT EXISTS invoice_url TEXT",
    "ALTER TABLE stripe_payments ADD COLUMN IF NOT EXISTS invoice_number VARCHAR(50)",
]

if __name__ == "__main__":
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            for stmt in STMTS:
                cur.execute(stmt)
                print(f"OK: {stmt[:60]}")
        conn.commit()
    print("Migración stripe_invoices_v1 completada.")
