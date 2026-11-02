-- Autores (mangaká, roteirista, ilustrador) de cada mangá.
select distinct
    manga_id,
    a.node.id                                                         as author_id,
    trim(concat_ws(' ', nullif(a.node.first_name, ''), nullif(a.node.last_name, ''))) as author_name,
    a.role                                                            as author_role
from (
    select manga_id, unnest(from_json(_payload->'$.authors',
        '[{"node": {"id": "INTEGER", "first_name": "VARCHAR", "last_name": "VARCHAR"}, "role": "VARCHAR"}]')) as a
    from {{ ref('stg_mal__manga') }}
)
where a.node.id is not null
