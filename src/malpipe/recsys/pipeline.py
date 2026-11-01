"""Orquestra: carregar → avaliar modelos → treinar no conjunto completo → recomendar → gravar no DuckDB.

Saídas (schema `ml`):
- ml.model_metrics           métricas offline de cada modelo (precision/recall/NDCG@k, cobertura, novidade)
- ml.community_agreement     concordância dos vizinhos do item-kNN com as recomendações da comunidade (Jikan)
- ml.similar_anime           top-10 animes similares para cada anime (item-kNN)
- ml.recommendations_for_user  recomendações para a sua lista, com explicação ("porque você deu 9 para X")
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table
from scipy import sparse

from malpipe.recsys.data import load_interactions, load_item_features
from malpipe.recsys.evaluate import community_agreement, evaluate, holdout_split
from malpipe.recsys.models import (
    ContentRecommender,
    HybridRecommender,
    ItemKNNRecommender,
    PopularityRecommender,
    SVDRecommender,
    top_k,
)


def _write(con: duckdb.DuckDBPyConnection, name: str, df: pd.DataFrame) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS ml")
    con.register("_df", df)
    con.execute(f"CREATE OR REPLACE TABLE ml.{name} AS SELECT * FROM _df")
    con.unregister("_df")


def _user_rows(con, username: str, item_index: dict[int, int], n_items: int):
    """Monta o vetor (centralizado) da sua lista no espaço de itens do modelo."""
    mine = con.execute(
        "SELECT mal_id, user_score, list_status FROM core.fct_my_list WHERE username = ?", [username]
    ).df()
    if mine.empty:
        return None, None, None
    rated = mine[mine.user_score.notna() & mine.mal_id.isin(item_index.keys())]
    if rated.empty:
        return None, None, mine
    cols = rated.mal_id.map(item_index).to_numpy()
    scores = rated.user_score.to_numpy(dtype=np.float32)
    centered = scores - scores.mean()
    centered[centered == 0] = 1e-3
    row = sparse.csr_matrix((centered, (np.zeros(len(cols)), cols)), shape=(1, n_items))
    seen_status = {"completed", "watching", "on_hold", "dropped"}
    seen_cols = mine[mine.list_status.isin(seen_status) & mine.mal_id.isin(item_index.keys())].mal_id.map(item_index)
    seen = sparse.csr_matrix(
        (np.ones(len(seen_cols)), (np.zeros(len(seen_cols)), seen_cols.to_numpy())), shape=(1, n_items)
    )
    return row, seen, mine


def run(
    duckdb_path: Path,
    username: str | None = None,
    k: int = 10,
    max_users: int | None = None,
    console: Console | None = None,
) -> dict:
    console = console or Console()
    con = duckdb.connect(str(duckdb_path))
    trained_at = datetime.now(UTC).replace(tzinfo=None)

    data = load_interactions(con, max_users=max_users)
    features = load_item_features(con, data.item_ids)
    console.print(f"interações: {data.raw.nnz:,} | usuários: {data.n_users:,} | itens: {data.n_items:,}")

    # popularidade (percentil) de cada item, para medir novidade das recomendações
    counts = np.diff(data.raw.tocsc().indptr)
    pop_pct = pd.Series(counts).rank(pct=True).to_numpy()

    knn_params = {"neighbors": 100, "shrinkage": 25}
    svd_factors = int(np.clip(data.n_items // 20, 8, 64))

    def make_hybrid():
        # Híbrido final: colaborativo + conteúdo + um pouco de popularidade.
        # A popularidade sozinha é um baseline forte em holdout (viés de popularidade), mas
        # cobre uma fração mínima do catálogo; o híbrido empata/vence em precisão com
        # cobertura muitas vezes maior.
        return HybridRecommender(
            [ItemKNNRecommender(**knn_params), ContentRecommender(features), PopularityRecommender()],
            [0.5, 0.2, 0.3],
            name="hybrid",
        )

    def make_models():
        return [
            PopularityRecommender(),
            ItemKNNRecommender(**knn_params),
            SVDRecommender(factors=svd_factors),
            ContentRecommender(features),
            make_hybrid(),
        ]

    # ---------- avaliação offline
    split = holdout_split(data.raw)
    metrics = [evaluate(m, split, k=k, item_popularity=pop_pct) for m in make_models()]
    metrics_df = pd.DataFrame(metrics).assign(trained_at=trained_at, n_items=data.n_items, n_users=data.n_users)
    _write(con, "model_metrics", metrics_df)

    table = Table(title=f"Avaliação offline (holdout, top-{k})")
    for col in ["model", f"precision_at_{k}", f"recall_at_{k}", f"ndcg_at_{k}", "catalog_coverage",
                "avg_popularity_percentile"]:  # fmt: skip
        table.add_column(col)
    for m in metrics:
        table.add_row(
            m["model"],
            *(f"{m[c]:.4f}" for c in [f"precision_at_{k}", f"recall_at_{k}", f"ndcg_at_{k}", "catalog_coverage"]),
            f"{m['avg_popularity_percentile']:.3f}",
        )
    console.print(table)

    # ---------- modelo final no conjunto completo
    hybrid = make_hybrid().fit(data.centered)
    knn = hybrid.models[0]

    titles = dict(con.execute("SELECT mal_id, title FROM core.dim_anime").fetchall())
    similar = []
    for i, mal_id in enumerate(data.item_ids):
        for rank, (j, sim) in enumerate(knn.similar_items(i, top=10), start=1):
            similar.append(
                {
                    "mal_id": int(mal_id),
                    "rank": rank,
                    "similar_mal_id": int(data.item_ids[j]),
                    "similarity": round(sim, 5),
                    "similar_title": titles.get(int(data.item_ids[j])),
                }  # fmt: skip
            )
    _write(con, "similar_anime", pd.DataFrame(similar))

    # ---------- concordância com a comunidade (Jikan)
    community_df = con.execute("SELECT mal_id, recommended_mal_id FROM staging.stg_jikan__recommendations").df()
    agreement = {}
    if not community_df.empty:
        community = community_df.groupby("mal_id").recommended_mal_id.apply(set).to_dict()
        agreement = community_agreement(knn, data.item_ids, community)
        _write(con, "community_agreement", pd.DataFrame([agreement | {"trained_at": trained_at}]))
        console.print(f"concordância com recomendações da comunidade (Jikan): {agreement}")

    # ---------- recomendações para a sua lista
    recs_out = []
    if username:
        index = data.item_index()
        row, seen, mine = _user_rows(con, username, index, data.n_items)
        if row is None:
            console.print(f"[yellow]sem notas de '{username}' que casem com o catálogo do modelo[/]")
        else:
            ptw = set(mine[mine.list_status == "plan_to_watch"].mal_id.astype(int))
            for model in (hybrid, knn):
                top = top_k(model.score(row), exclude=seen, k=max(k, 20))[0]
                for rank, j in enumerate(top, start=1):
                    because = knn.explain(row, int(j))
                    recs_out.append({
                        "username": username,
                        "model": model.name,
                        "rank": rank,
                        "mal_id": int(data.item_ids[j]),
                        "title": titles.get(int(data.item_ids[j])),
                        "already_in_plan_to_watch": int(data.item_ids[j]) in ptw,
                        "because_you_liked_mal_id": int(data.item_ids[because]) if because is not None else None,
                        "because_you_liked": titles.get(int(data.item_ids[because])) if because is not None else None,
                        "generated_at": trained_at,
                    })  # fmt: skip
            _write(con, "recommendations_for_user", pd.DataFrame(recs_out))
            best = [r for r in recs_out if r["model"] == hybrid.name][:5]
            console.print(f"Top 5 para {username}: " + "; ".join(r["title"] or str(r["mal_id"]) for r in best))

    con.close()
    return {"metrics": metrics, "agreement": agreement, "n_recommendations": len(recs_out)}
