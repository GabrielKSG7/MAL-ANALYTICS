# ADR 001 — DuckDB como warehouse

**Status:** aceito · **Data:** 2026-11

## Contexto

O maior volume do projeto é o dataset do Kaggle (~109M linhas, ~2 GB em CSV). O restante (≈30 mil
animes com histórico semanal, elencos, distribuições) é pequeno. O projeto é pessoal, roda num
notebook, e precisa ser reproduzível por qualquer pessoa que clonar o repositório.

## Decisão

Usar **DuckDB** (arquivo único `data/mal.duckdb`) como warehouse e **dbt-duckdb** para a modelagem.

## Consequências

- ✅ Zero infraestrutura: `pip install` e pronto; o CI roda o pipeline inteiro em segundos.
- ✅ `read_csv` paralelo carrega o Kaggle sem passar pelo Python; funções de JSON (`->>`, `from_json`),
  listas (`list_filter`, `unnest`) e `QUALIFY` deixam o staging curto e legível.
- ✅ CTE recursiva para o grafo de franquias, `arg_max`, `quantile_cont`, `percent_rank` nativos.
- ⚠️ Um escritor por vez: dashboard aberto em modo leitura bloqueia escrita — documentado no runbook.
- ⚠️ Não é multiusuário. Se o projeto virar serviço, migrar para Postgres/MotherDuck/BigQuery é trocar
  o adapter do dbt; os modelos usam SQL majoritariamente portável (as exceções — JSON e listas — estão
  concentradas no staging).
