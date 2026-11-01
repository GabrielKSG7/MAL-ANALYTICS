with latest as (
    select mal_id, _payload as payload
    from {{ ref('stg_mal__anime_extractions') }}
    {{ latest_by('mal_id') }}
),

exploded as (
    select
        mal_id,
        unnest(from_json(payload->'$.genres', '[{"id": "INTEGER", "name": "VARCHAR"}]')) as genre
    from latest
)

select distinct
    mal_id,
    genre.id   as genre_id,
    genre.name as genre_name
from exploded
where genre.id is not null
