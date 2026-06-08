"""Migración: añade created_by_id a incidents + tabla incident_notes."""

from app.config import get_settings
from app.database import engine
from sqlalchemy import text

EXISTING_COL = text(
    "ALTER TABLE incidents "
    "ADD COLUMN IF NOT EXISTS created_by_id UUID REFERENCES employees(id)"
)

NEW_TABLE = text(
    """
    CREATE TABLE IF NOT EXISTS incident_notes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
        author_id UUID REFERENCES employees(id),
        author_name VARCHAR(200),
        content VARCHAR(5000) NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT now()
    )
    """
)

IDX = text(
    "CREATE INDEX IF NOT EXISTS ix_incident_notes_incident_id ON incident_notes(incident_id)"
)


def run() -> None:
    with engine.begin() as conn:
        conn.execute(EXISTING_COL)
        conn.execute(NEW_TABLE)
        conn.execute(IDX)
    print("✅ Migración incident_notes_v1 completada.")


if __name__ == "__main__":
    run()
