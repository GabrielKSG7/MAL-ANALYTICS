# ADR 006 — Painel público como site estático gerado pelo pipeline

**Status:** aceito · **Data:** 2026-11

## Contexto

O dashboard em Streamlit lê o DuckDB local e é ótimo para explorar, mas não serve para quem chega por
um link (recrutadores, LinkedIn): precisaria de um servidor com o banco, e os termos da AniList e do MAL
não permitem republicar a base. O que se quer mostrar são os **achados**, que são números agregados.

## Decisão

- **Site estático no GitHub Pages** (`site/`): uma página com os achados, gráficos em d3 e textos que
  explicam cada número. Sem servidor, sem banco, link permanente no domínio do autor.
- **Dados gerados pelo pipeline**: `malpipe site` roda consultas fixas sobre as marts e grava
  `site/data/*.json` — só agregados (médias, contagens, top-N). O build local (`tasks.ps1 build` /
  `make build`) já chama o comando; publicar é commit + push.
- **Frases que acompanham os dados**: nomes e números do texto ("quem lidera é…", "a mais lida é…") são
  preenchidos a partir dos JSON, então continuam verdadeiros quando os dados mudam.
- **Sem dependência de CDN**: d3 7.9.0 e as fontes (IBM Plex Sans, Source Serif 4; OFL) ficam em
  `site/assets/`, com as licenças.
- **Verificação antes de publicar**: `scripts/check_site.py` confere que todo conjunto citado na página
  existe e é uma lista de linhas; roda no CI (com os dados de demonstração, sem sobrescrever os reais) e
  no workflow `pages.yml`, que publica a pasta a cada push em `site/`.

## Consequências

- O painel público é um retrato do último `malpipe site` versionado, não uma consulta ao vivo — a data
  de atualização aparece no rodapé (`data/meta.json`).
- Mudou um corte nos dados: os achados de adaptação usam `num_source_works = 1` (coluna nova em
  `mart_adaptation_scores`), o mesmo recorte do README.
- Ativação única no repositório: *Settings → Pages → Source: GitHub Actions*.
