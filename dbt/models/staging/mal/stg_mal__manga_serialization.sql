-- Revista/selo onde cada mangá foi publicado.
select distinct manga_id, s.node.id as magazine_id, s.node.name as magazine_name
from (
    select manga_id, unnest(_serialization) as s
    from {{ ref('stg_mal__manga') }}
)
where s.node.id is not null
