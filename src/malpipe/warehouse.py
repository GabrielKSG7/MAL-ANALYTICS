"""Camada bronze no DuckDB.

Decisões (ver docs/adr/002-bronze-append-only-json.md):
- Bronze é **append-only**: cada extração vira uma linha nova, com o JSON cru da API.
  Isso dá histórico de graça (evolução de nota/membros) e permite reprocessar o
  silver/gold sem bater na API de novo.
- O próprio bronze funciona como checkpoint: "o que falta extrair" é calculado a partir
  do que já está lá (status HTTP + data da extração). Não existe tabela de estado separada
  que possa ficar dessincronizada.
"""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import duckdb

DDL = [
    "CREATE SCHEMA IF NOT EXISTS bronze",
    "CREATE SCHEMA IF NOT EXISTS meta",
    """
    CREATE TABLE IF NOT EXISTS meta.runs (
        run_id        VARCHAR PRIMARY KEY,
        command       VARCHAR NOT NULL,
        started_at    TIMESTAMP NOT NULL,
        finished_at   TIMESTAMP,
        status        VARCHAR NOT NULL,
        rows_written  BIGINT DEFAULT 0,
        notes         VARCHAR
    )
    """,
    # IDs descobertos (ranking, temporadas, manami). Base para o crawl de detalhes.
    """
    CREATE TABLE IF NOT EXISTS bronze.mal_anime_discovery (
        mal_id         INTEGER NOT NULL,
        discovered_via VARCHAR NOT NULL,
        extracted_at   TIMESTAMP NOT NULL,
        run_id         VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bronze.mal_anime (
        mal_id        INTEGER NOT NULL,
        http_status   INTEGER NOT NULL,
        payload       JSON,
        error         VARCHAR,
        extracted_at  TIMESTAMP NOT NULL,
        run_id        VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bronze.mal_user_animelist (
        username      VARCHAR NOT NULL,
        payload       JSON NOT NULL,
        extracted_at  TIMESTAMP NOT NULL,
        run_id        VARCHAR NOT NULL
    )
    """,
    *[
        f"""
        CREATE TABLE IF NOT EXISTS bronze.jikan_{name} (
            mal_id        INTEGER NOT NULL,
            http_status   INTEGER NOT NULL,
            payload       JSON,
            error         VARCHAR,
            extracted_at  TIMESTAMP NOT NULL,
            run_id        VARCHAR NOT NULL
        )
        """
        for name in ("statistics", "recommendations", "characters")
    ],
    """
    CREATE TABLE IF NOT EXISTS bronze.manami_anime (
        payload       JSON NOT NULL,
        dataset_date  DATE,
        extracted_at  TIMESTAMP NOT NULL,
        run_id        VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bronze.kaggle_animelist (
        user_id           BIGINT,
        anime_id          INTEGER,
        score             INTEGER,
        watching_status   INTEGER,
        watched_episodes  INTEGER,
        source_file       VARCHAR,
        loaded_at         TIMESTAMP NOT NULL,
        run_id            VARCHAR NOT NULL
    )
    """,
]

# --- ecossistema: mangá (MAL API), elenco/staff/estúdios (AniList) e episódios (Kitsu)
DDL += [
    """
    CREATE TABLE IF NOT EXISTS bronze.mal_manga_discovery (
        mal_id         INTEGER NOT NULL,
        discovered_via VARCHAR NOT NULL,
        extracted_at   TIMESTAMP NOT NULL,
        run_id         VARCHAR NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bronze.mal_manga (
        mal_id        INTEGER NOT NULL,
        http_status   INTEGER NOT NULL,
        payload       JSON,
        error         VARCHAR,
        extracted_at  TIMESTAMP NOT NULL,
        run_id        VARCHAR NOT NULL
    )
    """,
    # payload = Media da AniList com TODAS as páginas de personagens/staff já mescladas
    """
    CREATE TABLE IF NOT EXISTS bronze.anilist_media (
        mal_id        INTEGER NOT NULL,
        http_status   INTEGER NOT NULL,
        payload       JSON,
        error         VARCHAR,
        extracted_at  TIMESTAMP NOT NULL,
        run_id        VARCHAR NOT NULL
    )
    """,
    # payload = lista com todos os episódios do anime (todas as páginas do Kitsu)
    """
    CREATE TABLE IF NOT EXISTS bronze.kitsu_episodes (
        mal_id        INTEGER NOT NULL,
        kitsu_id      INTEGER,
        http_status   INTEGER NOT NULL,
        payload       JSON,
        error         VARCHAR,
        extracted_at  TIMESTAMP NOT NULL,
        run_id        VARCHAR NOT NULL
    )
    """,
]

