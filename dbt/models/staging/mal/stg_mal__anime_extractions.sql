{{ config(materialized='table') }}
{#
  Todas as extrações bem-sucedidas, já tipadas. É a base para:
  - stg_mal__anime (estado atual, 1 linha por anime)
  - fct_anime_metrics_snapshot (histórico de nota/membros)
  - gêneros, estúdios e relações (listas `_genres`, `_studios`, `_related_anime`, já tipadas)

  Escala: o JSON é lido UMA vez por linha (`from_json` com o tipo dos campos usados). A versão
  anterior fazia um `->>` por coluna (~40 leituras do documento inteiro) e carregava o JSON cru até
  os modelos filhos — com ~30 mil animes isso estourava a memória ao materializar.
#}
with parsed as (
    select
        mal_id,
        extracted_at,
        from_json(payload, '{
            "title": "VARCHAR",
            "alternative_titles": {"en": "VARCHAR", "ja": "VARCHAR"},
            "synopsis": "VARCHAR", "background": "VARCHAR",
            "main_picture": {"medium": "VARCHAR", "large": "VARCHAR"},
            "media_type": "VARCHAR", "status": "VARCHAR", "num_episodes": "VARCHAR",
            "average_episode_duration": "VARCHAR", "source": "VARCHAR", "rating": "VARCHAR", "nsfw": "VARCHAR",
            "start_date": "VARCHAR", "end_date": "VARCHAR",
            "start_season": {"year": "VARCHAR", "season": "VARCHAR"},
            "broadcast": {"day_of_the_week": "VARCHAR", "start_time": "VARCHAR"},
            "mean": "VARCHAR", "rank": "VARCHAR", "popularity": "VARCHAR",
            "num_list_users": "VARCHAR", "num_scoring_users": "VARCHAR",
            "statistics": {"status": {"watching": "VARCHAR", "completed": "VARCHAR", "on_hold": "VARCHAR",
                                      "dropped": "VARCHAR", "plan_to_watch": "VARCHAR"}},
            "created_at": "VARCHAR", "updated_at": "VARCHAR",
            "genres": [{"id": "INTEGER", "name": "VARCHAR"}],
            "studios": [{"id": "INTEGER", "name": "VARCHAR"}],
            "related_anime": [{"node": {"id": "INTEGER", "title": "VARCHAR"}, "relation_type": "VARCHAR"}]
        }') as j
    from {{ source('bronze', 'mal_anime') }}
    where http_status = 200 and payload is not null
)

select
    mal_id,
    extracted_at,
    cast(extracted_at as date)                                   as snapshot_date,

    j.title                                                      as title,
    nullif(j.alternative_titles.en, '')                          as title_english,
    nullif(j.alternative_titles.ja, '')                          as title_japanese,
    j.synopsis                                                   as synopsis,
    j.background                                                 as background,
    j.main_picture.large                                         as picture_url_large,
    coalesce(j.main_picture.medium, j.main_picture.large)        as picture_url,

    j.media_type                                                 as media_type,
    j.status                                                     as airing_status,
    try_cast(j.num_episodes as integer)                          as num_episodes,
    try_cast(j.average_episode_duration as integer)              as episode_duration_sec,
    j.source                                                     as source_material,
    j.rating                                                     as age_rating,
    j.nsfw                                                       as nsfw_level,

    j.start_date                                                 as start_date_raw,
    {{ parse_mal_date("j.start_date") }}                         as start_date,
    {{ mal_date_precision("j.start_date") }}                     as start_date_precision,
    {{ parse_mal_date("j.end_date") }}                           as end_date,
    try_cast(j.start_season.year as integer)                     as season_year,
    lower(j.start_season.season)                                 as season_name,
    j.broadcast.day_of_the_week                                  as broadcast_day,
    j.broadcast.start_time                                       as broadcast_time_jst,

    try_cast(j.mean as double)                                   as mean_score,
    try_cast(j.rank as integer)                                  as score_rank,
    try_cast(j.popularity as integer)                            as popularity_rank,
    try_cast(j.num_list_users as bigint)                         as num_list_users,
    try_cast(j.num_scoring_users as bigint)                      as num_scoring_users,

    try_cast(j.statistics.status.watching as bigint)             as status_watching,
    try_cast(j.statistics.status.completed as bigint)            as status_completed,
    try_cast(j.statistics.status.on_hold as bigint)              as status_on_hold,
    try_cast(j.statistics.status.dropped as bigint)              as status_dropped,
    try_cast(j.statistics.status.plan_to_watch as bigint)        as status_plan_to_watch,

    try_cast(j.created_at as timestamptz)                        as mal_created_at,
    try_cast(j.updated_at as timestamptz)                        as mal_updated_at,

    j.genres                                                     as _genres,
    j.studios                                                    as _studios,
    j.related_anime                                              as _related_anime
from parsed
