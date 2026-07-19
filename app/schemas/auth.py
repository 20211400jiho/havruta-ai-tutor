from pydantic import BaseModel, EmailStr


# -------------------------------
# 회원가입 요청 데이터
# -------------------------------
class SignupRequest(BaseModel):

    # 이메일
    email: EmailStr

    # 비밀번호
    password: str

    # 이름
    name: str

    # 학년
    grade: int


# -------------------------------
# 로그인 요청 데이터
# -------------------------------
class LoginRequest(BaseModel):

    # 이메일
    email: EmailStr

    # 비밀번호
    password: str