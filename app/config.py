import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./boss_overseas.db")
    BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
    SEARCH_KEYWORDS = os.getenv("SEARCH_KEYWORDS", "海外").split(",")
    MAX_PAGES = int(os.getenv("MAX_PAGES", "2"))


settings = Settings()