select distinct
    mal_id,
    lower(trim(tag)) as tag
from (
    select mal_id, unnest(tags) as tag
    from {{ ref('stg_manami__anime') }}
)
where tag is not null and trim(tag) <> ''
