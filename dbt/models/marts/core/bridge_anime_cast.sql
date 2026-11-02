-- Elenco: anime × personagem × dublador (um personagem sem dublador aparece com person_id nulo).
select
    c.mal_id,
    c.character_id,
    c.character_role,
    v.person_id,
    v.voice_language
from {{ ref('stg_anilist__characters') }} c
left join {{ ref('stg_anilist__voice_actors') }} v using (mal_id, character_id)
