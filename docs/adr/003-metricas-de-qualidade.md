# ADR 003 — Como medir "qualidade" além da média do MAL

**Status:** aceito · **Data:** 2026-11

## Contexto

A média do MAL tem dois problemas conhecidos: (1) títulos com poucos votos aparecem com notas extremas;
(2) a média esconde o formato da distribuição — um 7.5 de consenso é diferente de um 7.5 "ame ou odeie".

## Decisão

1. **Nota bayesiana** (`int_anime__weighted_score`), fórmula do Top 250 do IMDb:
   `WR = v/(v+m)·R + m/(v+m)·C`, com `C` = média global e `m` = percentil 75 de votos (configurável em
   `vars.bayes_prior_percentile`). Usada nos rankings de estúdio e de joias escondidas.
2. **Forma da distribuição** (`int_anime__score_dispersion`, a partir do Jikan):
   - desvio-padrão ponderado das notas;
   - entropia normalizada (0 = todos deram a mesma nota, 1 = uniforme);
   - **índice de polarização** `4 · share(9–10) · share(1–4)` — 0 quando um extremo está vazio,
     1 quando metade dá 9–10 e metade dá 1–4. Simples de explicar e de testar.
3. **Comportamento**: `completion_rate = completed / (completed + dropped)` e `drop_rate`.

## Consequências

- Propriedades matemáticas viram testes: a nota bayesiana fica sempre entre a média do anime e a média
  global (`assert_weighted_score_within_bounds`); o índice de polarização fica em [0, 1]; e há unit tests
  com casos extremos (distribuição 50/50 → índice 1; tudo numa nota → 0).
