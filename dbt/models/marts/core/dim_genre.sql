select
    genre_id::integer           as genre_id,
    any_value(genre_name)       as genre_name,
    count(distinct mal_id)      as num_anime
from {{ ref('stg_mal__anime_genres') }}
group by genre_id
