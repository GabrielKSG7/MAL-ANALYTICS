"""Conector da API GraphQL da AniList — elenco, dubladores, staff, estúdios e pessoas.

Docs: https://docs.anilist.co
- Limite: 90 req/min no normal; em "modo degradado" (ativo em 2026) são 30 req/min.
  Padrão aqui: ANILIST_RPS=0.45 (~27/min). Estourou? 429 + Retry-After → respeitamos.
- Termos: gratuito para uso não comercial. A AniList proíbe "coleta em massa", com tolerância
  declarada para projetos educacionais — este é um projeto pessoal/educacional, com ritmo
  conservador e sem redistribuição dos dados.

Busca cada anime pelo ID do MAL (`Media(idMal: ...)`), então tudo se liga ao resto do warehouse
sem tabela de-para. Personagens e staff vêm paginados (25 por página); buscamos até
ANILIST_MAX_PAGES páginas e mesclamos tudo num único payload por anime.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable

from malpipe.config import Settings
from malpipe.http import FetchResult, PoliteClient
from malpipe.warehouse import RunContext, Warehouse, to_json, utcnow

log = logging.getLogger(__name__)

PER_PAGE = 25

QUERY = """
query ($idMal: Int, $page: Int, $withMeta: Boolean!, $withChars: Boolean!, $withStaff: Boolean!) {
  Media(idMal: $idMal, type: ANIME) {
    id
    idMal
    title @include(if: $withMeta) { romaji english native }
    favourites @include(if: $withMeta)
    averageScore @include(if: $withMeta)
    popularity @include(if: $withMeta)
    countryOfOrigin @include(if: $withMeta)
    tags @include(if: $withMeta) { name rank category isMediaSpoiler }
    studios @include(if: $withMeta) {
      edges { isMain node { id name isAnimationStudio favourites siteUrl } }
    }
    characters(page: $page, perPage: 25, sort: [ROLE, RELEVANCE, ID]) @include(if: $withChars) {
      pageInfo { hasNextPage }
      edges {
        role
        node {
          id
          name { full native }
          gender
          age
          favourites
          dateOfBirth { year month day }
          image { medium }
          siteUrl
        }
        voiceActorRoles(sort: [RELEVANCE, ID]) {
          roleNotes
          dubGroup
          voiceActor { ...person }
        }
      }
    }
    staff(page: $page, perPage: 25, sort: [RELEVANCE, ID]) @include(if: $withStaff) {
      pageInfo { hasNextPage }
      edges { role node { ...person } }
    }
  }
}

