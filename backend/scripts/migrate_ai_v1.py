"""Tablas de configuración y uso de IA."""

import os
import sys

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://hrm:hrm_secret@localhost:5432/hrm"
)


def table_exists(conn, name: str) -> bool:
    return name in inspect(conn).get_table_names()


def main() -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        if not table_exists(conn, "ai_actions"):
            conn.execute(
                text(
                    """
                    CREATE TABLE ai_actions (
                        id UUID PRIMARY KEY,
                        code VARCHAR(50) NOT NULL UNIQUE,
                        name VARCHAR(120) NOT NULL,
                        description VARCHAR(500),
                        category VARCHAR(50) NOT NULL DEFAULT 'general',
                        sort_order INTEGER NOT NULL DEFAULT 0,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            print("Tabla ai_actions creada.")

        if not table_exists(conn, "ai_profile_actions"):
            conn.execute(
                text(
                    """
                    CREATE TABLE ai_profile_actions (
                        id UUID PRIMARY KEY,
                        action_id UUID NOT NULL REFERENCES ai_actions(id) ON DELETE CASCADE,
                        profile_key VARCHAR(50) NOT NULL,
                        enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        UNIQUE (action_id, profile_key)
                    )
                    """
                )
            )
            print("Tabla ai_profile_actions creada.")

        if not table_exists(conn, "ai_conversation_rules"):
            conn.execute(
                text(
                    """
                    CREATE TABLE ai_conversation_rules (
                        id UUID PRIMARY KEY,
                        title VARCHAR(120) NOT NULL,
                        content VARCHAR(4000) NOT NULL,
                        priority INTEGER NOT NULL DEFAULT 100,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            print("Tabla ai_conversation_rules creada.")

        if not table_exists(conn, "ai_usage_records"):
            conn.execute(
                text(
                    """
                    CREATE TABLE ai_usage_records (
                        id UUID PRIMARY KEY,
                        tenant_id UUID NOT NULL REFERENCES tenants(id),
                        profile_key VARCHAR(50),
                        action_code VARCHAR(50),
                        source VARCHAR(40) NOT NULL DEFAULT 'whatsapp',
                        model VARCHAR(80) NOT NULL DEFAULT '',
                        prompt_tokens INTEGER NOT NULL DEFAULT 0,
                        completion_tokens INTEGER NOT NULL DEFAULT 0,
                        total_tokens INTEGER NOT NULL DEFAULT 0,
                        duration_ms INTEGER NOT NULL DEFAULT 0,
                        success BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX ix_ai_usage_tenant_created ON ai_usage_records (tenant_id, created_at)"
                )
            )
            print("Tabla ai_usage_records creada.")

    # Seed catalog
    from sqlmodel import Session

    from app.database import engine as app_engine
    from app.services.ai_config_service import ensure_ai_catalog

    with Session(app_engine) as session:
        ensure_ai_catalog(session)
        session.commit()
    print("Migración IA v1 OK.")


if __name__ == "__main__":
    main()
