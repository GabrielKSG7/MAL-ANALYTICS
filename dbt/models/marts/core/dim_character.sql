select
    character_id,
    any_value(character_name)        as character_name,
    max(character_favorites)         as favorites,
    count(distinct mal_id)           as num_anime_appearances,
    bool_or(character_role = 'Main') as ever_main
from {{ ref('stg_jikan__characters') }}
group by character_id
