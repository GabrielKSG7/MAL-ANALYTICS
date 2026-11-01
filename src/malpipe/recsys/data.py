"""Carga das interações do DuckDB em matrizes esparsas."""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import numpy as np
import pandas as pd
from scipy import sparse


@dataclass
class Interactions:
    """Matriz usuário × item de notas explícitas.

    `raw`: nota 1–10. `centered`: nota menos a média do usuário (remove viés de escala).
    Índices inteiros são gerados no SQL (dense_rank) para não carregar milhões de hashes no Python.
    """

    raw: sparse.csr_matrix
    centered: sparse.csr_matrix
    item_ids: np.ndarray  # coluna → mal_id

    @property
    def n_users(self) -> int:
        return self.raw.shape[0]

    @property
    def n_items(self) -> int:
        return self.raw.shape[1]

    def item_index(self) -> dict[int, int]:
        return {int(m): i for i, m in enumerate(self.item_ids)}


def center_rows(raw: sparse.csr_matrix) -> sparse.csr_matrix:
    raw = raw.tocsr().astype(np.float32)
    counts = np.diff(raw.indptr)
    sums = np.asarray(raw.sum(axis=1)).ravel()
    means = np.divide(sums, counts, out=np.zeros_like(sums), where=counts > 0)
    centered = raw.copy()
    centered.data = centered.data - np.repeat(means, counts).astype(np.float32)
    # nota exatamente igual à média vira 0 e some do esparso; guardamos um epsilon para não perder o "viu"
    centered.data[centered.data == 0] = 1e-3
    return centered


def load_interactions(
    con: duckdb.DuckDBPyConnection,
    min_user_ratings: int = 5,
    min_item_ratings: int = 5,
    max_users: int | None = None,
) -> Interactions:
    user_sample = (
        f"AND user_key IN (SELECT user_key FROM users ORDER BY hash(user_key) LIMIT {int(max_users)})"
        if max_users
        else ""
    )
    df: pd.DataFrame = con.execute(
        f"""
        WITH rated AS (
            SELECT user_key, mal_id, user_score
            FROM core.fct_user_rating
            WHERE user_score IS NOT NULL
        ),
        items AS (
            SELECT mal_id FROM rated GROUP BY mal_id HAVING count(*) >= {int(min_item_ratings)}
        ),
        users AS (
            SELECT user_key FROM rated JOIN items USING (mal_id)
            GROUP BY user_key HAVING count(*) >= {int(min_user_ratings)}
        ),
        filtered AS (
            SELECT r.* FROM rated r
            JOIN items USING (mal_id)
            WHERE user_key IN (SELECT user_key FROM users) {user_sample}
        )
        SELECT
            (dense_rank() OVER (ORDER BY user_key) - 1)::INTEGER AS u,
            (dense_rank() OVER (ORDER BY mal_id) - 1)::INTEGER   AS i,
            mal_id::INTEGER                                     AS mal_id,
            user_score::FLOAT                                   AS score
        FROM filtered
        """
    ).df()
    if df.empty:
        raise RuntimeError("core.fct_user_rating sem interações suficientes — rode o dbt antes.")

    n_users, n_items = int(df.u.max()) + 1, int(df.i.max()) + 1
    raw = sparse.csr_matrix((df.score.to_numpy(), (df.u.to_numpy(), df.i.to_numpy())), shape=(n_users, n_items))
    item_ids = df.drop_duplicates("i").sort_values("i").mal_id.to_numpy()
    return Interactions(raw=raw, centered=center_rows(raw), item_ids=item_ids)


def load_item_features(con: duckdb.DuckDBPyConnection, item_ids: np.ndarray) -> sparse.csr_matrix:
    """Matriz item × feature (gêneros, tags, estúdio, origem, década) com TF-IDF e norma L2."""
    meta = con.execute(
        """
        SELECT mal_id, genres, tags, main_studio_name, source_material, decade, media_type
        FROM core.dim_anime
        """
    ).df()
    meta = meta.set_index("mal_id")

    vocab: dict[str, int] = {}
    rows, cols = [], []
    for row_idx, mal_id in enumerate(item_ids):
        if mal_id not in meta.index:
            continue
        m = meta.loc[mal_id]
        feats = set()
        for g in m.genres if isinstance(m.genres, (list, np.ndarray)) else []:
            feats.add(f"genre:{g}")
        for t in m.tags if isinstance(m.tags, (list, np.ndarray)) else []:
            feats.add(f"tag:{t}")
        for prefix, value in (
            ("studio", m.main_studio_name),
            ("source", m.source_material),
            ("decade", m.decade),
            ("media", m.media_type),
        ):
            if pd.notna(value):
                feats.add(f"{prefix}:{value}")
        for f in feats:
            rows.append(row_idx)
            cols.append(vocab.setdefault(f, len(vocab)))

    n_items = len(item_ids)
    binary = sparse.csr_matrix(
        (np.ones(len(rows), dtype=np.float32), (rows, cols)), shape=(n_items, max(len(vocab), 1))
    )
    df_counts = np.asarray((binary > 0).sum(axis=0)).ravel()
    idf = np.log((1 + n_items) / (1 + df_counts)) + 1
    tfidf = binary @ sparse.diags(idf.astype(np.float32))
    norms = np.sqrt(np.asarray(tfidf.multiply(tfidf).sum(axis=1)).ravel())
    norms[norms == 0] = 1
    return sparse.diags(1 / norms) @ tfidf
