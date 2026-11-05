with latest as (
    select mal_id, _related_anime
    from {{ ref('stg_mal__anime_extractions') }}
    {{ latest_by('mal_id') }}
),

exploded as (
    select
        mal_id,
        unnest(
            _related_anime
        ) as rel
    from latest
)

select distinct
    mal_id,
    rel.node.id      as related_mal_id,
    rel.node.title   as related_title,
    rel.relation_type
from exploded
where rel.node.id is not null
