select
    mal_id,
    character_id,
    person_id,
    character_role,
    voice_language
from {{ ref('stg_jikan__characters') }}
