select distinct manga_id, g.id as genre_id, g.name as genre_name
from (
    select manga_id, unnest(from_json(_payload->'$.genres', '[{"id": "INTEGER", "name": "VARCHAR"}]')) as g
    from {{ ref('stg_mal__manga') }}
)
where g.id is not null
