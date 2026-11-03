{{ config(materialized='table') }}
-- Mangás, light novels, manhwas etc. (MAL API), extração mais recente.
--
-- Escala: são ~86 mil payloads. Duas escolhas mantêm a memória baixa (o build original estourava 4 GB):
--   1. o JSON é lido UMA vez por linha (`from_json` com o tipo dos campos usados), em vez de um `->>`
--      por coluna — cada `->>` reabre o documento inteiro;
--   2. é tabela, e as listas (gêneros, autores, revista, animes) já saem tipadas para as pontes, que
--      não precisam mais tocar no JSON.
with parsed as (
    select
        mal_id,
        extracted_at,
        from_json(payload, '{
            "title": "VARCHAR",
            "alternative_titles": {"en": "VARCHAR", "ja": "VARCHAR"},
            "main_picture": {"medium": "VARCHAR", "large": "VARCHAR"},
            "synopsis": "VARCHAR", "media_type": "VARCHAR", "status": "VARCHAR", "nsfw": "VARCHAR",
            "start_date": "VARCHAR", "end_date": "VARCHAR",
            "num_volumes": "VARCHAR", "num_chapters": "VARCHAR", "mean": "VARCHAR", "rank": "VARCHAR",
            "popularity": "VARCHAR", "num_list_users": "VARCHAR", "num_scoring_users": "VARCHAR",
            "genres": [{"id": "INTEGER", "name": "VARCHAR"}],
            "authors": [{"node": {"id": "INTEGER", "first_name": "VARCHAR", "last_name": "VARCHAR"}, "role": "VARCHAR"}],
            "serialization": [{"node": {"id": "INTEGER", "name": "VARCHAR"}}],
            "related_anime": [{"node": {"id": "INTEGER"}, "relation_type": "VARCHAR"}]
        }') as j
    from {{ latest_success(source('bronze', 'mal_manga')) }} as src
)

select
    mal_id                                                       as manga_id,
    j.title                                                      as title,
    nullif(j.alternative_titles.en, '')                          as title_english,
    nullif(j.alternative_titles.ja, '')                          as title_japanese,
    coalesce(j.main_picture.medium, j.main_picture.large)        as picture_url,
    j.synopsis                                                   as synopsis,
    j.media_type                                                 as media_type,
    j.status                                                     as publishing_status,
    {{ parse_mal_date("j.start_date") }}                         as start_date,
    {{ parse_mal_date("j.end_date") }}                           as end_date,
    try_cast(j.num_volumes as integer)                           as num_volumes,
    try_cast(j.num_chapters as integer)                          as num_chapters,
    try_cast(j.mean as double)                                   as mean_score,
    try_cast(j.rank as integer)                                  as score_rank,
    try_cast(j.popularity as integer)                            as popularity_rank,
    try_cast(j.num_list_users as bigint)                         as num_list_users,
    try_cast(j.num_scoring_users as bigint)                      as num_scoring_users,
    j.nsfw                                                       as nsfw_level,
    extracted_at,
    j.genres                                                     as _genres,
    j.authors                                                    as _authors,
    j.serialization                                              as _serialization,
    j.related_anime                                              as _related_anime
from parsed