JIKAN_ENTITIES = ("statistics", "recommendations", "characters")


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Warehouse:
    def __init__(self, path: Path | str, read_only: bool = False) -> None:
        self.path = Path(path)
        if not read_only:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(self.path), read_only=read_only)
        # várias fontes podem extrair em paralelo (threads); o DuckDB exige serializar o uso
        # de uma mesma conexão, então todo acesso passa por este lock.
        self.lock = threading.RLock()
        if not read_only:
            self.init_schema()

    def init_schema(self) -> None:
        for stmt in DDL:
            self.con.execute(stmt)

    def close(self) -> None:
        self.con.close()

    # ------------------------------------------------------------------ runs
    @contextmanager
    def run(self, command: str):
        """Registra uma execução em meta.runs (sucesso/falha + linhas gravadas)."""
        run = RunContext(self, command)
        with self.lock:
            self.con.execute(
                "INSERT INTO meta.runs (run_id, command, started_at, status) VALUES (?, ?, ?, 'running')",
                [run.run_id, command, utcnow()],
            )
        try:
            yield run
        except BaseException as exc:
            self._finish_run(run, "failed", f"{type(exc).__name__}: {exc}")
            raise
        else:
            self._finish_run(run, "success", run.notes)

    def _finish_run(self, run: RunContext, status: str, notes: str | None) -> None:
        with self.lock:
            self.con.execute(
                "UPDATE meta.runs SET finished_at = ?, status = ?, rows_written = ?, notes = ? WHERE run_id = ?",
                [utcnow(), status, run.rows_written, notes, run.run_id],
            )

    # ---------------------------------------------------------------- writes
    def insert_rows(self, table: str, columns: Sequence[str], rows: Iterable[Sequence]) -> int:
        with self.lock:
            return self._insert_rows(table, columns, rows)

    def _insert_rows(self, table: str, columns: Sequence[str], rows: Iterable[Sequence]) -> int:
        rows = list(rows)
        if not rows:
            return 0
        placeholders = ", ".join("?" for _ in columns)
        self.con.executemany(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", rows)
        return len(rows)

    # ----------------------------------------------------------- checkpoints
    def pending_ids(
        self,
        table: str,
        refresh_days: int,
        candidate_sql: str,
        retry_not_found: bool = False,
        limit: int | None = None,
    ) -> list[int]:
        """IDs candidatos que ainda precisam ser (re)extraídos para `table`.

        Fica de fora quem foi extraído com sucesso há menos de `refresh_days` dias e,
        a menos que `retry_not_found`, quem já retornou 404 (ID inexistente/removido).
        Falhas transitórias (429/5xx/rede esgotada) voltam para a fila.
        """
        not_found_clause = "" if retry_not_found else "OR (http_status = 404)"
        sql = f"""
            WITH candidates AS ({candidate_sql}),
            done AS (
                SELECT DISTINCT mal_id FROM {table}
                WHERE (http_status BETWEEN 200 AND 299
                       AND extracted_at >= now()::TIMESTAMP - INTERVAL ({refresh_days}) DAY)
                      {not_found_clause}
            )
            , mine AS (
                -- prioridade: animes da sua lista entram primeiro na fila, para o painel
                -- "Meu perfil" e as recomendações ficarem prontos em minutos, não em horas
                SELECT DISTINCT TRY_CAST(payload->>'$.node.id' AS INTEGER) AS mal_id
                FROM bronze.mal_user_animelist
            )
            SELECT c.mal_id FROM candidates c
            LEFT JOIN done d USING (mal_id)
            LEFT JOIN mine m USING (mal_id)
            WHERE d.mal_id IS NULL
            ORDER BY (m.mal_id IS NULL), c.mal_id
        """
        if limit:
            sql += f" LIMIT {int(limit)}"
        with self.lock:
            return [r[0] for r in self.con.execute(sql).fetchall()]

    def known_mal_ids_sql(self) -> str:
        """Universo de IDs conhecidos: descobertos via MAL + sua lista + presentes no manami."""
        return """
            SELECT DISTINCT mal_id FROM bronze.mal_anime_discovery
            UNION
            SELECT DISTINCT TRY_CAST(payload->>'$.node.id' AS INTEGER) FROM bronze.mal_user_animelist
            UNION
            SELECT DISTINCT TRY_CAST(regexp_extract(s.src, 'myanimelist\\.net/anime/(\\d+)', 1) AS INTEGER)
            FROM (SELECT unnest(from_json(payload->'sources', '["VARCHAR"]')) AS src FROM bronze.manami_anime) s
            WHERE s.src LIKE '%myanimelist.net/anime/%'
        """

    def done_ids(self, table: str, refresh_days: int) -> set[int]:
        """IDs já resolvidos em `table`: sucesso recente ou 404 (não existe na fonte)."""
        sql = f"""
            SELECT DISTINCT mal_id FROM {table}
            WHERE (http_status BETWEEN 200 AND 299
                   AND extracted_at >= now()::TIMESTAMP - INTERVAL ({int(refresh_days)}) DAY)
               OR http_status = 404
        """
        with self.lock:
            return {r[0] for r in self.con.execute(sql).fetchall()}

    def known_manga_ids_sql(self) -> str:
        return "SELECT DISTINCT mal_id FROM bronze.mal_manga_discovery"

    def kitsu_candidates(self) -> dict[int, int]:
        """mal_id → kitsu_id para animes seriados (TV/ONA/OVA/especiais) com detalhe do MAL.

        O vínculo vem do anime-offline-database; filmes, clipes e comerciais ficam de fora porque
        têm um único "episódio" e não agregam nada na tabela de episódios.
        """
        sql = """
            WITH manami AS (
                SELECT
                    TRY_CAST(regexp_extract(list_filter(from_json(payload->'sources', '["VARCHAR"]'),
                        lambda s: s LIKE '%myanimelist.net/anime/%')[1], 'anime/(\\d+)', 1) AS INTEGER) AS mal_id,
                    TRY_CAST(regexp_extract(list_filter(from_json(payload->'sources', '["VARCHAR"]'),
                        lambda s: s LIKE '%kitsu.%/anime/%')[1], 'anime/(\\d+)', 1) AS INTEGER) AS kitsu_id
                FROM bronze.manami_anime
                QUALIFY dataset_date IS NOT DISTINCT FROM max(dataset_date) OVER ()
            ),
            mal AS (
                SELECT mal_id, payload->>'$.media_type' AS media_type
                FROM bronze.mal_anime WHERE http_status = 200
                QUALIFY row_number() OVER (PARTITION BY mal_id ORDER BY extracted_at DESC) = 1
            )
            SELECT m.mal_id, any_value(m.kitsu_id)
            FROM manami m JOIN mal USING (mal_id)
            WHERE m.kitsu_id IS NOT NULL AND mal.media_type IN ('tv', 'ona', 'ova', 'special', 'tv_special')
            GROUP BY m.mal_id
        """
        with self.lock:
            return dict(self.con.execute(sql).fetchall())

    def fetched_mal_ids_sql(self) -> str:
        """IDs com detalhe do MAL extraído com sucesso (base para o enriquecimento via Jikan)."""
        return "SELECT DISTINCT mal_id FROM bronze.mal_anime WHERE http_status = 200"

    def table_counts(self) -> list[tuple[str, int]]:
        tables = self.con.execute(
            "SELECT table_schema || '.' || table_name FROM information_schema.tables "
            "WHERE table_schema IN ('bronze', 'meta') ORDER BY 1"
        ).fetchall()
        return [(t, self.con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]) for (t,) in tables]


class RunContext:
    def __init__(self, wh: Warehouse, command: str) -> None:
        self.wh = wh
        self.command = command
        self.run_id = f"{utcnow():%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}"
        self.rows_written = 0
        self.notes: str | None = None

    def add(self, n: int) -> None:
        self.rows_written += n


def to_json(obj) -> str | None:
    return None if obj is None else json.dumps(obj, ensure_ascii=False)
