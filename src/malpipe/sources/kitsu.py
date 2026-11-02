"""Conector da API do Kitsu — episódios (título, número, temporada, data de exibição, duração).

API pública JSON:API: https://kitsu.app/api/edge (kitsu.io redireciona para cá).
Sem limite publicado; usamos KITSU_RPS=2 por padrão. O vínculo MAL ↔ Kitsu vem do
anime-offline-database.

GET /anime/{kitsu_id}/episodes?page[limit]=20&sort=number  → segue links.next até acabar.
"""

from __future__ import annotations

import logging

from malpipe.config import Settings
from malpipe.http import FetchResult, PoliteClient
from malpipe.warehouse import RunContext, Warehouse, to_json, utcnow

log = logging.getLogger(__name__)

PAGE_LIMIT = 20  # máximo aceito pelo Kitsu
FIELDS = "number,seasonNumber,relativeNumber,canonicalTitle,titles,airdate,length,synopsis"
MAX_PAGES = 200  # 4.000 episódios: cobre até One Piece / Detective Conan


def build_client(settings: Settings, **kwargs) -> PoliteClient:
    return PoliteClient(
        base_url=settings.kitsu_base_url,
        rps=settings.kitsu_rps,
        headers={"User-Agent": settings.user_agent, "Accept": "application/vnd.api+json"},
        timeout=settings.http_timeout,
        max_retries=settings.max_retries,
        **kwargs,
    )


def fetch_episodes(client: PoliteClient, kitsu_id: int) -> FetchResult:
    params = {"page[limit]": PAGE_LIMIT, "page[offset]": 0, "sort": "number", "fields[episodes]": FIELDS}
    first = client.get(f"/anime/{kitsu_id}/episodes", params=params)
    if not first.ok:
        return first
    episodes = []
    page, result = 1, first
    while True:
        for item in result.payload.get("data") or []:
            attrs = item.get("attributes") or {}
            episodes.append({"kitsu_episode_id": item.get("id"), **attrs})
        next_url = (result.payload.get("links") or {}).get("next")
        if not next_url or page >= MAX_PAGES:
            break
        result = client.get(next_url)
        page += 1
        if not result.ok:
            break  # mantém as páginas que já vieram
    return FetchResult(first.url, first.status_code, {"episodes": episodes})


def fetch_all(
    client: PoliteClient,
    wh: Warehouse,
    run: RunContext,
    targets: dict[int, int],
    flush_every: int = 25,
) -> dict[int, int]:
    """`targets`: mal_id → kitsu_id."""
    columns = ("mal_id", "kitsu_id", "http_status", "payload", "error", "extracted_at", "run_id")
    buffer: list[tuple] = []
    status_count: dict[int, int] = {}
    items = list(targets.items())
    for i, (mal_id, kitsu_id) in enumerate(items, start=1):
        result = fetch_episodes(client, kitsu_id)
        status_count[result.status_code] = status_count.get(result.status_code, 0) + 1
        payload = (result.payload or {}).get("episodes") if result.ok else None
        buffer.append((mal_id, kitsu_id, result.status_code, to_json(payload), result.error, utcnow(), run.run_id))
        if client.host_unreachable:
            run.add(wh.insert_rows("bronze.kitsu_episodes", columns, buffer))
            client.raise_if_unreachable()
        if len(buffer) >= flush_every or i == len(items):
            run.add(wh.insert_rows("bronze.kitsu_episodes", columns, buffer))
            buffer.clear()
            log.info("kitsu episódios: %s/%s (%s)", i, len(items), status_count)
    return status_count
