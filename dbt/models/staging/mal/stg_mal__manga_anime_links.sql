-- Ligações mangá → anime declaradas no MAL (adaptação, spin-off etc.).
select distinct manga_id, r.node.id as mal_id, r.relation_type
from (
    select manga_id, unnest(_related_anime) as r
    from {{ ref('stg_mal__manga') }}
)
where r.node.id is not null
