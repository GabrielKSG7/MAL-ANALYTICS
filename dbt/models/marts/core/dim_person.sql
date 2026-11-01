-- Dubladores (seiyuus) e o tamanho da carreira capturada nos dados.
select
    person_id,
    any_value(person_name)                                                   as person_name,
    count(distinct mal_id)                                                   as num_anime,
    count(distinct character_id)                                             as num_characters,
    count(distinct character_id) filter (where character_role = 'Main')      as num_main_roles,
    list(distinct voice_language)                                            as languages
from {{ ref('stg_jikan__characters') }}
where person_id is not null
group by person_id
