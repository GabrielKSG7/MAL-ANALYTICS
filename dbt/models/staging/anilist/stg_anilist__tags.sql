-- Tags temáticas da AniList com relevância (rank 0–100) e marcação de spoiler.
with t as (
    select
        mal_id,
        unnest(from_json(_payload->'$.tags',
            '[{"name": "VARCHAR", "rank": "INTEGER", "category": "VARCHAR", "isMediaSpoiler": "BOOLEAN"}]')) as tag
    from {{ ref('stg_anilist__media') }}
)

select distinct
    mal_id,
    tag.name            as tag,
    tag.category        as category,
    tag.rank            as relevance,
    tag.isMediaSpoiler  as is_spoiler
from t
where tag.name is not null
