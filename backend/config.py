import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings:
    APP_NAME = os.getenv("APP_NAME", "Job Crawler Web")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{DATA_DIR / 'app.db'}"
    )

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")

    BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
    BROWSER_CDP_URL = os.getenv("BROWSER_CDP_URL", "")
    BROWSER_USER_AGENT = os.getenv(
        "BROWSER_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    DEFAULT_MAX_PAGES = int(os.getenv("DEFAULT_MAX_PAGES", "5"))
    DEFAULT_MAX_JOBS = int(os.getenv("DEFAULT_MAX_JOBS", "200"))


settings = Settings()
