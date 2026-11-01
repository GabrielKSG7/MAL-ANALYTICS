from __future__ import annotations

import numpy as np
from scipy import sparse

from malpipe.recsys.data import center_rows
from malpipe.recsys.evaluate import holdout_split, precision_recall_ndcg
from malpipe.recsys.models import (
    HybridRecommender,
    ItemKNNRecommender,
    PopularityRecommender,
    SVDRecommender,
    top_k,
)


def _two_taste_groups(n_users=60, seed=0):
    """Metade dos usuários ama os itens 0–4 e odeia 5–9; a outra metade, o contrário."""
    rng = np.random.default_rng(seed)
    rows, cols, vals = [], [], []
    for u in range(n_users):
        likes = range(0, 5) if u % 2 == 0 else range(5, 10)
        for i in range(10):
            if rng.random() < 0.7:
                rows.append(u)
                cols.append(i)
                vals.append(9.0 if i in likes else 3.0)
    return sparse.csr_matrix((vals, (rows, cols)), shape=(n_users, 10))


def test_metrics_perfect_and_empty():
    p, r, n = precision_recall_ndcg(np.array([1, 2, 3]), {1, 2, 3}, k=3)
    assert (p, r, round(n, 6)) == (1.0, 1.0, 1.0)
    assert precision_recall_ndcg(np.array([7, 8]), {1}, k=2) == (0.0, 0.0, 0.0)


def test_top_k_excludes_seen_items():
    scores = np.array([[0.9, 0.8, 0.1, 0.5]])
    seen = sparse.csr_matrix(([1.0], ([0], [0])), shape=(1, 4))
    assert top_k(scores, seen, k=2).tolist() == [[1, 3]]


def test_center_rows_removes_user_bias():
    raw = sparse.csr_matrix(np.array([[10, 8, 0], [4, 0, 2]], dtype=float))
    centered = center_rows(raw).toarray()
    assert np.allclose(centered[0, :2], [1, -1]) and np.allclose(centered[1, [0, 2]], [1, -1])


def test_item_knn_learns_taste_groups():
    centered = center_rows(_two_taste_groups())
    knn = ItemKNNRecommender(neighbors=4, shrinkage=0).fit(centered)
    neighbors_of_0 = {j for j, _ in knn.similar_items(0, top=4)}
    assert neighbors_of_0 <= {1, 2, 3, 4}  # vizinhos de um item do grupo A são do grupo A

    # usuário novo que só deu 10 para o item 0 deve receber itens do grupo A
    new_user = sparse.csr_matrix(([1.0], ([0], [0])), shape=(1, 10))
    recs = top_k(knn.score(new_user), new_user, k=3)[0]
    assert set(recs.tolist()) <= {1, 2, 3, 4}
    assert knn.explain(new_user, int(recs[0])) == 0


def test_svd_and_hybrid_beat_or_match_popularity_on_structured_data():
    raw = _two_taste_groups(n_users=200)
    split = holdout_split(raw, relevant_threshold=8, min_relevant=2, max_test_users=200)

    def ndcg(model):
        model.fit(split.train_centered)
        users = split.test_users
        recs = top_k(model.score(split.train_centered[users]), split.train_raw[users], k=3)
        pairs = zip(users, recs, strict=True)
        return np.mean([precision_recall_ndcg(r, split.held_out[int(u)], 3)[2] for u, r in pairs])

    pop = ndcg(PopularityRecommender())
    assert ndcg(SVDRecommender(factors=2)) > pop
    assert ndcg(HybridRecommender([ItemKNNRecommender(4, 0), PopularityRecommender()], [0.8, 0.2])) > pop


def test_holdout_hides_only_relevant_items():
    raw = _two_taste_groups()
    split = holdout_split(raw, relevant_threshold=8, min_relevant=2)
    for u, items in split.held_out.items():
        for i in items:
            assert raw[u, i] >= 8 and split.train_raw[u, i] == 0
    assert split.train_raw.nnz == raw.nnz - sum(len(v) for v in split.held_out.values())
