"""Modelos de recomendação implementados com numpy/scipy (sem dependências pesadas).

Todos seguem a mesma interface:
    fit(train: csr usuários×itens [notas centralizadas]) -> self
    score(user_rows: csr n×itens [notas centralizadas]) -> ndarray n×itens

`score` recebe as linhas do usuário (e não um índice), o que permite "fold-in":
recomendar para alguém que não estava no treino — como a sua lista do MAL.
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import svds


def _l2_normalize_columns(m: sparse.csr_matrix) -> sparse.csc_matrix:
    m = m.tocsc().astype(np.float32)
    norms = np.sqrt(np.asarray(m.multiply(m).sum(axis=0)).ravel())
    norms[norms == 0] = 1
    return m @ sparse.diags(1 / norms)


class PopularityRecommender:
    """Baseline: recomenda o que mais gente avaliou bem. Todo modelo precisa vencer isto."""

    name = "popularity"

    def __init__(self, like_threshold: float = 0.0) -> None:
        self.like_threshold = like_threshold
        self.item_scores: np.ndarray | None = None

    def fit(self, train: sparse.csr_matrix) -> PopularityRecommender:
        liked = train.copy()
        liked.data = (liked.data > self.like_threshold).astype(np.float32)
        self.item_scores = np.asarray(liked.sum(axis=0)).ravel()
        return self

    def score(self, user_rows: sparse.csr_matrix) -> np.ndarray:
        return np.tile(self.item_scores, (user_rows.shape[0], 1))


class ItemKNNRecommender:
    """Filtragem colaborativa item-item com similaridade cosseno sobre notas centralizadas.

    - `shrinkage` reduz a similaridade de pares com poucos usuários em comum.
    - Mantém só os `neighbors` vizinhos mais próximos de cada item (matriz esparsa W).
    - Calcula em blocos de itens para caber em memória com dezenas de milhares de itens.
    """

    name = "item_knn"

    def __init__(self, neighbors: int = 50, shrinkage: float = 10.0, block_size: int = 1024) -> None:
        self.neighbors = neighbors
        self.shrinkage = shrinkage
        self.block_size = block_size
        self.W: sparse.csr_matrix | None = None

    def fit(self, train: sparse.csr_matrix) -> ItemKNNRecommender:
        n_items = train.shape[1]
        xn = _l2_normalize_columns(train)
        binary = train.copy().tocsc()
        binary.data = np.ones_like(binary.data, dtype=np.float32)
        k = min(self.neighbors, n_items - 1)

        rows, cols, vals = [], [], []
        for start in range(0, n_items, self.block_size):
            stop = min(start + self.block_size, n_items)
            sims = (xn[:, start:stop].T @ xn).toarray()
            if self.shrinkage > 0:
                co = (binary[:, start:stop].T @ binary).toarray()
                sims *= co / (co + self.shrinkage)
            for local, item in enumerate(range(start, stop)):
                sims[local, item] = 0.0  # sem auto-similaridade
            top = np.argpartition(-sims, k, axis=1)[:, :k]
            for local in range(stop - start):
                idx = top[local]
                v = sims[local, idx]
                keep = v > 0
                rows.extend([start + local] * int(keep.sum()))
                cols.extend(idx[keep].tolist())
                vals.extend(v[keep].tolist())
        self.W = sparse.csr_matrix((vals, (rows, cols)), shape=(n_items, n_items), dtype=np.float32)
        return self

    def score(self, user_rows: sparse.csr_matrix) -> np.ndarray:
        return np.asarray((user_rows @ self.W.T).todense())

    def similar_items(self, item: int, top: int = 10) -> list[tuple[int, float]]:
        row = self.W.getrow(item)
        order = np.argsort(-row.data)[:top]
        return [(int(row.indices[o]), float(row.data[o])) for o in order]

    def explain(self, user_row: sparse.csr_matrix, item: int) -> int | None:
        """Item já avaliado pelo usuário que mais contribuiu para a recomendação de `item`."""
        contrib = self.W.getrow(item).multiply(user_row)
        if contrib.nnz == 0:
            return None
        contrib = contrib.tocsr()
        return int(contrib.indices[np.argmax(contrib.data)])


class SVDRecommender:
    """Fatoração de matriz (SVD truncado) sobre notas centralizadas, com fold-in:
    score = r · V · Vᵀ, onde V são os fatores latentes dos itens."""

    name = "svd"

    def __init__(self, factors: int = 64, seed: int = 42) -> None:
        self.factors = factors
        self.seed = seed
        self.V: np.ndarray | None = None

    def fit(self, train: sparse.csr_matrix) -> SVDRecommender:
        k = max(2, min(self.factors, min(train.shape) - 1))
        rng = np.random.default_rng(self.seed)
        v0 = rng.standard_normal(min(train.shape)).astype(np.float64)
        _, _, vt = svds(train.astype(np.float64), k=k, v0=v0)
        self.V = vt.T.astype(np.float32)
        return self

    def score(self, user_rows: sparse.csr_matrix) -> np.ndarray:
        return np.asarray(user_rows @ self.V) @ self.V.T


class ContentRecommender:
    """Baseado em conteúdo: perfil do usuário = soma das features (TF-IDF) dos itens,
    ponderada pela nota centralizada. Funciona até para itens que ninguém avaliou."""

    name = "content"

    def __init__(self, item_features: sparse.csr_matrix) -> None:
        self.F = item_features.tocsr().astype(np.float32)

    def fit(self, train: sparse.csr_matrix) -> ContentRecommender:
        return self

    def score(self, user_rows: sparse.csr_matrix) -> np.ndarray:
        profiles = user_rows @ self.F  # n × features
        return np.asarray((profiles @ self.F.T).todense())


class HybridRecommender:
    """Combina modelos padronizando os scores por usuário (z-score) antes de somar com pesos."""

    def __init__(self, models: list, weights: list[float], name: str = "hybrid") -> None:
        if len(models) != len(weights):
            raise ValueError("models e weights precisam ter o mesmo tamanho")
        self.models = models
        self.weights = weights
        self.name = name

    def fit(self, train: sparse.csr_matrix) -> HybridRecommender:
        for m in self.models:
            m.fit(train)
        return self

    @staticmethod
    def _standardize(s: np.ndarray) -> np.ndarray:
        mu = s.mean(axis=1, keepdims=True)
        sd = s.std(axis=1, keepdims=True)
        sd[sd == 0] = 1
        return (s - mu) / sd

    def score(self, user_rows: sparse.csr_matrix) -> np.ndarray:
        total = None
        for m, w in zip(self.models, self.weights, strict=True):
            part = w * self._standardize(m.score(user_rows))
            total = part if total is None else total + part
        return total


def top_k(scores: np.ndarray, exclude: sparse.csr_matrix | None, k: int) -> np.ndarray:
    """Índices dos k maiores scores por linha, ignorando itens em `exclude` (já vistos)."""
    scores = scores.astype(np.float64, copy=True)
    if exclude is not None:
        ex = exclude.tocoo()
        scores[ex.row, ex.col] = -np.inf
    k = min(k, scores.shape[1])
    part = np.argpartition(-scores, k - 1, axis=1)[:, :k]
    order = np.take_along_axis(scores, part, axis=1).argsort(axis=1)[:, ::-1]
    return np.take_along_axis(part, order, axis=1)
