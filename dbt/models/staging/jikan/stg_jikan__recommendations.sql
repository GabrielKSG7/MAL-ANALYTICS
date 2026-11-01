-- Recomendações "quem gostou de X recomenda Y", votadas pela comunidade.
-- Servem de ground truth externo para avaliar o recomendador item-item.
with latest as (
    select mal_id, payload
    from {{ source('bronze', 'jikan_recommendations') }}
    where http_status = 200 and payload is not null
    {{ latest_by('mal_id') }}
),

exploded as (
    select
        mal_id,
        unnest(from_json(payload, '[{"entry": {"mal_id": "INTEGER", "title": "VARCHAR"}, "votes": "INTEGER"}]')) as r
    from latest
)

select
    mal_id,
    r.entry.mal_id as recommended_mal_id,
    r.entry.title  as recommended_title,
    r.votes        as votes
from exploded
where r.entry.mal_id is not null and r.entry.mal_id <> mal_id
qualify row_number() over (partition by mal_id, r.entry.mal_id order by r.votes desc) = 1
