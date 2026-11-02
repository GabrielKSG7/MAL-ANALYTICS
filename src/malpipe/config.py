"""Configuração centralizada, lida de variáveis de ambiente (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

# utf-8-sig: o Bloco de Notas/PowerShell do Windows costumam gravar BOM no início do arquivo,
# o que faria a primeira variável do .env não ser reconhecida.
load_dotenv(ENV_FILE, encoding="utf-8-sig")
load_dotenv(Path.cwd() / ".env", encoding="utf-8-sig")  # fallback: .env na pasta atual


def _project_path(name: str, default: str) -> Path:
    """Caminho vindo do .env; se for relativo, é resolvido a partir da raiz do projeto
    (e não da pasta atual), para o Python, o dbt e o dashboard enxergarem o MESMO arquivo."""
    path = Path(os.getenv(name, default)).expanduser()
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


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

    duckdb_path: Path = field(default_factory=lambda: _project_path("DUCKDB_PATH", "data/mal.duckdb"))
    data_dir: Path = field(default_factory=lambda: _project_path("DATA_DIR", "data"))
    # Cópia do banco para ferramentas externas (DBeaver, Power BI...). Fica separada para que um
    # cliente aberto nunca trave a ingestão/o dbt — o DuckDB aceita um único processo escrevendo.
    reports_db_path: Path = field(default_factory=lambda: _project_path("REPORTS_DB_PATH", "data/mal_reports.duckdb"))

    mal_client_id: str | None = field(default_factory=lambda: os.getenv("MAL_CLIENT_ID"))
    mal_username: str | None = field(default_factory=lambda: os.getenv("MAL_USERNAME"))
    mal_base_url: str = field(default_factory=lambda: os.getenv("MAL_BASE_URL", "https://api.myanimelist.net/v2"))
    mal_rps: float = field(default_factory=lambda: _float("MAL_RPS", 1.0))

    jikan_base_url: str = field(default_factory=lambda: os.getenv("JIKAN_BASE_URL", "https://api.jikan.moe/v4"))
    jikan_rps: float = field(default_factory=lambda: _float("JIKAN_RPS", 1.0))

    anilist_url: str = field(default_factory=lambda: os.getenv("ANILIST_URL", "https://graphql.anilist.co"))
    # A AniList está em "modo degradado" (30 req/min); 0,45 req/s ≈ 27/min deixa folga.
    anilist_rps: float = field(default_factory=lambda: _float("ANILIST_RPS", 0.45))
    # Páginas de 25 personagens e 25 membros de staff por anime (4 → até 100 de cada).
    anilist_max_pages: int = field(default_factory=lambda: _int("ANILIST_MAX_PAGES", 4))

    kitsu_base_url: str = field(default_factory=lambda: os.getenv("KITSU_BASE_URL", "https://kitsu.app/api/edge"))
    kitsu_rps: float = field(default_factory=lambda: _float("KITSU_RPS", 2.0))

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
