# ADR 002 — Bronze append-only com JSON cru, e o bronze como checkpoint

**Status:** aceito · **Data:** 2026-11

## Contexto

As APIs são lentas de propósito (≈1 req/s). Uma carga completa do MAL leva horas. Precisamos:
(1) não perder progresso se o processo cair; (2) poder mudar a modelagem sem extrair de novo;
(3) acompanhar a evolução de nota/membros ao longo do tempo.

## Decisão

- Cada resposta vira **uma linha nova** no bronze com o **JSON inteiro**, `http_status`, `error`,
  `extracted_at` e `run_id`. Nada é atualizado nem apagado.
- Respostas de erro também são gravadas (payload nulo), inclusive 404.
- A fila de extração é **calculada a partir do bronze**: candidatos − sucesso recente − 404.
  Não existe uma tabela de estado separada.
- O staging aplica "última extração vence" (`QUALIFY row_number() ... = 1`) quando precisa do estado atual;
  a fato `fct_anime_metrics_snapshot` usa **todas** as extrações para formar a série temporal.

## Consequências

- ✅ Reprocessar = `dbt build --full-refresh`, sem nenhuma chamada de rede.
- ✅ Campo novo na API? Já está no JSON guardado; basta expor no staging.
- ✅ Histórico de graça: a cada semana, o `mart_anime_trending` compara com a anterior.
- ✅ Checkpoint impossível de dessincronizar (é o próprio dado).
- ⚠️ O bronze cresce ~30 mil linhas por semana de refresh completo (≈ dezenas de MB/ano em DuckDB comprimido).
  Se necessário, compactar extrações antigas mantendo 1 por mês.
