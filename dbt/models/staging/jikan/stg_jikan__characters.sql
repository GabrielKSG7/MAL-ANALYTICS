-- Elenco: uma linha por (anime, personagem, dublador). Personagem sem dublador continua
-- presente com person_id nulo (a lista vazia é trocada por um elemento nulo antes do unnest,
-- senão o unnest descartaria a linha).
with latest as (
    select mal_id, payload
    from {{ source('bronze', 'jikan_characters') }}
    where http_status = 200 and payload is not null
    {{ latest_by('mal_id') }}
),

characters as (
    select
        mal_id,
        unnest(
            from_json(
                payload,
                '[{"character": {"mal_id": "INTEGER", "name": "VARCHAR"}, "role": "VARCHAR", "favorites": "INTEGER",
                   "voice_actors": [{"person": {"mal_id": "INTEGER", "name": "VARCHAR"}, "language": "VARCHAR"}]}]'
            )
        ) as c
    from latest
),

flattened as (
    select
        mal_id,
        c.character.mal_id as character_id,
        c.character.name   as character_name,
        c.role             as character_role,
        c.favorites        as character_favorites,
        unnest(
            case when len(c.voice_actors) = 0
                 then [{'person': {'mal_id': null::integer, 'name': null::varchar}, 'language': null::varchar}]
                 else c.voice_actors end
        ) as va
    from characters
)

select
    mal_id,
    character_id,
    character_name,
    character_role,
    character_favorites,
    va.person.mal_id as person_id,
    va.person.name   as person_name,
    va.language      as voice_language
from flattened
where character_id is not null
