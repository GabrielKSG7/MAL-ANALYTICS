"""Carga do dataset de interações usuário × anime do Kaggle.

Dataset principal: "Anime Recommendation Database 2020" (hernan4444)
https://www.kaggle.com/datasets/hernan4444/anime-recommendation-database-2020

    kaggle datasets download -d hernan4444/anime-recommendation-database-2020 -f animelist.csv -p data/raw

animelist.csv → user_id, anime_id, score, watching_status, watched_episodes
(~109 milhões de linhas, ~2 GB). Carregamos direto com o leitor de CSV do DuckDB, que é
paralelo e não passa os dados pelo Python.

watching_status: 1=watching, 2=completed, 3=on_hold, 4=dropped, 6=plan_to_watch
"""

from __future__ import annotations

import logging
from pathlib import Path

from malpipe.warehouse import RunContext, Warehouse, utcnow

log = logging.getLogger(__name__)

EXPECTED_COLUMNS = {"user_id", "anime_id", "score", "watching_status", "watched_episodes"}


def load_animelist(wh: Warehouse, run: RunContext, csv_path: Path, sample_users: int | None = None) -> int:
    """Carrega animelist.csv no bronze.

    `sample_users` permite carregar só N usuários (amostragem determinística por hash),
    útil para desenvolver localmente sem os 109M de linhas.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"{csv_path} não encontrado. Veja o comando de download no docstring.")

    header = wh.con.execute(
        "SELECT * FROM read_csv(?, header = true, sample_size = 1000) LIMIT 0", [str(csv_path)]
    ).description
    columns = {c[0] for c in header}
    missing = EXPECTED_COLUMNS - columns
    if missing:
        raise ValueError(f"CSV sem as colunas esperadas: {missing}")

    # Reprocessar o mesmo arquivo substitui a carga anterior (idempotente por arquivo).
    wh.con.execute("DELETE FROM bronze.kaggle_animelist WHERE source_file = ?", [csv_path.name])

    user_filter = ""
    if sample_users:
        user_filter = f"""
            WHERE user_id IN (
                SELECT user_id FROM (SELECT DISTINCT user_id FROM src)
                ORDER BY hash(user_id) LIMIT {int(sample_users)}
            )
        """

    before = wh.con.execute("SELECT count(*) FROM bronze.kaggle_animelist").fetchone()[0]
    wh.con.execute(
        f"""
        INSERT INTO bronze.kaggle_animelist
        WITH src AS (
            SELECT
                CAST(user_id AS BIGINT)          AS user_id,
                CAST(anime_id AS INTEGER)        AS anime_id,
                CAST(score AS INTEGER)           AS score,
                CAST(watching_status AS INTEGER) AS watching_status,
                CAST(watched_episodes AS INTEGER) AS watched_episodes
            FROM read_csv(?, header = true)
        )
        SELECT user_id, anime_id, score, watching_status, watched_episodes, ?, ?, ?
        FROM src {user_filter}
        """,
        [str(csv_path), csv_path.name, utcnow(), run.run_id],
    )
    written = wh.con.execute("SELECT count(*) FROM bronze.kaggle_animelist").fetchone()[0] - before
    run.add(written)
    log.info("kaggle: %s linhas carregadas de %s", written, csv_path.name)
    return written
