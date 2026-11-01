{#
  anime-offline-database: snapshot mais recente, uma linha por anime do MAL.
  O ID do MAL é extraído da lista `sources` (URLs). Entradas sem MAL ficam de fora
  porque o projeto é centrado no MAL — mas os IDs de outros sites são preservados
  para servir de ponte (AniList, Kitsu, AniDB).
#}
with latest_snapshot as (
    select payload, dataset_date
    from {{ source('bronze', 'manami_anime') }}
    qualify dataset_date = max(dataset_date) over ()
),

parsed as (
    select
        from_json(payload->'$.sources', '["VARCHAR"]') as sources,
        payload->>'$.title'                             as title,
        payload->>'$.type'                              as media_type,
        try_cast(payload->>'$.episodes' as integer)     as num_episodes,
        payload->>'$.status'                            as airing_status,
        lower(payload->>'$.animeSeason.season')         as season_name,
        try_cast(payload->>'$.animeSeason.year' as integer) as season_year,
        try_cast(payload->>'$.score.median' as double)  as cross_site_score_median,
        try_cast(payload->>'$.score.arithmeticMean' as double) as cross_site_score_mean,
        from_json(payload->'$.tags', '["VARCHAR"]')     as tags,
        from_json(payload->'$.studios', '["VARCHAR"]')  as studios,
        from_json(payload->'$.synonyms', '["VARCHAR"]') as synonyms,
        dataset_date
    from latest_snapshot
),

with_ids as (
    select
        *,
        try_cast(regexp_extract(
            list_filter(sources, lambda s: s like '%myanimelist.net/anime/%')[1],
            'myanimelist\.net/anime/(\d+)', 1) as integer)              as mal_id,
        try_cast(regexp_extract(
            list_filter(sources, lambda s: s like '%anilist.co/anime/%')[1],
            'anilist\.co/anime/(\d+)', 1) as integer)                   as anilist_id,
        try_cast(regexp_extract(
            list_filter(sources, lambda s: s like '%kitsu.%/anime/%')[1],
            '/anime/(\d+)', 1) as integer)                              as kitsu_id,
        try_cast(regexp_extract(
            list_filter(sources, lambda s: s like '%anidb.net/anime/%')[1],
            'anidb\.net/anime/(\d+)', 1) as integer)                    as anidb_id,
        len(sources)                                                     as num_sources
    from parsed
)

select
    mal_id,
    anilist_id,
    kitsu_id,
    anidb_id,
    num_sources,
    title,
    media_type,
    num_episodes,
    airing_status,
    season_name,
    season_year,
    cross_site_score_median,
    cross_site_score_mean,
    tags,
    studios,
    synonyms,
    dataset_date
from with_ids
where mal_id is not null
-- Raramente duas entradas apontam para o mesmo ID do MAL; fica a com mais fontes.
qualify row_number() over (partition by mal_id order by num_sources desc, title) = 1
