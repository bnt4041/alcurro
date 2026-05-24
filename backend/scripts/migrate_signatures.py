"""Tablas de firma electrónica."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        tables = inspect(conn).get_table_names()

        if "signature_envelopes" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE signature_envelopes (
                        id UUID PRIMARY KEY,
                        tenant_id UUID NOT NULL REFERENCES tenants(id),
                        document_delivery_id UUID REFERENCES document_deliveries(id),
                        reference VARCHAR(32) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'borrador',
                        original_path VARCHAR(500) NOT NULL,
                        original_hash VARCHAR(64) NOT NULL,
                        signed_path VARCHAR(500),
                        signed_hash VARCHAR(64),
                        certificate_path VARCHAR(500),
                        certificate_json_path VARCHAR(500),
                        expires_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        cancelled_at TIMESTAMP,
                        cancel_reason VARCHAR(500),
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_signature_envelopes_tenant ON signature_envelopes (tenant_id)"
                )
            )
            print("Tabla signature_envelopes creada.")

        if "signature_signers" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE signature_signers (
                        id UUID PRIMARY KEY,
                        envelope_id UUID NOT NULL REFERENCES signature_envelopes(id),
                        employee_id UUID REFERENCES employees(id),
                        full_name VARCHAR(200) NOT NULL,
                        email VARCHAR(255),
                        phone VARCHAR(30),
                        id_document VARCHAR(20) NOT NULL,
                        sign_order INTEGER NOT NULL DEFAULT 1,
                        status VARCHAR(20) NOT NULL DEFAULT 'pendiente',
                        token_hash VARCHAR(64) NOT NULL,
                        token_plain VARCHAR(64),
                        otp_verified_at TIMESTAMP,
                        signed_at TIMESTAMP,
                        signature_path VARCHAR(500),
                        signer_name VARCHAR(200),
                        ip_address VARCHAR(45),
                        user_agent VARCHAR(500),
                        created_at TIMESTAMP NOT NULL,
                        CONSTRAINT uq_signer_envelope_order UNIQUE (envelope_id, sign_order)
                    )
                    """
                )
            )
            print("Tabla signature_signers creada.")

        if "signature_otps" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE signature_otps (
                        id UUID PRIMARY KEY,
                        signer_id UUID NOT NULL REFERENCES signature_signers(id),
                        code_hash VARCHAR(64) NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        attempts INTEGER NOT NULL DEFAULT 0,
                        used_at TIMESTAMP,
                        created_at TIMESTAMP NOT NULL
                    )
                    """
                )
            )
            print("Tabla signature_otps creada.")

        if "signature_events" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE signature_events (
                        id UUID PRIMARY KEY,
                        envelope_id UUID NOT NULL REFERENCES signature_envelopes(id),
                        event_type VARCHAR(50) NOT NULL,
                        payload_json TEXT NOT NULL DEFAULT '{}',
                        prev_hash VARCHAR(64),
                        event_hash VARCHAR(64) NOT NULL,
                        created_at TIMESTAMP NOT NULL
                    )
                    """
                )
            )
            print("Tabla signature_events creada.")

        if "signature_notifications" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE signature_notifications (
                        id UUID PRIMARY KEY,
                        envelope_id UUID NOT NULL REFERENCES signature_envelopes(id),
                        signer_id UUID REFERENCES signature_signers(id),
                        channel VARCHAR(20) NOT NULL,
                        event_type VARCHAR(30) NOT NULL,
                        success BOOLEAN NOT NULL DEFAULT TRUE,
                        detail VARCHAR(500),
                        created_at TIMESTAMP NOT NULL
                    )
                    """
                )
            )
            print("Tabla signature_notifications creada.")


if __name__ == "__main__":
    main()
