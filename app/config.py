from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    jwt_secret: str = "dev-only-change-me"
    jwt_ttl_days: int = 30
    guest_ttl_days: int = 30

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"

    database_url: str = "sqlite+aiosqlite:///./lumina.db"
    frontend_url: str = "http://localhost:3000"


settings = Settings()
