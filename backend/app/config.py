from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "CloudSense AI"
    database_url: str = "sqlite:///./cloudsense.db"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    cloud_mode: str = "mock"
    mock_email: bool = True
    mock_slack: bool = True
    ollama_base_url: str | None = None
    llm_model: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
