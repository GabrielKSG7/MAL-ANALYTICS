-- Quem dubla cada personagem em cada anime, por idioma.
with edges as (
    select
        mal_id,
        unnest(_characters) as e
    from {{ ref('stg_anilist__media') }}
),

roles as (
    select mal_id, e.node.id as character_id, e.role, unnest(e.voiceActorRoles) as r
    from edges
)

select distinct
    mal_id,
    character_id,
    r.voiceActor.id               as person_id,
    r.voiceActor.languageV2       as voice_language,
    r.roleNotes                   as role_notes,
    r.dubGroup                    as dub_group
from roles
where r.voiceActor.id is not null and character_id is not null
