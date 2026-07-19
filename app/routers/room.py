import random
import string

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.room import Room
from app.models.user import User
from app.schemas.room import RoomCreateRequest, RoomJoinRequest
from app.utils.security import verify_access_token


router = APIRouter(
    prefix="/rooms",
    tags=["학습방"]
)

# Swagger에서 JWT 토큰을 입력받기 위한 설정
security = HTTPBearer()


# 중복되지 않는 초대 코드 생성
def create_invite_code(db: Session) -> str:
    while True:
        invite_code = "".join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=6
            )
        )

        existing_room = (
            db.query(Room)
            .filter(Room.invite_code == invite_code)
            .first()
        )

        if existing_room is None:
            return invite_code


# 학습방 목록 조회
@router.get(
    "",
    summary="학습방 목록 조회",
    description="현재 생성된 모든 학습방 목록을 조회합니다."
)
def get_rooms(db: Session = Depends(get_db)):
    rooms = (
        db.query(Room)
        .order_by(Room.created_at.desc())
        .all()
    )

    return {
        "message": "학습방 목록을 조회했습니다.",
        "count": len(rooms),
        "rooms": [
            {
                "room_id": room.room_id,
                "title": room.title,
                "invite_code": room.invite_code,
                "creator_id": room.creator_id,
                "max_members": room.max_members,
                "created_at": room.created_at
            }
            for room in rooms
        ]
    }


# 학습방 상세 조회
@router.get(
    "/{room_id}",
    summary="학습방 상세 조회",
    description="학습방 번호를 이용하여 특정 학습방의 정보를 조회합니다."
)
def get_room_detail(
    room_id: int,
    db: Session = Depends(get_db)
):
    room = (
        db.query(Room)
        .filter(Room.room_id == room_id)
        .first()
    )

    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="학습방을 찾을 수 없습니다."
        )

    return {
        "message": "학습방 상세 정보를 조회했습니다.",
        "room": {
            "room_id": room.room_id,
            "title": room.title,
            "invite_code": room.invite_code,
            "creator_id": room.creator_id,
            "max_members": room.max_members,
            "created_at": room.created_at
        }
    }


# 학습방 참여
@router.post(
    "/join",
    summary="학습방 참여",
    description="초대 코드를 입력하여 학습방에 참여합니다."
)
def join_room(
    request: RoomJoinRequest,
    db: Session = Depends(get_db)
):
    room = (
        db.query(Room)
        .filter(Room.invite_code == request.invite_code)
        .first()
    )

    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="학습방을 찾을 수 없습니다."
        )

    return {
        "message": "학습방 참여에 성공했습니다.",
        "room": {
            "room_id": room.room_id,
            "title": room.title,
            "invite_code": room.invite_code,
            "creator_id": room.creator_id,
            "max_members": room.max_members
        }
    }


# 학습방 생성
@router.post(
    "/create",
    summary="학습방 생성",
    description="로그인한 사용자가 새로운 학습방을 생성합니다."
)
def create_room(
    request: RoomCreateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    # Authorization 헤더에서 JWT 토큰 가져오기
    token = credentials.credentials

    # JWT 토큰을 확인하여 사용자 번호 가져오기
    user_id = verify_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 토큰입니다."
        )

    # 토큰에 저장된 사용자가 실제로 존재하는지 확인
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자 정보를 찾을 수 없습니다."
        )

    # 새로운 초대 코드 생성
    invite_code = create_invite_code(db)

    # 학습방 정보 생성
    new_room = Room(
        title=request.title,
        invite_code=invite_code,
        creator_id=user.id,
        max_members=request.max_members
    )

    # 데이터베이스에 학습방 저장
    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    return {
        "message": "학습방이 생성되었습니다.",
        "room": {
            "room_id": new_room.room_id,
            "title": new_room.title,
            "invite_code": new_room.invite_code,
            "creator_id": new_room.creator_id,
            "max_members": new_room.max_members,
            "created_at": new_room.created_at
        }
    }