-- Episódios (Kitsu), extração mais recente por anime.
with latest as (
    select mal_id, kitsu_id, payload, extracted_at
    from {{ source('bronze', 'kitsu_episodes') }}
    where http_status = 200 and payload is not null
    {{ latest_by('mal_id') }}
),

eps as (
    select
        mal_id,
        kitsu_id,
        unnest(from_json(payload,
            '[{"kitsu_episode_id": "VARCHAR", "number": "INTEGER", "seasonNumber": "INTEGER",
               "relativeNumber": "INTEGER", "canonicalTitle": "VARCHAR", "airdate": "VARCHAR",
               "length": "INTEGER", "synopsis": "VARCHAR"}]')) as e
    from latest
)

select distinct on (mal_id, e.number)
    mal_id,
    kitsu_id,
    e.number                                     as episode_number,
    e.seasonNumber                               as season_number,
    e.relativeNumber                             as relative_number,
    nullif(trim(e.canonicalTitle), '')           as episode_title,
    try_cast(e.airdate as date)                  as aired_on,
    e.length                                     as length_min,
    nullif(trim(e.synopsis), '')                 as synopsis
from eps
where e.number is not null
order by mal_id, e.number, e.airdate nulls last
