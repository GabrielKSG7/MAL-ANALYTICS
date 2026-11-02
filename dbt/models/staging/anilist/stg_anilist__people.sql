-- Pessoas (dubladores + staff) deduplicadas. A ficha vem embutida nos créditos, então não
-- custa nenhuma requisição extra.
with va as (
    select unnest(e.voiceActorRoles).voiceActor as p
    from (
        select unnest(from_json(_payload->'$.characters',
            '[{"voiceActorRoles": [{"voiceActor": {{ anilist_person_type() }}}]}]')) as e
        from {{ ref('stg_anilist__media') }}
    )
),

staff as (
    select unnest(from_json(_payload->'$.staff', '[{"node": {{ anilist_person_type() }}}]')).node as p
    from {{ ref('stg_anilist__media') }}
),

people as (
    select p from va
    union all
    select p from staff
)

select
    p.id                                          as person_id,
    any_value(p.name.full)                        as person_name,
    any_value(p.name.native)                      as person_name_native,
    any_value(p.languageV2)                       as language,
    any_value(p.gender)                           as gender,
    max(p.favourites)                             as favourites,
    any_value(p.primaryOccupations)               as occupations,
    any_value(p.homeTown)                         as home_town,
    any_value({{ fuzzy_date('p.dateOfBirth') }})  as birth_date,
    any_value({{ fuzzy_date('p.dateOfDeath') }})  as death_date,
    min(list_min(p.yearsActive))                  as active_since,
    any_value(p.image.medium)                     as image_url,
    any_value(p.siteUrl)                          as profile_url
from people
where p.id is not null
group by p.id
