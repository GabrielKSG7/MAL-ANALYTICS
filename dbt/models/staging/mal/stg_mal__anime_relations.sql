with latest as (
    select mal_id, _payload as payload
    from {{ ref('stg_mal__anime_extractions') }}
    {{ latest_by('mal_id') }}
),

exploded as (
    select
        mal_id,
        unnest(
            from_json(
                payload->'$.related_anime',
                '[{"node": {"id": "INTEGER", "title": "VARCHAR"}, "relation_type": "VARCHAR"}]'
            )
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
