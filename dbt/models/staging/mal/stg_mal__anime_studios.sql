with latest as (
    select mal_id, _studios
    from {{ ref('stg_mal__anime_extractions') }}
    {{ latest_by('mal_id') }}
),

exploded as (
    select
        mal_id,
        unnest(
            _studios
        ) as studio,
        generate_subscripts(
            _studios, 1
        ) as studio_position
    from latest
)

select distinct
    mal_id,
    studio.id          as studio_id,
    studio.name        as studio_name,
    studio_position = 1 as is_main_studio
from exploded
where studio.id is not null
