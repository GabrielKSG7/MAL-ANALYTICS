"""Avaliação offline: holdout por usuário + métricas de ranking."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse

from malpipe.recsys.data import center_rows
from malpipe.recsys.models import top_k


@dataclass
class Split:
    train_raw: sparse.csr_matrix
    train_centered: sparse.csr_matrix
    test_users: np.ndarray
    held_out: dict[int, set[int]]  # usuário → itens relevantes escondidos


def holdout_split(
    raw: sparse.csr_matrix,
    relevant_threshold: float = 8.0,
    test_fraction: float = 0.2,
    min_relevant: int = 3,
    max_test_users: int = 2000,
    seed: int = 42,
) -> Split:
    """Para cada usuário elegível, esconde ~20% dos itens que ele avaliou com nota ≥ limiar.
    O modelo treina sem eles e precisa "reencontrá-los" no top-k."""
    rng = np.random.default_rng(seed)
    raw = raw.tocsr()
    n_items = raw.shape[1]
    held_out: dict[int, set[int]] = {}

    # elegíveis: avaliaram itens suficientes e têm itens "relevantes" para esconder
    relevant_mask = raw.copy()
    relevant_mask.data = (relevant_mask.data >= relevant_threshold).astype(np.int8)
    n_relevant = np.asarray(relevant_mask.sum(axis=1)).ravel()
    n_rated = np.diff(raw.indptr)
    eligible = np.flatnonzero((n_relevant >= min_relevant) & (n_rated >= 2 * min_relevant))
    chosen = rng.permutation(eligible)[:max_test_users]

    hide_keys = []
    for u in chosen:
        lo, hi = raw.indptr[u], raw.indptr[u + 1]
        items, scores = raw.indices[lo:hi], raw.data[lo:hi]
        relevant = items[scores >= relevant_threshold]
        n_hide = max(1, int(round(len(relevant) * test_fraction)))
        hide = rng.choice(relevant, n_hide, replace=False)
        held_out[int(u)] = {int(i) for i in hide}
        hide_keys.extend(int(u) * n_items + int(i) for i in hide)

    coo = raw.tocoo()
    keys = coo.row.astype(np.int64) * n_items + coo.col
    keep = ~np.isin(keys, np.array(hide_keys, dtype=np.int64))
    train_raw = sparse.csr_matrix((coo.data[keep], (coo.row[keep], coo.col[keep])), shape=raw.shape)
    return Split(
        train_raw=train_raw,
        train_centered=center_rows(train_raw),
        test_users=np.array(sorted(held_out), dtype=np.int64),
        held_out=held_out,
    )


def precision_recall_ndcg(recs: np.ndarray, truth: set[int], k: int) -> tuple[float, float, float]:
    recs = recs[:k]
    hits = np.array([1.0 if r in truth else 0.0 for r in recs])
    precision = hits.sum() / k
    recall = hits.sum() / len(truth) if truth else 0.0
    discounts = 1 / np.log2(np.arange(2, len(recs) + 2))
    dcg = float((hits * discounts).sum())
    idcg = float(discounts[: min(len(truth), k)].sum())
    return precision, recall, (dcg / idcg if idcg else 0.0)


def evaluate(model, split: Split, k: int = 10, batch: int = 512, item_popularity: np.ndarray | None = None) -> dict:
    model.fit(split.train_centered)
    precisions, recalls, ndcgs = [], [], []
    recommended: set[int] = set()
    pop_of_recs: list[float] = []
    for start in range(0, len(split.test_users), batch):
        users = split.test_users[start : start + batch]
        rows = split.train_centered[users]
        recs = top_k(model.score(rows), exclude=split.train_raw[users], k=k)
        for u, r in zip(users, recs, strict=True):
            p, rc, n = precision_recall_ndcg(r, split.held_out[int(u)], k)
            precisions.append(p)
            recalls.append(rc)
            ndcgs.append(n)
            recommended.update(int(x) for x in r)
            if item_popularity is not None:
                pop_of_recs.extend(item_popularity[r].tolist())
    n_items = split.train_raw.shape[1]
    return {
        "model": model.name,
        "k": k,
        f"precision_at_{k}": float(np.mean(precisions)),
        f"recall_at_{k}": float(np.mean(recalls)),
        f"ndcg_at_{k}": float(np.mean(ndcgs)),
        "catalog_coverage": len(recommended) / n_items,
        # novidade: popularidade média (percentil) dos itens recomendados — menor = menos óbvio
        "avg_popularity_percentile": float(np.mean(pop_of_recs)) if pop_of_recs else None,
        "n_test_users": int(len(split.test_users)),
    }


def community_agreement(knn, item_ids: np.ndarray, community: dict[int, set[int]], top: int = 10) -> dict:
    """Quanto os vizinhos do item-kNN coincidem com as recomendações votadas pela comunidade (Jikan)."""
    index = {int(m): i for i, m in enumerate(item_ids)}
    hits, precisions, evaluated = 0, [], 0
    for mal_id, recs in community.items():
        if mal_id not in index:
            continue
        recs_in_space = {r for r in recs if r in index}
        if not recs_in_space:
            continue
        evaluated += 1
        neighbors = {int(item_ids[j]) for j, _ in knn.similar_items(index[mal_id], top)}
        overlap = len(neighbors & recs_in_space)
        hits += overlap > 0
        precisions.append(overlap / top)
    return {
        "items_evaluated": evaluated,
        f"hit_rate_at_{top}": hits / evaluated if evaluated else None,
        f"precision_at_{top}": float(np.mean(precisions)) if precisions else None,
    }