fragment person on Staff {
  id
  name { full native }
  languageV2
  gender
  favourites
  primaryOccupations
  homeTown
  yearsActive
  dateOfBirth { year month day }
  dateOfDeath { year month day }
  image { medium }
  siteUrl
}
"""


def build_client(settings: Settings, **kwargs) -> PoliteClient:
    return PoliteClient(
        base_url=settings.anilist_url,
        rps=settings.anilist_rps,
        headers={
            "User-Agent": settings.user_agent,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=settings.http_timeout,
        max_retries=settings.max_retries,
        backoff_cap=90.0,  # o "castigo" da AniList ao estourar o limite é de 1 minuto
        **kwargs,
    )


def _media(result: FetchResult) -> dict | None:
    if not result.ok:
        return None
    return ((result.payload or {}).get("data") or {}).get("Media")


def fetch_media(client: PoliteClient, mal_id: int, max_pages: int) -> FetchResult:
    """Busca um anime com todas as páginas de personagens e staff (até `max_pages`)."""
    variables = {"idMal": mal_id, "page": 1, "withMeta": True, "withChars": True, "withStaff": True}
    first = client.post_json("", {"query": QUERY, "variables": variables})
    media = _media(first)
    if media is None:
        if first.ok:
            # HTTP 200 com "errors" e sem dados = erro de GraphQL (consulta inválida, campo removido…).
            # Vira 400 para NÃO entrar como extraído e voltar para a fila depois da correção.
            errors = (first.payload or {}).get("errors")
            return FetchResult(first.url, 400, None, f"GraphQL: {json.dumps(errors, ensure_ascii=False)[:400]}")
        # A AniList responde 404 com {"errors": [{"message": "Not Found."}]} quando não há o idMal.
        return first

    characters = list((media.get("characters") or {}).get("edges") or [])
    staff = list((media.get("staff") or {}).get("edges") or [])
    more_chars = bool(((media.get("characters") or {}).get("pageInfo") or {}).get("hasNextPage"))
    more_staff = bool(((media.get("staff") or {}).get("pageInfo") or {}).get("hasNextPage"))

    page = 1
    while (more_chars or more_staff) and page < max_pages:
        page += 1
        variables = {"idMal": mal_id, "page": page, "withMeta": False, "withChars": more_chars,
                     "withStaff": more_staff}  # fmt: skip
        nxt = _media(client.post_json("", {"query": QUERY, "variables": variables}))
        if nxt is None:  # falha numa página extra: fica com o que já veio, sem perder o anime
            break
        if more_chars:
            characters += (nxt.get("characters") or {}).get("edges") or []
            more_chars = bool(((nxt.get("characters") or {}).get("pageInfo") or {}).get("hasNextPage"))
        if more_staff:
            staff += (nxt.get("staff") or {}).get("edges") or []
            more_staff = bool(((nxt.get("staff") or {}).get("pageInfo") or {}).get("hasNextPage"))

    media["characters"] = characters
    media["staff"] = staff
    media["truncated"] = more_chars or more_staff  # sobrou página além do limite configurado
    return FetchResult(first.url, first.status_code, media)


def fetch_all(
    client: PoliteClient,
    wh: Warehouse,
    run: RunContext,
    ids: Iterable[int],
    max_pages: int = 4,
    flush_every: int = 20,
) -> dict[int, int]:
    columns = ("mal_id", "http_status", "payload", "error", "extracted_at", "run_id")
    buffer: list[tuple] = []
    status_count: dict[int, int] = {}
    ids = list(ids)
    graphql_errors = 0
    for i, mal_id in enumerate(ids, start=1):
        result = fetch_media(client, mal_id, max_pages)
        status_count[result.status_code] = status_count.get(result.status_code, 0) + 1
        graphql_errors = graphql_errors + 1 if (result.error or "").startswith("GraphQL") else 0
        if graphql_errors >= 3:
            run.add(wh.insert_rows("bronze.anilist_media", columns, buffer))
            raise RuntimeError(
                f"A AniList rejeitou a consulta 3 vezes seguidas (provável mudança na API): {result.error}"
            )
        buffer.append((mal_id, result.status_code, to_json(result.payload if result.ok else None),
                       result.error, utcnow(), run.run_id))  # fmt: skip
        if client.host_unreachable:
            run.add(wh.insert_rows("bronze.anilist_media", columns, buffer))
            client.raise_if_unreachable()
        if len(buffer) >= flush_every or i == len(ids):
            run.add(wh.insert_rows("bronze.anilist_media", columns, buffer))
            buffer.clear()
            log.info("anilist: %s/%s (%s)", i, len(ids), status_count)
    return status_count


# ----------------------------------------------------------------------------- relações (em lote)
# A ligação anime → mangá de origem não vem da MAL API na prática (o `related_anime` dos mangás
# chega vazio), mas a AniList informa a obra de origem de cada anime (`relationType: SOURCE`).
# Como só precisamos das relações, dá para pedir 50 animes por requisição: ~30 mil animes em
# ~600 chamadas (≈ 20 min no ritmo degradado), em vez de 30 mil.
RELATIONS_QUERY = """
query ($ids: [Int]) {
  Page(page: 1, perPage: 50) {
    media(idMal_in: $ids, type: ANIME) {
      idMal
      relations {
        edges {
          relationType(version: 2)
          node { id idMal type format }
        }
      }
    }
  }
}
"""
RELATIONS_BATCH = 50


def fetch_relations_batch(client: PoliteClient, ids: list[int]) -> tuple[int, dict[int, list], str | None]:
    """Uma requisição para até 50 animes. Devolve (status, {mal_id: arestas}, erro)."""
    result = client.post_json("", {"query": RELATIONS_QUERY, "variables": {"ids": ids}})
    if not result.ok:
        return result.status_code, {}, result.error
    data = (result.payload or {}).get("data") or {}
    page = data.get("Page")
    if page is None:
        errors = (result.payload or {}).get("errors")
        return 400, {}, f"GraphQL: {json.dumps(errors, ensure_ascii=False)[:400]}"
    found: dict[int, list] = {}
    for media in page.get("media") or []:
        if media and media.get("idMal") is not None and media["idMal"] not in found:
            found[media["idMal"]] = ((media.get("relations") or {}).get("edges")) or []
    return result.status_code, found, None


def fetch_relations_all(
    client: PoliteClient, wh: Warehouse, run: RunContext, ids: Iterable[int], batch_size: int = RELATIONS_BATCH
) -> dict[int, int]:
    """Grava uma linha por anime em bronze.anilist_relations (404 = anime sem cadastro na AniList)."""
    columns = ("mal_id", "http_status", "payload", "error", "extracted_at", "run_id")
    ids = list(ids)
    status_count: dict[int, int] = {}
    graphql_errors = 0
    for start in range(0, len(ids), batch_size):
        chunk = ids[start : start + batch_size]
        status, found, error = fetch_relations_batch(client, chunk)
        rows = []
        for mal_id in chunk:
            if status == 200:
                st, payload, err = (200, to_json(found[mal_id]), None) if mal_id in found else (404, None, None)
            else:
                st, payload, err = status, None, error
            status_count[st] = status_count.get(st, 0) + 1
            rows.append((mal_id, st, payload, err, utcnow(), run.run_id))
        run.add(wh.insert_rows("bronze.anilist_relations", columns, rows))
        graphql_errors = graphql_errors + 1 if (error or "").startswith("GraphQL") else 0
        if graphql_errors >= 3:
            raise RuntimeError(f"A AniList rejeitou a consulta de relações 3 vezes seguidas: {error}")
        if client.host_unreachable:
            client.raise_if_unreachable()
        done = min(start + batch_size, len(ids))
        if done % (batch_size * 10) == 0 or done == len(ids):
            log.info("anilist relações: %s/%s (%s)", done, len(ids), status_count)
    return status_count
