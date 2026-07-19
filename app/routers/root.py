from fastapi import APIRouter

# 기본 API를 관리하는 Router
router = APIRouter(
    tags=["서버 확인"]
)


# 서버가 정상적으로 실행 중인지 확인하는 API
@router.get(
    "/",
    summary="서버 상태 확인",
    description="하브루타 AI 튜터 백엔드 서버의 실행 상태를 확인합니다."
)
def root():
    return {
        "message": "하브루타 AI 튜터 백엔드 서버입니다!"
    }