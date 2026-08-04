import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database.base import Base
from app.database.connection import get_db
from app.services.rag_service import index_local_documents
from main import app


TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=TEST_ENGINE, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def database():
    Base.metadata.create_all(TEST_ENGINE)
    db = TestSession()
    index_local_documents(db)
    db.close()
    yield
    Base.metadata.drop_all(TEST_ENGINE)


@pytest.fixture
def client():
    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    response = client.post(
        "/auth/signup",
        json={
            "email": "student@example.com",
            "password": "strong-password",
            "name": "테스트 학생",
            "grade": "고등학교 1학년",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
