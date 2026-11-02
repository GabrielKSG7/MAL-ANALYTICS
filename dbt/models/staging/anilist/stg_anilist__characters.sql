-- Personagens de cada anime (sem os dubladores, que ficam em stg_anilist__voice_actors).
with edges as (
    select
        mal_id,
        unnest(from_json(_payload->'$.characters',
            '[{"role": "VARCHAR", "node": {"id": "INTEGER", "name": {"full": "VARCHAR", "native": "VARCHAR"},
               "gender": "VARCHAR", "age": "VARCHAR", "favourites": "INTEGER", "image": {"medium": "VARCHAR"},
               "siteUrl": "VARCHAR"}}]')) as e
    from {{ ref('stg_anilist__media') }}
)

select distinct on (mal_id, e.node.id)
    mal_id,
    e.node.id                                       as character_id,
    e.node.name.full                                as character_name,
    e.node.name.native                              as character_name_native,
    e.node.gender                                   as gender,
    e.node.age                                      as age,
    e.node.favourites                               as favourites,
    e.node.image.medium                             as image_url,
    e.node.siteUrl                                  as profile_url,
    case upper(e.role) when 'MAIN' then 'Main' when 'SUPPORTING' then 'Supporting' else 'Background' end
                                                    as character_role
from edges
where e.node.id is not null
order by mal_id, e.node.id, case upper(e.role) when 'MAIN' then 1 when 'SUPPORTING' then 2 else 3 end
