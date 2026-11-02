-- Estúdios e produtoras de cada anime segundo a AniList (inclui produtoras, não só animação).
with edges as (
    select
        mal_id,
        unnest(from_json(_payload->'$.studios.edges',
            '[{"isMain": "BOOLEAN", "node": {"id": "INTEGER", "name": "VARCHAR", "isAnimationStudio": "BOOLEAN",
               "favourites": "INTEGER", "siteUrl": "VARCHAR"}}]')) as e
    from {{ ref('stg_anilist__media') }}
)

select distinct
    mal_id,
    e.node.id                  as anilist_studio_id,
    e.node.name                as studio_name,
    e.node.isAnimationStudio   as is_animation_studio,
    coalesce(e.isMain, false)  as is_main,
    e.node.favourites          as favourites
from edges
where e.node.id is not null
