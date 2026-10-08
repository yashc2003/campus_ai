from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str | None
    database_name: str
    environment: str


def get_settings() -> Settings:
    uri = os.getenv("MONGODB_URI", "").strip() or None
    return Settings(
        mongodb_uri=uri,
        database_name=os.getenv("DATABASE_NAME", "campus_ai").strip() or "campus_ai",
        environment=os.getenv("CAMPUS_AI_ENV", "development").strip(),
    )
