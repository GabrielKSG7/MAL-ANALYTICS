# ADR 004 — Recomendador: modelos simples, bem avaliados

**Status:** aceito · **Data:** 2026-11

## Contexto

Queremos recomendar animes para a lista pessoal do autor e mostrar, de forma honesta, o quanto cada
abordagem funciona. Bibliotecas como `implicit`/`surprise` têm builds problemáticos em algumas
plataformas; o volume (≈300k usuários × 17k itens) cabe em matrizes esparsas do SciPy.

## Decisão

Implementar com numpy/scipy, com interface comum `fit(train)` / `score(user_rows)`:

| Modelo | Ideia | Papel |
|---|---|---|
| `popularity` | mais bem avaliados no geral | **baseline** que todo modelo precisa enfrentar |
| `item_knn` | cosseno item-item sobre notas centralizadas, com *shrinkage* e top-N vizinhos, calculado em blocos | colaborativo explicável ("porque você deu 9 para X") |
| `svd` | SVD truncado + *fold-in* (`r · V · Vᵀ`) | fatoração latente |
| `content` | TF-IDF de gêneros, tags (manami), estúdio, origem, década | cold start e diversidade |
| `hybrid` | soma ponderada de scores padronizados (kNN 0.5 + conteúdo 0.2 + popularidade 0.3) | modelo final |

`score(user_rows)` recebe as **linhas** do usuário (não um índice), o que permite *fold-in*:
recomendar para a sua lista sem retreinar.

**Avaliação offline:** para cada usuário de teste, escondemos 20% dos itens avaliados com nota ≥ 8 e
medimos precision/recall/NDCG@10, **cobertura de catálogo** e **popularidade média dos recomendados**
(novidade). Avaliação externa extra: quanto os vizinhos do kNN coincidem com as recomendações votadas
pela comunidade no Jikan.

## Consequências

- Em holdout, popularidade é um baseline difícil de bater (viés de popularidade) — por isso reportamos
  cobertura e novidade junto: o híbrido empata/vence em precisão recomendando de uma fração muito maior
  do catálogo.
- O Kaggle é de 2020: títulos posteriores só entram via conteúdo (o híbrido cobre isso parcialmente).
- Próximos passos possíveis: ALS para feedback implícito (status `plan_to_watch`/`dropped`), embeddings
  de sinopse para o modelo de conteúdo, avaliação temporal.
