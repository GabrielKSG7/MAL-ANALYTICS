select mal_id, studio_id, is_main_studio
from {{ ref('stg_mal__anime_studios') }}
