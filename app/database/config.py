from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    ai_provider: str = "local"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    redis_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

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
