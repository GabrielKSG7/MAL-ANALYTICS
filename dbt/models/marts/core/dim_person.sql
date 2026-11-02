-- Pessoas do ecossistema (dubladores e staff), com a ficha da AniList e o tamanho da carreira
-- capturada nos dados. person_id = ID da AniList.
with voiced as (
    select person_id,
           count(distinct mal_id)                                              as num_anime_voiced,
           count(distinct character_id)                                        as num_characters,
           count(distinct character_id) filter (where c.character_role = 'Main') as num_main_roles
    from {{ ref('stg_anilist__voice_actors') }} v
    join {{ ref('stg_anilist__characters') }} c using (mal_id, character_id)
    group by person_id
),

worked as (
    select person_id,
           count(distinct mal_id)                                        as num_anime_staff,
           count(distinct mal_id) filter (where role_group = 'Direção')  as num_anime_directed,
           mode(role_group) filter (where role_group <> 'Outros')        as main_role_group
    from {{ ref('stg_anilist__staff_roles') }}
    group by person_id
)

select
    p.person_id,
    p.person_name,
    p.person_name_native,
    p.language,
    p.gender,
    p.birth_date,
    p.death_date,
    p.home_town,
    p.active_since,
    p.occupations,
    p.favourites,
    coalesce(v.num_anime_voiced, 0)     as num_anime_voiced,
    coalesce(v.num_characters, 0)       as num_characters,
    coalesce(v.num_main_roles, 0)       as num_main_roles,
    coalesce(w.num_anime_staff, 0)      as num_anime_staff,
    coalesce(w.num_anime_directed, 0)   as num_anime_directed,
    w.main_role_group,
    p.image_url,
    p.profile_url
from {{ ref('stg_anilist__people') }} p
left join voiced v using (person_id)
left join worked w using (person_id)
