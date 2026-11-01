"""Configuração centralizada, lida de variáveis de ambiente (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    """Parâmetros do pipeline. Os defaults são conservadores de propósito.

    - MAL API v2 não documenta rate limit; a prática da comunidade é ~1 req/s.
    - Jikan publica 3 req/s e 60 req/min; usamos 1 req/s para não pressionar o serviço
      (que, por trás, raspa o próprio MAL).
    """

    duckdb_path: Path = field(
        default_factory=lambda: Path(os.getenv("DUCKDB_PATH", PROJECT_ROOT / "data" / "mal.duckdb"))
    )
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data")))

    mal_client_id: str | None = field(default_factory=lambda: os.getenv("MAL_CLIENT_ID"))
    mal_username: str | None = field(default_factory=lambda: os.getenv("MAL_USERNAME"))
    mal_base_url: str = "https://api.myanimelist.net/v2"
    mal_rps: float = field(default_factory=lambda: _float("MAL_RPS", 1.0))

    jikan_base_url: str = field(default_factory=lambda: os.getenv("JIKAN_BASE_URL", "https://api.jikan.moe/v4"))
    jikan_rps: float = field(default_factory=lambda: _float("JIKAN_RPS", 1.0))

    manami_url: str = (
        "https://github.com/manami-project/anime-offline-database/releases/latest/download/"
        "anime-offline-database-minified.json.zst"
    )

    # Quantos dias até um registro já extraído ser considerado "velho" e re-extraído.
    refresh_days: int = field(default_factory=lambda: _int("REFRESH_DAYS", 7))
    http_timeout: float = field(default_factory=lambda: _float("HTTP_TIMEOUT", 30.0))
    max_retries: int = field(default_factory=lambda: _int("MAX_RETRIES", 5))
    user_agent: str = "mal-anime-analytics/0.1 (personal, non-commercial portfolio project)"


def get_settings() -> Settings:
    return Settings()
