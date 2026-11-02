-- Anime na AniList (extração mais recente por ID do MAL). `_payload` alimenta os demais modelos.
select
    mal_id,
    try_cast(payload->>'$.id' as integer)                 as anilist_id,
    payload->>'$.title.romaji'                            as title_romaji,
    payload->>'$.title.english'                           as title_english,
    payload->>'$.title.native'                            as title_native,
    try_cast(payload->>'$.favourites' as integer)         as anilist_favourites,
    try_cast(payload->>'$.averageScore' as integer)       as anilist_average_score,
    try_cast(payload->>'$.popularity' as integer)         as anilist_popularity,
    payload->>'$.countryOfOrigin'                         as country_of_origin,
    coalesce(try_cast(payload->>'$.truncated' as boolean), false) as cast_truncated,
    extracted_at,
    payload                                               as _payload
from {{ source('bronze', 'anilist_media') }}
where http_status = 200 and payload is not null
{{ latest_by('mal_id') }}
