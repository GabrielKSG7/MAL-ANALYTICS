select
    g.mal_id,
    g.genre_id,
    1.0 / count(*) over (partition by g.mal_id) as allocation_weight  -- evita dupla contagem em somas
from {{ ref('stg_mal__anime_genres') }} g
