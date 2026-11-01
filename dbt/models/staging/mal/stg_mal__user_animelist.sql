-- Lista pública do usuário: só a extração mais recente de cada username conta
-- (itens removidos da lista somem na extração seguinte).
with source as (
    select * from {{ source('bronze', 'mal_user_animelist') }}
),

latest_extraction as (
    select *
    from source
    qualify extracted_at = max(extracted_at) over (partition by username)
)

select
    username,
    try_cast(payload->>'$.node.id' as integer)                       as mal_id,
    payload->>'$.node.title'                                          as title,
    payload->>'$.list_status.status'                                  as list_status,
    nullif(try_cast(payload->>'$.list_status.score' as integer), 0)   as user_score,
    try_cast(payload->>'$.list_status.num_episodes_watched' as integer) as episodes_watched,
    coalesce(try_cast(payload->>'$.list_status.is_rewatching' as boolean), false) as is_rewatching,
    coalesce(try_cast(payload->>'$.list_status.num_times_rewatched' as integer), 0) as times_rewatched,
    {{ parse_mal_date("payload->>'$.list_status.start_date'") }}      as started_on,
    {{ parse_mal_date("payload->>'$.list_status.finish_date'") }}     as finished_on,
    try_cast(payload->>'$.list_status.updated_at' as timestamptz)     as list_updated_at,
    extracted_at
from latest_extraction
