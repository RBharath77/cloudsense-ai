from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = f"sqlite:///{BACKEND_DIR / 'cloudsense.db'}"

class Settings(BaseSettings):
    app_name: str = "CloudSense AI"
    database_url: str = DEFAULT_DB_PATH
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
