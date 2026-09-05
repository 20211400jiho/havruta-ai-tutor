from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.paths import BACKEND_DIR, resolve_chroma_dir


class Settings(BaseSettings):
    app_name: str = "Havruta AI Tutor API"
    app_env: str = "development"
    database_url_env: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "MYSQL_URL"),
    )
    db_host: str = Field(default="127.0.0.1", validation_alias=AliasChoices("DB_HOST", "MYSQLHOST"))
    db_port: int = Field(default=3306, validation_alias=AliasChoices("DB_PORT", "MYSQLPORT"))
    db_user: str = Field(default="root", validation_alias=AliasChoices("DB_USER", "MYSQLUSER"))
    db_password: str = Field(default="", validation_alias=AliasChoices("DB_PASSWORD", "MYSQLPASSWORD"))
    db_name: str = Field(default="havruta_ai_tutor", validation_alias=AliasChoices("DB_NAME", "MYSQLDATABASE"))
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6-terra"
    openai_reasoning_effort: str = "none"
    openai_timeout_seconds: float = 45.0
    openai_max_output_tokens: int = 700
    ai_requests_per_minute: int = 12
    ai_requests_per_day: int = 200
    rag_provider: str = "auto"
    rag_curriculum_year: str = "2022"
    chroma_dir: str = "chroma_db"
    chroma_collection: str = "havruta_math_all"
    embedding_model: str = "intfloat/multilingual-e5-base"
    embedding_local_files_only: bool = True
    rag_min_score: float = 0.2
    redis_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("chroma_dir")
    @classmethod
    def normalize_chroma_dir(cls, value: str) -> str:
        return str(resolve_chroma_dir(value))

    @property
    def database_url(self) -> str:
        if self.database_url_env:
            if self.database_url_env.startswith("mysql://"):
                return self.database_url_env.replace("mysql://", "mysql+pymysql://", 1)
            return self.database_url_env
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
