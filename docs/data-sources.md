# Fontes de dados, limites e termos de uso

> **Resumo:** projeto pessoal, não comercial. Nenhum dado extraído é versionado ou redistribuído
> neste repositório — só o código. Respeite os limites de cada fonte.

## 1. MAL API v2 (oficial)

- **Docs:** https://myanimelist.net/apiconfig/references/api/v2
- **Credencial:** registre um app em https://myanimelist.net/apiconfig (App Type `other`, Purpose
  `hobbyist`, `non-commercial`). Os endpoints públicos aceitam só o header `X-MAL-CLIENT-ID`; não é
  preciso OAuth para ler animes nem listas **públicas** de usuários.
- **Rate limit:** não documentado. A prática da comunidade é ≈ 1 req/s; o padrão aqui é `MAL_RPS=1.0`.
- **Termos:** API License and Developer Agreement (aceito no cadastro) e Terms of Use do site, que
  concedem licença para uso pessoal e não comercial.
- **Endpoints usados:**

| Endpoint | Para quê | Paginação |
|---|---|---|
| `GET /anime/ranking?ranking_type=all` | descobrir IDs ranqueados | 500 por página, segue `paging.next` |
| `GET /anime/season/{ano}/{temporada}` | descobrir IDs por temporada (inclui anunciados) | 500 por página |
| `GET /anime/{id}?fields=...` | detalhe completo (27 campos) | — |
| `GET /users/{nome}/animelist` | sua lista | 1000 por página |

- **Pegadinhas tratadas no código:**
  - `statistics.status.*` chega como **string** (`"121547"`) — convertido no staging.
  - Datas parciais (`"2015"`, `"2015-04"`) — `parse_mal_date` + coluna de precisão.
  - Sem `nsfw=true`, alguns títulos somem das listagens.
  - IDs inexistentes retornam 404 — gravados no bronze para não serem tentados de novo.

**Tempo estimado de carga completa:** ~30 mil IDs ÷ 1 req/s ≈ 8–9 h (uma vez). Depois, só o incremental.

## 2. Jikan v4 (não oficial)

- **Docs:** https://docs.api.jikan.moe — raspa o site do MAL e faz cache de 24 h.
- **Limites publicados:** 3 req/s e 60 req/min. Padrão aqui: `JIKAN_RPS=1.0`.
- **Para cargas grandes:** rode sua própria instância (`docker run -d -p 8080:8080 jikanme/jikan-rest`)
  e defina `JIKAN_BASE_URL=http://localhost:8080/v4`. Lembre que ela continua acessando o MAL por trás —
  mantenha o ritmo baixo.
- **Endpoints usados:** `/anime/{id}/statistics` (distribuição de notas), `/anime/{id}/recommendations`,
  `/anime/{id}/characters`.

## 3. anime-offline-database (manami-project)

- **Repo:** https://github.com/manami-project/anime-offline-database — atualizado semanalmente.
- **Arquivo:** `anime-offline-database-minified.json.zst` (zstd, ~6 MB) nos releases.
- **Conteúdo (snapshot de jul/2026):** 41.537 animes, dos quais 30.561 têm ID do MAL; IDs cruzados de
  AniList, Kitsu, AniDB, Anime-Planet etc.; tags temáticas; estúdios; nota agregada entre sites.
- **Licença:** ODbL v1.0 + DbCL v1.0 — atribuição obrigatória; share-alike se você redistribuir uma base derivada.

## 4. Kaggle — Anime Recommendation Database 2020 (hernan4444)

- **Página:** https://www.kaggle.com/datasets/hernan4444/anime-recommendation-database-2020
- **Download:**
  ```bash
  pip install kaggle   # e coloque seu kaggle.json em ~/.kaggle/
  kaggle datasets download -d hernan4444/anime-recommendation-database-2020 -f animelist.csv -p data/raw --unzip
  malpipe kaggle data/raw/animelist.csv                    # completo (~109M linhas)
  malpipe kaggle data/raw/animelist.csv --sample-users 20000   # amostra para desenvolver
  ```
- **Conteúdo:** `user_id, anime_id, score, watching_status, watched_episodes` — 325.772 usuários, 17.562 animes.
- **Limitações:** congelado em 2020 (títulos novos não têm interações) e `score = 0` significa "sem nota".
- **Privacidade:** o `user_id` é transformado em hash (`user_key`) já no staging; as marts nunca expõem o ID original.

## Boas práticas adotadas

- Um único processo, sequencial, com intervalo mínimo entre requisições (sem paralelismo nem rotação de IP).
- Respeito ao `Retry-After` e backoff exponencial com jitter em 429/5xx.
- User-Agent identificando o projeto.
- Checkpoint: nunca re-extrai o que já está fresco no bronze.
