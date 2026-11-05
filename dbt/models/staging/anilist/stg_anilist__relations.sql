-- Relações de cada anime na AniList (versão 2 dos tipos: inclui SOURCE = obra de origem).
with latest as (
    select mal_id, payload
    from {{ latest_success(source('bronze', 'anilist_relations')) }} as src
),

edges as (
    select
        mal_id,
        unnest(from_json(payload,
            '[{"relationType": "VARCHAR", "node": {"id": "INTEGER", "idMal": "INTEGER", "type": "VARCHAR", "format": "VARCHAR"}}]'
        )) as e
    from latest
)

select distinct
    mal_id,
    e.relationType      as relation_type,
    e.node.type         as related_type,
    e.node.format       as related_format,
    e.node.id           as related_anilist_id,
    e.node.idMal        as related_mal_id
from edges
where e.relationType is not null
