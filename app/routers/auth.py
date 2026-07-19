from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

# 회원가입과 로그인 요청 데이터 형식
from app.schemas.auth import SignupRequest, LoginRequest

# 데이터베이스 연결
from app.database.database import get_db

# 사용자 테이블
from app.models.user import User

# 비밀번호 처리와 JWT 토큰 관련 함수
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_access_token
)


# Swagger에서 Bearer 토큰을 입력받기 위한 설정
bearer_scheme = HTTPBearer()


# 회원가입과 로그인 API를 관리하는 Router
router = APIRouter(
    prefix="/auth",
    tags=["사용자 관리"]
)


# 회원가입 API
@router.post(
    "/signup",
    summary="회원가입",
    description="이메일, 비밀번호, 이름, 학년 정보를 받아 회원가입을 처리합니다."
)
def signup(
    request: SignupRequest,
    db: Session = Depends(get_db)
):
    # 이미 가입된 이메일인지 확인
    existing_user = db.query(User).filter(
        User.email == request.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="이미 가입된 이메일입니다."
        )

    # 비밀번호를 암호화하여 사용자 정보 생성
    new_user = User(
        email=request.email,
        password=hash_password(request.password),
        name=request.name,
        grade=request.grade
    )

    # 사용자 정보를 데이터베이스에 저장
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "회원가입이 완료되었습니다.",
        "user_id": new_user.id,
        "email": new_user.email,
        "name": new_user.name,
        "grade": new_user.grade
    }


# 로그인 API
@router.post(
    "/login",
    summary="로그인",
    description="이메일과 비밀번호를 확인하고 로그인 토큰을 발급합니다."
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    # 입력한 이메일로 사용자 조회
    user = db.query(User).filter(
        User.email == request.email
    ).first()

    # 가입되지 않은 이메일인 경우
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="이메일 또는 비밀번호가 올바르지 않습니다."
        )

    # 입력한 비밀번호가 일치하지 않는 경우
    if not verify_password(
        request.password,
        user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="이메일 또는 비밀번호가 올바르지 않습니다."
        )

    # 로그인한 사용자의 JWT 토큰 생성
    access_token = create_access_token(user.id)

    return {
        "message": "로그인에 성공했습니다.",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "grade": user.grade
        }
    }


# 현재 로그인한 사용자 정보 조회 API
@router.get(
    "/users/me",
    summary="내 정보 조회",
    description="JWT 토큰을 확인하여 현재 로그인한 사용자의 정보를 반환합니다."
)
def get_my_information(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    # Authorization 헤더에서 JWT 토큰을 가져온다.
    token = credentials.credentials

    # 토큰을 검증하고 토큰에 저장된 사용자 번호를 가져온다.
    user_id = verify_access_token(token)

    # 토큰이 만료되었거나 올바르지 않은 경우
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="유효하지 않거나 만료된 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # 토큰의 사용자 번호로 사용자 정보를 조회한다.
    user = db.query(User).filter(
        User.id == user_id
    ).first()

    # 사용자 정보가 존재하지 않는 경우
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="사용자 정보를 찾을 수 없습니다."
        )

    return {
        "message": "사용자 정보를 불러왔습니다.",
        "user": {
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "grade": user.grade
        }
    }