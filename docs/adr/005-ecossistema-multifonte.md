# ADR 005 — Ecossistema (pessoas, episódios, mangá) a partir de APIs oficiais

**Status:** aceito · **Data:** 2026-11

## Contexto

O núcleo do projeto cobre ~30 mil animes do MAL. Para responder perguntas sobre **pessoas**
(dubladores, diretores, compositores), **episódios** e **mangás/adaptações**, o plano original era o
Jikan (`/characters`, `/staff`, `/episodes`). Na rede do autor o Jikan é inacessível (timeouts) e,
mesmo acessível, seriam ~90 mil chamadas a 1 req/s raspando o próprio MAL.

## Decisão

Usar APIs oficiais, cada uma no que faz melhor, todas ligadas pelo `mal_id`:

| Entidade | Fonte | Ligação com o MAL |
|---|---|---|
| Personagens, dubladores (por idioma), staff com papel, fichas de pessoas | AniList GraphQL | consulta por `idMal` |
| Episódios (título, data, duração) | Kitsu JSON:API | `kitsu_id` do anime-offline-database |
| Mangás, autores, revistas | MAL API v2 (`/manga`) | `manga_id` do MAL |
| Adaptação mangá → anime | AniList (relações em lote, `SOURCE`) + MAL `related_anime` | `idMal` dos dois lados |

- **Uma requisição por anime na AniList**: elenco + staff + tags + estúdios na mesma consulta GraphQL,
  com páginas extras só quando necessário (diretivas `@include` evitam rebuscar o que já veio).
  Corte em `ANILIST_MAX_PAGES` com marcação `truncated` — previsível em tempo, honesto no dado.
- **Paralelismo entre fontes, não dentro delas**: `malpipe ecosystem` usa uma thread por host, cada
  uma com seu rate limiter; o DuckDB é protegido por um `RLock` no `Warehouse`. Tempo total = a fonte
  mais lenta (~20 h) em vez da soma (~35 h).
- **Bronze igual ao resto**: JSON cru, append-only, checkpoint derivado do próprio bronze, 404 definitivo.
- **IDs de pessoa/personagem = AniList.** `dim_person` e `dim_character` passam a ser AniList; o elenco
  do Jikan continua no bronze, mas não alimenta o core (evita conciliar dois espaços de IDs).
- **Papéis normalizados no dbt** (`staff_role_group`): "Director", "Chief Director", "Episode Director (ep 3)"
  etc. viram 13 grupos estáveis, testados com `accepted_values`.

- **JSON lido uma vez** (adendo pós-carga real): a primeira versão extraía cada coluna com `->>` e
  deixava o `_payload` para os modelos filhos reabrirem. Com 86 mil mangás o build estourou 4 GB
  (`Out of Memory`). Agora `stg_mal__manga` e `stg_anilist__media` são tabelas que fazem um único
  `from_json` com o tipo de todos os campos usados e entregam listas tipadas aos filhos; a deduplicação
  (`latest_success`) agrega só `(id, max(extracted_at))` e filtra por junção, sem janela sobre os
  payloads. Medido com dados sintéticos do mesmo tamanho: mangá de >1,2 GB para <300 MB; AniList com
  1 GB de JSON roda em 1 GB. O mesmo padrão foi aplicado depois a `stg_mal__anime_extractions`
  (~40 `->>` por linha), que estourava a memória no `publish` com 30 mil animes. Teste em escala real
  (30 mil animes, 86 mil mangás, 30 mil AniList): build completo em 36 s e publish em 8 s com 1,5 GB.

- **Ligação mangá × anime pela AniList** (adendo pós-carga real): o `related_anime` dos 85.913 mangás
  não gerou nenhuma ligação de adaptação (mart de adaptações vazia, *Berserk* e *One Piece* listados como "sem
  anime"). A AniList informa a obra de origem de cada anime (`relationType: SOURCE`, com o `idMal` do
  mangá), e a consulta aceita 50 IDs por vez: ~600 requisições para 30 mil animes.
  `int_manga__anime_links` une as duas fontes e registra quem confirmou cada ligação (`link_sources`).

## Consequências

- Novos modelos: `bridge_anime_staff`, `fct_episode`, `dim_manga`, `bridge_manga_anime`,
  `bridge_manga_author` e as marts de dubladores, diretores, episódios e adaptações.
- A AniList é a fonte mais sensível nos termos (proíbe coleta em massa; tolera projetos educacionais).
  Mitigação: ritmo abaixo do limite, dados só locais, `--limit` documentado.
- Séries muito longas ficam com elenco/créditos parciais (os mais relevantes primeiro). Aceitável para
  rankings; documentado no `truncated`.
- O Kitsu depende do `malpipe manami` (mapa de IDs) — documentado no runbook e no `status`.
