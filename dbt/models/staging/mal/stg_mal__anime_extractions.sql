{#
  Todas as extrações bem-sucedidas, já tipadas. É a base para:
  - stg_mal__anime (estado atual, 1 linha por anime)
  - fct_anime_metrics_snapshot (histórico de nota/membros)
#}
with source as (
    select * from {{ source('bronze', 'mal_anime') }}
    where http_status = 200 and payload is not null
),

parsed as (
    select
        mal_id,
        extracted_at,
        cast(extracted_at as date)                                   as snapshot_date,

        payload->>'$.title'                                          as title,
        nullif(payload->>'$.alternative_titles.en', '')              as title_english,
        nullif(payload->>'$.alternative_titles.ja', '')              as title_japanese,
        payload->>'$.synopsis'                                       as synopsis,
        payload->>'$.background'                                     as background,
        payload->>'$.main_picture.large'                             as picture_url_large,
        coalesce(payload->>'$.main_picture.medium',
                 payload->>'$.main_picture.large')                   as picture_url,

        payload->>'$.media_type'                                     as media_type,
        payload->>'$.status'                                         as airing_status,
        try_cast(payload->>'$.num_episodes' as integer)              as num_episodes,
        try_cast(payload->>'$.average_episode_duration' as integer)  as episode_duration_sec,
        payload->>'$.source'                                         as source_material,
        payload->>'$.rating'                                         as age_rating,
        payload->>'$.nsfw'                                           as nsfw_level,

        payload->>'$.start_date'                                     as start_date_raw,
        {{ parse_mal_date("payload->>'$.start_date'") }}             as start_date,
        {{ mal_date_precision("payload->>'$.start_date'") }}         as start_date_precision,
        {{ parse_mal_date("payload->>'$.end_date'") }}               as end_date,
        try_cast(payload->>'$.start_season.year' as integer)         as season_year,
        lower(payload->>'$.start_season.season')                     as season_name,
        payload->>'$.broadcast.day_of_the_week'                      as broadcast_day,
        payload->>'$.broadcast.start_time'                           as broadcast_time_jst,

        try_cast(payload->>'$.mean' as double)                       as mean_score,
        try_cast(payload->>'$.rank' as integer)                      as score_rank,
        try_cast(payload->>'$.popularity' as integer)                as popularity_rank,
        try_cast(payload->>'$.num_list_users' as bigint)             as num_list_users,
        try_cast(payload->>'$.num_scoring_users' as bigint)          as num_scoring_users,

        {{ status_count('watching') }}                               as status_watching,
        {{ status_count('completed') }}                              as status_completed,
        {{ status_count('on_hold') }}                                as status_on_hold,
        {{ status_count('dropped') }}                                as status_dropped,
        {{ status_count('plan_to_watch') }}                          as status_plan_to_watch,

        try_cast(payload->>'$.created_at' as timestamptz)            as mal_created_at,
        try_cast(payload->>'$.updated_at' as timestamptz)            as mal_updated_at,

        payload                                                      as _payload
    from source
)

select * from parsed
