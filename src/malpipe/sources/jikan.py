"""Conector do Jikan v4 — enriquecimento do que a API oficial não entrega.

Docs: https://docs.api.jikan.moe
- /anime/{id}/statistics      → distribuição de notas 1–10 (base da análise de polarização)
- /anime/{id}/recommendations → recomendações dos usuários (votos), útil para avaliar o recomendador
- /anime/{id}/characters      → personagens e dubladores (grafo de seiyuus)

Limites publicados: 3 req/s e 60 req/min. Usamos 1 req/s por padrão. Para cargas grandes,
rode sua própria instância (docker run jikanme/jikan-rest) e aponte JIKAN_BASE_URL para ela.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from malpipe.config import Settings
from malpipe.http import PoliteClient
from malpipe.warehouse import JIKAN_ENTITIES, RunContext, Warehouse, to_json, utcnow

log = logging.getLogger(__name__)


def build_client(settings: Settings, **kwargs) -> PoliteClient:
    return PoliteClient(
        base_url=settings.jikan_base_url,
        rps=settings.jikan_rps,
        headers={"User-Agent": settings.user_agent},
        timeout=settings.http_timeout,
        max_retries=settings.max_retries,
        **kwargs,
    )


def fetch_entity(
    client: PoliteClient,
    wh: Warehouse,
    run: RunContext,
    entity: str,
    ids: Iterable[int],
    flush_every: int = 25,
) -> dict[int, int]:
    if entity not in JIKAN_ENTITIES:
        raise ValueError(f"entidade inválida: {entity}. Use uma de {JIKAN_ENTITIES}")
    table = f"bronze.jikan_{entity}"
    columns = ("mal_id", "http_status", "payload", "error", "extracted_at", "run_id")
    buffer: list[tuple] = []
    status_count: dict[int, int] = {}
    ids = list(ids)
    for i, mal_id in enumerate(ids, start=1):
        result = client.get(f"/anime/{mal_id}/{entity}")
        status_count[result.status_code] = status_count.get(result.status_code, 0) + 1
        # O Jikan embrulha tudo em {"data": ...}; guardamos só o conteúdo útil.
        payload = result.payload.get("data") if result.ok else None
        buffer.append((mal_id, result.status_code, to_json(payload), result.error, utcnow(), run.run_id))
        if client.host_unreachable:
            run.add(wh.insert_rows(table, columns, buffer))
            client.raise_if_unreachable()
        if len(buffer) >= flush_every or i == len(ids):
            run.add(wh.insert_rows(table, columns, buffer))
            buffer.clear()
            log.info("jikan %s: %s/%s (%s)", entity, i, len(ids), status_count)
    return status_count
