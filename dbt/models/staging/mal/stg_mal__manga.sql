-- Mangás, light novels, manhwas etc. (MAL API), extração mais recente. `_payload` alimenta as pontes.
select
    mal_id                                                       as manga_id,
    payload->>'$.title'                                          as title,
    nullif(payload->>'$.alternative_titles.en', '')              as title_english,
    nullif(payload->>'$.alternative_titles.ja', '')              as title_japanese,
    coalesce(payload->>'$.main_picture.medium', payload->>'$.main_picture.large') as picture_url,
    payload->>'$.synopsis'                                       as synopsis,
    payload->>'$.media_type'                                     as media_type,
    payload->>'$.status'                                         as publishing_status,
    {{ parse_mal_date("payload->>'$.start_date'") }}             as start_date,
    {{ parse_mal_date("payload->>'$.end_date'") }}               as end_date,
    try_cast(payload->>'$.num_volumes' as integer)               as num_volumes,
    try_cast(payload->>'$.num_chapters' as integer)              as num_chapters,
    try_cast(payload->>'$.mean' as double)                       as mean_score,
    try_cast(payload->>'$.rank' as integer)                      as score_rank,
    try_cast(payload->>'$.popularity' as integer)                as popularity_rank,
    try_cast(payload->>'$.num_list_users' as bigint)             as num_list_users,
    try_cast(payload->>'$.num_scoring_users' as bigint)          as num_scoring_users,
    payload->>'$.nsfw'                                           as nsfw_level,
    extracted_at,
    payload                                                      as _payload
from {{ source('bronze', 'mal_manga') }}
where http_status = 200 and payload is not null
{{ latest_by('mal_id') }}
