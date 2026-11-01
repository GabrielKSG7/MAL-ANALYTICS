"""Conector da API oficial do MyAnimeList (v2).

Docs: https://myanimelist.net/apiconfig/references/api/v2
Autenticação: endpoints públicos aceitam apenas o header `X-MAL-CLIENT-ID`
(registre um app em https://myanimelist.net/apiconfig, tipo "other"/hobbyist).

Estratégia de cobertura total:
1. **Descoberta** de IDs via ranking (`ranking_type=all`) e temporadas — pagina de 500 em 500.
2. União com os IDs do MAL presentes no anime-offline-database (cobre o que não está ranqueado,
   ex.: títulos ainda não lançados).
3. **Detalhe** por ID, com checkpoint no bronze (só extrai o que é novo ou está velho).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator

from malpipe.config import Settings
from malpipe.http import FetchResult, PoliteClient
from malpipe.warehouse import RunContext, Warehouse, to_json, utcnow

log = logging.getLogger(__name__)

ANIME_FIELDS = ",".join(
    [
        "id", "title", "main_picture", "alternative_titles", "start_date", "end_date", "synopsis",
        "mean", "rank", "popularity", "num_list_users", "num_scoring_users", "nsfw", "created_at",
        "updated_at", "media_type", "status", "genres", "num_episodes", "start_season", "broadcast",
        "source", "average_episode_duration", "rating", "studios", "related_anime", "statistics",
        "background",
    ]
)  # fmt: skip

SEASONS = ("winter", "spring", "summer", "fall")
PAGE_LIMIT = 500  # máximo aceito por ranking/season
LIST_PAGE_LIMIT = 1000  # máximo aceito por user animelist


def build_client(settings: Settings, **kwargs) -> PoliteClient:
    if not settings.mal_client_id:
        from malpipe.config import ENV_FILE

        raise RuntimeError(
            "MAL_CLIENT_ID não configurado. Crie um app em https://myanimelist.net/apiconfig "
            f"e coloque o Client ID em {ENV_FILE}" + ("" if ENV_FILE.exists() else " (arquivo não existe)")
        )
    return PoliteClient(
        base_url=settings.mal_base_url,
        rps=settings.mal_rps,
        headers={"X-MAL-CLIENT-ID": settings.mal_client_id, "User-Agent": settings.user_agent},
        timeout=settings.http_timeout,
        max_retries=settings.max_retries,
        **kwargs,
    )


def paginate(client: PoliteClient, url: str, params: dict | None) -> Iterator[FetchResult]:
    """Segue `paging.next` (URL absoluta, já com offset/limit) até acabar."""
    next_url: str | None = url
    next_params = params
    while next_url:
        result = client.get(next_url, params=next_params)
        yield result
        if not result.ok:
            return
        next_url = (result.payload.get("paging") or {}).get("next")
        next_params = None  # a URL de `next` já carrega a querystring


def discover_ranking(
    client: PoliteClient, wh: Warehouse, run: RunContext, ranking_type: str = "all", max_pages: int | None = None
) -> int:
    params = {"ranking_type": ranking_type, "limit": PAGE_LIMIT, "fields": "id", "nsfw": "true"}
    written = 0
    for page, result in enumerate(paginate(client, "/anime/ranking", params), start=1):
        if not result.ok:
            log.error("falha no ranking (página %s): %s %s", page, result.status_code, result.error)
            break
        rows = [
            (item["node"]["id"], f"ranking:{ranking_type}", utcnow(), run.run_id)
            for item in result.payload.get("data", [])
        ]
        written += wh.insert_rows(
            "bronze.mal_anime_discovery", ("mal_id", "discovered_via", "extracted_at", "run_id"), rows
        )
        log.info("ranking %s: página %s, %s IDs acumulados", ranking_type, page, written)
        if max_pages and page >= max_pages:
            break
    run.add(written)
    return written


def discover_seasons(client: PoliteClient, wh: Warehouse, run: RunContext, years: Iterable[int]) -> int:
    written = 0
    for year in years:
        for season in SEASONS:
            params = {"limit": PAGE_LIMIT, "fields": "id", "nsfw": "true"}
            for result in paginate(client, f"/anime/season/{year}/{season}", params):
                if not result.ok:
                    if result.status_code != 404:
                        log.error("falha em %s/%s: %s", year, season, result.status_code)
                    break
                rows = [
                    (item["node"]["id"], f"season:{year}-{season}", utcnow(), run.run_id)
                    for item in result.payload.get("data", [])
                ]
                written += wh.insert_rows(
                    "bronze.mal_anime_discovery",
                    ("mal_id", "discovered_via", "extracted_at", "run_id"),
                    rows,
                )
        log.info("temporadas de %s descobertas (%s IDs acumulados)", year, written)
    run.add(written)
    return written


def fetch_details(
    client: PoliteClient, wh: Warehouse, run: RunContext, ids: Iterable[int], flush_every: int = 25
) -> dict[int, int]:
    """Extrai o detalhe completo de cada ID. Grava em lotes para não perder progresso."""
    buffer: list[tuple] = []
    status_count: dict[int, int] = {}
    columns = ("mal_id", "http_status", "payload", "error", "extracted_at", "run_id")
    ids = list(ids)
    for i, mal_id in enumerate(ids, start=1):
        result = client.get(f"/anime/{mal_id}", params={"fields": ANIME_FIELDS, "nsfw": "true"})
        status_count[result.status_code] = status_count.get(result.status_code, 0) + 1
        buffer.append((mal_id, result.status_code, to_json(result.payload), result.error, utcnow(), run.run_id))
        if len(buffer) >= flush_every or i == len(ids):
            run.add(wh.insert_rows("bronze.mal_anime", columns, buffer))
            buffer.clear()
            log.info("detalhes MAL: %s/%s (%s)", i, len(ids), status_count)
    return status_count


def fetch_user_list(client: PoliteClient, wh: Warehouse, run: RunContext, username: str) -> int:
    """Lista pública de um usuário (a sua, para o projeto 'Meu perfil vs MAL')."""
    params = {
        "fields": "list_status{status,score,num_episodes_watched,is_rewatching,updated_at,"
        "start_date,finish_date,num_times_rewatched}",
        "limit": LIST_PAGE_LIMIT,
        "nsfw": "true",
    }
    written = 0
    extracted_at = utcnow()
    for result in paginate(client, f"/users/{username}/animelist", params):
        if not result.ok:
            raise RuntimeError(
                f"não consegui ler a lista de '{username}' (HTTP {result.status_code}). "
                "A lista precisa estar pública no MAL."
            )
        rows = [(username, to_json(item), extracted_at, run.run_id) for item in result.payload.get("data", [])]
        written += wh.insert_rows("bronze.mal_user_animelist", ("username", "payload", "extracted_at", "run_id"), rows)
    run.add(written)
    return written
