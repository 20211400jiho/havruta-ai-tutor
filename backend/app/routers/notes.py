from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import get_current_user
from app.models.study_content import StudyNote
from app.models.user import User


router = APIRouter(prefix="/notes", tags=["정리노트"])


def parse_sections(content: str) -> list[dict]:
    sections: list[dict] = []
    current: dict | None = None
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            current = {"title": line[3:].strip(), "items": []}
            sections.append(current)
        elif line.startswith("- ") and current is not None:
            current["items"].append(line[2:].strip())
    return sections


def note_dict(note: StudyNote, include_content: bool = True) -> dict:
    result = {
        "id": note.id,
        "session_id": note.session_id,
        "title": note.title,
        "subject": note.subject,
        "created_at": note.created_at,
        "updated_at": note.updated_at,
    }
    if include_content:
        result["content"] = note.content
        result["sections"] = parse_sections(note.content)
    return result


@router.get("")
def list_notes(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    notes = db.query(StudyNote).filter(StudyNote.user_id == user.id).order_by(StudyNote.created_at.desc()).all()
    return {"count": len(notes), "notes": [note_dict(note, False) for note in notes]}


@router.get("/{note_id}")
def get_note(note_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    note = db.get(StudyNote, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="정리노트를 찾을 수 없습니다.")
    if note.user_id != user.id:
        raise HTTPException(status_code=403, detail="정리노트 접근 권한이 없습니다.")
    return {"note": note_dict(note)}
