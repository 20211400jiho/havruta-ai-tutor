"""Apply the small idempotent schema upgrade used by the integrated MVP."""

import secrets
import string

from sqlalchemy import inspect, text

from app.database.connection import create_tables, engine


def column_names(table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def unique_names(table: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in inspect(engine).get_unique_constraints(table)
        if constraint.get("name")
    }


def migrate() -> None:
    # Fresh Railway databases need all current tables; create_all is idempotent.
    # Existing databases then receive the legacy column/constraint upgrades below.
    create_tables()
    with engine.begin() as connection:
        if "grade" not in column_names("users"):
            connection.execute(text("ALTER TABLE users ADD COLUMN grade VARCHAR(50) NULL AFTER name"))

        if "unit_code" not in column_names("chat_sessions"):
            connection.execute(
                text("ALTER TABLE chat_sessions ADD COLUMN unit_code VARCHAR(100) NULL AFTER topic")
            )

        room_columns = column_names("learning_rooms")
        if "invite_code" not in room_columns:
            connection.execute(text("ALTER TABLE learning_rooms ADD COLUMN invite_code VARCHAR(10) NULL AFTER owner_id"))
        if "max_members" not in room_columns:
            connection.execute(text("ALTER TABLE learning_rooms ADD COLUMN max_members INT NOT NULL DEFAULT 2 AFTER invite_code"))

        room_ids = connection.execute(text("SELECT id FROM learning_rooms WHERE invite_code IS NULL")).scalars().all()
        alphabet = string.ascii_uppercase + string.digits
        for room_id in room_ids:
            while True:
                code = "".join(secrets.choice(alphabet) for _ in range(6))
                exists = connection.execute(
                    text("SELECT 1 FROM learning_rooms WHERE invite_code = :code"), {"code": code}
                ).first()
                if not exists:
                    connection.execute(
                        text("UPDATE learning_rooms SET invite_code = :code WHERE id = :room_id"),
                        {"code": code, "room_id": room_id},
                    )
                    break
        connection.execute(text("ALTER TABLE learning_rooms MODIFY invite_code VARCHAR(10) NOT NULL"))

        constraints = unique_names("learning_rooms")
        if "uq_learning_rooms_invite_code" not in constraints:
            connection.execute(
                text("ALTER TABLE learning_rooms ADD CONSTRAINT uq_learning_rooms_invite_code UNIQUE (invite_code)")
            )

        if "uq_room_member" not in unique_names("room_members"):
            connection.execute(
                text("ALTER TABLE room_members ADD CONSTRAINT uq_room_member UNIQUE (room_id, user_id)")
            )
        if "uq_learning_records_session" not in unique_names("learning_records"):
            connection.execute(
                text("ALTER TABLE learning_records ADD CONSTRAINT uq_learning_records_session UNIQUE (session_id)")
            )
        if "uq_documents_file_path" not in unique_names("documents"):
            connection.execute(
                text("ALTER TABLE documents ADD CONSTRAINT uq_documents_file_path UNIQUE (file_path)")
            )
        if "uq_document_chunk" not in unique_names("document_chunks"):
            connection.execute(
                text("ALTER TABLE document_chunks ADD CONSTRAINT uq_document_chunk UNIQUE (document_id, chunk_index)")
            )


if __name__ == "__main__":
    migrate()
    print("Schema migration complete")
