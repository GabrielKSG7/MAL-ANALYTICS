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

## 5. MAL API v2 — mangá

- Mesma credencial e ritmo da API de anime (`MAL_RPS`). O comando `malpipe manga` descobre os IDs pelos
  rankings `all` e `bypopularity` e depois busca o detalhe de cada um.
- **Endpoints:** `GET /manga/ranking` (500 por página) e `GET /manga/{id}?fields=...` — inclui autores
  (`authors{first_name,last_name}` + papel), revista (`serialization`), volumes/capítulos e
  `related_anime`, que é de onde sai a ligação mangá → anime.
- **Volume:** ~70 mil IDs ranqueados ≈ 20 h a 1 req/s. É a carga mais longa do ecossistema.

## 6. AniList GraphQL

- **Docs:** https://docs.anilist.co — sem credencial para leitura.
- **Para quê:** elenco (personagem × dublador, por idioma), staff com o papel de cada pessoa
  (direção, roteiro, música…), fichas das pessoas e personagens, tags e estúdios. A consulta é feita por
  `idMal`, então tudo chega já ligado ao anime do MAL.
- **Rate limit:** 90 req/min no papel, mas a API está em **modo degradado com 30 req/min** desde 2025.
  Padrão aqui: `ANILIST_RPS=0.45` (≈ 27/min). Personagens e staff são paginados (25 por página); o
  conector junta até `ANILIST_MAX_PAGES=4` páginas por anime e marca `truncated=true` quando sobra —
  séries enormes (One Piece, Detective Conan) ficam com os personagens/créditos mais relevantes.
- **Pegadinhas tratadas:** erro de GraphQL chega com HTTP 200 → gravado como 400 e, após 3 seguidos,
  a carga para (consulta inválida não deve gerar 30 mil linhas de erro); anime sem cadastro na
  AniList → 404, não é tentado de novo.
- **Termos:** os [termos da API](https://docs.anilist.co/guide/terms-of-use) proíbem *"hoarding or mass
  collection of data"* e o uso da API como armazenamento, e dizem ser tolerantes com projetos puramente
  educacionais. Este projeto é pessoal e educacional, respeita o limite e guarda os dados só localmente —
  ainda assim é a fonte mais sensível: use `--limit` (ex.: só os animes da sua lista e os mais populares)
  se quiser ficar do lado conservador, e nunca republique a base derivada.
- **Volume:** ~30 mil animes × ~1,2 requisição ≈ 19 h no ritmo degradado.
- **Relações em lote** (`malpipe anilist-relations`, também roda dentro do `ecosystem`): `Page(perPage: 50)
  { media(idMal_in: [...]) { relations { edges { relationType(version: 2) node { idMal type } } } } }` —
  50 animes por chamada, ~600 chamadas (~20 min). É daqui que sai a ligação anime → mangá de origem
  (`relationType: SOURCE`): na carga real, o `related_anime` dos 85.913 mangás veio sem nenhuma ligação
  aproveitável da MAL API.

## 7. Kitsu (JSON:API)

- **Docs:** https://kitsu.docs.apiary.io — base `https://kitsu.app/api/edge`, sem credencial.
- **Para quê:** lista de episódios (número, temporada, título, data de exibição, duração, sinopse).
- **Mapeamento:** o ID do Kitsu vem do anime-offline-database (manami), por isso rode `malpipe manami`
  antes. Só séries (TV, ONA, OVA, especiais) — filmes e clipes não têm guia de episódios útil.
- **Paginação:** `page[limit]=20`, seguindo `links.next` (até 200 páginas).
- **Rate limit:** não publicado; padrão `KITSU_RPS=2`. **Volume:** ~15 mil séries ≈ 4 h.

## Carga do ecossistema de uma vez

`malpipe ecosystem` roda as três fontes acima **em paralelo**, uma thread por fonte. Cada fonte continua
sequencial e com o seu próprio limitador — o paralelismo é entre hosts diferentes, nunca contra o mesmo
servidor. A gravação no DuckDB passa por um lock (um escritor por vez). O tempo total é o da fonte mais
lenta (~20 h, o mangá), e o checkpoint permite interromper e retomar. `malpipe check-sources` testa todas
as fontes em segundos antes de começar.

## Boas práticas adotadas

- Requisições sequenciais por host, com intervalo mínimo entre elas (sem rotação de IP; paralelismo só entre fontes diferentes).
- Respeito ao `Retry-After` e backoff exponencial com jitter em 429/5xx.
- User-Agent identificando o projeto.
- Checkpoint: nunca re-extrai o que já está fresco no bronze.
- Circuit breaker: 3 falhas de rede seguidas param a fonte com mensagem clara, em vez de horas de timeout.
