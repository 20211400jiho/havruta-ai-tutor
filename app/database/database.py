from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite 데이터베이스 파일 경로
DATABASE_URL = "sqlite:///./havruta.db"

# 데이터베이스 엔진 생성
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# 데이터베이스 세션 생성
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 모든 테이블 모델이 상속받을 기본 클래스
Base = declarative_base()


# 데이터베이스 연결 함수
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()