-- Distribuição de notas 1–10 por anime (Jikan /statistics), extração mais recente.
with latest as (
    select mal_id, payload, extracted_at
    from {{ source('bronze', 'jikan_statistics') }}
    where http_status = 200 and payload is not null
    {{ latest_by('mal_id') }}
),

exploded as (
    select
        mal_id,
        extracted_at,
        unnest(
            from_json(payload->'$.scores', '[{"score": "INTEGER", "votes": "BIGINT", "percentage": "DOUBLE"}]')
        ) as s
    from latest
)

select
    mal_id,
    s.score      as score,
    s.votes      as votes,
    s.percentage as percentage,
    extracted_at
from exploded
where s.score between 1 and 10
