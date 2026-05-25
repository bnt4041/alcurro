"""Documentos de empresa para firma en inbound + envelope en alta."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def column_exists(conn, table: str, column: str) -> bool:
    cols = [c["name"] for c in inspect(conn).get_columns(table)]
    return column in cols


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        if not column_exists(conn, "clock_settings", "inbound_signature_delivery_ids"):
            conn.execute(
                text(
                    """
                    ALTER TABLE clock_settings
                    ADD COLUMN inbound_signature_delivery_ids JSONB NOT NULL DEFAULT '[]'::jsonb
                    """
                )
            )
            print("Columna clock_settings.inbound_signature_delivery_ids creada.")

        if not column_exists(
            conn, "employee_inbound_documents", "signature_envelope_id"
        ):
            conn.execute(
                text(
                    """
                    ALTER TABLE employee_inbound_documents
                    ADD COLUMN signature_envelope_id UUID
                        REFERENCES signature_envelopes(id)
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_employee_inbound_sig_env
                    ON employee_inbound_documents (signature_envelope_id)
                    """
                )
            )
            print("Columna employee_inbound_documents.signature_envelope_id creada.")

    print("Migración clock_settings v2 OK.")


if __name__ == "__main__":
    main()
