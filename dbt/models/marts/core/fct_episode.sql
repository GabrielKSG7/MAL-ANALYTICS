-- Episódios (Kitsu) ligados ao anime do MAL. Grão: anime × número do episódio.
select
    e.mal_id,
    e.episode_number,
    e.season_number,
    e.episode_title,
    e.aired_on,
    year(e.aired_on)                                                    as aired_year,
    e.length_min,
    e.aired_on - lag(e.aired_on) over (partition by e.mal_id order by e.episode_number) as days_since_previous,
    e.synopsis
from {{ ref('stg_kitsu__episodes') }} e
join {{ ref('dim_anime') }} a using (mal_id)
