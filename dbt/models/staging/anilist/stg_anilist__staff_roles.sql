-- Créditos de staff: quem fez o quê em cada anime. `role_group` agrupa variações
-- ("Episode Director (eps 1, 5)", "Chief Director"...) em categorias analíticas.
with edges as (
    select
        mal_id,
        unnest(_staff) as e
    from {{ ref('stg_anilist__media') }}
)

select distinct
    mal_id,
    e.node.id                                              as person_id,
    e.role                                                 as role,
    trim(regexp_replace(e.role, '\s*\(.*\)$', ''))         as role_base,
    {{ staff_role_group('e.role') }}                       as role_group
from edges
where e.node.id is not null and e.role is not null
