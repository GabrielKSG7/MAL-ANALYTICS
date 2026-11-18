# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/); versões seguem
[SemVer](https://semver.org/lang/pt-BR/).

## [1.0.0] — 2026-11-18

Primeira versão fechada. O escopo está no README (seção "Escopo da v1").

### Ingestão
- Cliente HTTP educado (rate limit, backoff com jitter, `Retry-After`, 404 definitivo, circuit breaker; GET e POST).
- Bronze append-only com JSON cru e checkpoint derivado do próprio bronze; observabilidade em `meta.runs`.
- Fontes: MAL API v2 (anime, mangá, lista do usuário), AniList GraphQL (elenco, staff, relações em lote),
  Kitsu (episódios), anime-offline-database, Jikan (opcional) e Kaggle (opcional).
- `malpipe ecosystem`: carga paralela por host; `check-sources`, `merge`, `status`.
- `malpipe weekly`: coleta semanal das temporadas recentes e da lista, com agendamento no Windows
  (`scripts/register-weekly-task.ps1`).

### Modelagem (dbt + DuckDB)
- 63 modelos em staging → intermediate → core → analytics, snapshot SCD2, fato incremental, contracts,
  exposures, testes genéricos próprios e unit tests.
- Franquias por CTE recursiva, nota bayesiana, polarização, papéis de staff normalizados, ligação
  mangá × anime (MAL + AniList).
- JSONs grandes lidos uma única vez (`from_json` tipado): build com 30 mil animes e 86 mil mangás em
  menos de 1,5 GB.

### Entregas
- Recomendador (popularidade, item-kNN, SVD, conteúdo, híbrido) com avaliação offline e explicações.
- Dashboard Streamlit com 10 abas; `malpipe publish` + 38 consultas para o DBeaver.
- Painel público no GitHub Pages gerado por `malpipe site`.
- 12 achados com dados reais no README; ADRs 001–006; lineage gerado do manifest.

### Qualidade
- 40 testes Python, ruff, CI com o pipeline inteiro em dados sintéticos + manami real, verificação das
  consultas SQL, do dashboard (AppTest), do painel público e do lineage.
