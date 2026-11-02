-- Personagens (ID da AniList), com favoritos e em quantos animes aparecem.
select
    character_id,
    any_value(character_name)           as character_name,
    any_value(character_name_native)    as character_name_native,
    any_value(gender)                   as gender,
    any_value(age)                      as age,
    max(favourites)                     as favourites,
    count(distinct mal_id)              as num_anime_appearances,
    bool_or(character_role = 'Main')    as ever_main,
    any_value(image_url)                as image_url,
    any_value(profile_url)              as profile_url
from {{ ref('stg_anilist__characters') }}
group by character_id
