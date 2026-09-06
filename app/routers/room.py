import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import get_current_user
from app.models.learning import LearningRoom, RoomMember
from app.models.user import User
from app.schemas.room import RoomCreateRequest, RoomJoinRequest
from app.services.connection_manager import manager


router = APIRouter(prefix="/rooms", tags=["학습방"])
ALPHABET = string.ascii_uppercase + string.digits


def room_dict(room: LearningRoom) -> dict:
    return {
        "id": room.id,
        "title": room.title,
        "subject": room.subject,
        "grade": room.grade,
        "owner_id": room.owner_id,
        "invite_code": room.invite_code,
        "max_members": room.max_members,
        "status": room.status,
        "member_count": len(room.members),
        "created_at": room.created_at,
    }


def create_invite_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(6))
        if not db.query(LearningRoom).filter(LearningRoom.invite_code == code).first():
            return code


@router.get("")
def list_rooms(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rooms = (
        db.query(LearningRoom)
        .outerjoin(RoomMember)
        .filter(or_(LearningRoom.owner_id == user.id, RoomMember.user_id == user.id))
        .filter(LearningRoom.status == "active")
        .order_by(LearningRoom.created_at.desc())
        .distinct()
        .all()
    )
    return {"count": len(rooms), "rooms": [room_dict(room) for room in rooms]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_room(
    request: RoomCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    room = LearningRoom(
        title=request.title.strip(),
        subject=request.subject,
        grade=request.grade,
        owner_id=user.id,
        invite_code=create_invite_code(db),
        max_members=request.max_members,
    )
    db.add(room)
    db.flush()
    db.add(RoomMember(room_id=room.id, user_id=user.id))
    db.commit()
    db.refresh(room)
    return {"message": "학습방이 생성되었습니다.", "room": room_dict(room)}


@router.post("/join")
def join_room(
    request: RoomJoinRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    room = db.query(LearningRoom).filter(LearningRoom.invite_code == request.invite_code.upper()).first()
    if room is None:
        raise HTTPException(status_code=404, detail="초대 코드에 해당하는 학습방이 없습니다.")
    if room.status != "active":
        raise HTTPException(status_code=409, detail="종료된 학습방입니다.")
    existing = db.query(RoomMember).filter_by(room_id=room.id, user_id=user.id).first()
    if existing:
        return {"message": "이미 참여한 학습방입니다.", "room": room_dict(room)}
    if len(room.members) >= room.max_members:
        raise HTTPException(status_code=409, detail="학습방 정원이 가득 찼습니다.")
    db.add(RoomMember(room_id=room.id, user_id=user.id))
    db.commit()
    db.refresh(room)
    return {"message": "학습방에 참여했습니다.", "room": room_dict(room)}


@router.get("/{room_id}")
def room_detail(
    room_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    room = db.get(LearningRoom, room_id)
    if room is None or room.status != "active":
        raise HTTPException(status_code=404, detail="학습방을 찾을 수 없습니다.")
    is_member = db.query(RoomMember).filter_by(room_id=room_id, user_id=user.id).first()
    if room.owner_id != user.id and not is_member:
        raise HTTPException(status_code=403, detail="학습방 접근 권한이 없습니다.")
    result = room_dict(room)
    result["members"] = [
        {"id": member.user.id, "name": member.user.name, "role": member.user.role}
        for member in room.members
    ]
    return {"room": result}


@router.delete("/{room_id}")
async def delete_room(
    room_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    room = db.get(LearningRoom, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="학습방을 찾을 수 없습니다.")
    if room.owner_id != user.id:
        raise HTTPException(status_code=403, detail="방장만 학습방을 삭제할 수 있습니다.")
    # Preserve personal learning records and their foreign-key relationships.
    room.status = "closed"
    db.commit()
    await manager.broadcast(room_id, {"type": "room_deleted", "room_id": room_id})
    return {"message": "학습방이 삭제되었습니다. 개인 학습 기록은 유지됩니다."}
