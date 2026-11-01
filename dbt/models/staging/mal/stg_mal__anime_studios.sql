with latest as (
    select mal_id, _payload as payload
    from {{ ref('stg_mal__anime_extractions') }}
    {{ latest_by('mal_id') }}
),

exploded as (
    select
        mal_id,
        unnest(
            from_json(payload->'$.studios', '[{"id": "INTEGER", "name": "VARCHAR"}]')
        ) as studio,
        generate_subscripts(
            from_json(payload->'$.studios', '[{"id": "INTEGER", "name": "VARCHAR"}]'), 1
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
