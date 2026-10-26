from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    cors_origins: str = "http://localhost:3000"
    groq_api_key: str | None = None
    groq_model: str | None = None


settings = Settings()