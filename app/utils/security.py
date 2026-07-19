from datetime import datetime, timedelta, timezone
import os

import jwt
from dotenv import load_dotenv
from jwt import ExpiredSignatureError, InvalidTokenError
from pwdlib import PasswordHash


# 프로젝트 최상위의 .env 파일을 불러온다.
load_dotenv()

# 비밀번호 암호화에 사용할 객체
password_hash = PasswordHash.recommended()

# JWT 설정값
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080")
)

# 비밀키가 설정되지 않았으면 서버 실행을 중단한다.
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY가 설정되지 않았습니다.")


# 입력받은 비밀번호를 암호화한다.
def hash_password(password: str) -> str:
    return password_hash.hash(password)


# 입력한 비밀번호와 저장된 암호화 비밀번호를 비교한다.
def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return password_hash.verify(
        plain_password,
        hashed_password
    )


# 로그인한 사용자에게 발급할 JWT 토큰을 생성한다.
def create_access_token(user_id: int) -> str:
    # 토큰 만료시간 설정
    expire_time = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    # 토큰 안에 저장할 정보
    payload = {
        "sub": str(user_id),
        "exp": expire_time
    }

    # JWT 토큰 생성
    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# 전달받은 JWT 토큰을 검사하고 사용자 번호를 반환한다.
def verify_access_token(token: str) -> int | None:
    try:
        # 토큰의 서명과 만료시간을 검사한다.
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        # 토큰에 저장된 사용자 번호를 가져온다.
        user_id = payload.get("sub")

        if user_id is None:
            return None

        return int(user_id)

    except ExpiredSignatureError:
        # 토큰 사용 기간이 만료된 경우
        return None

    except (InvalidTokenError, ValueError, TypeError):
        # 토큰이 위조되었거나 사용자 번호 형식이 잘못된 경우
        return None