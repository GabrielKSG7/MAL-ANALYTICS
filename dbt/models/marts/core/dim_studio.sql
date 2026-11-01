select
    s.studio_id::integer                                   as studio_id,
    any_value(s.studio_name)                               as studio_name,
    count(distinct s.mal_id)                               as num_anime,
    count(distinct s.mal_id) filter (where s.is_main_studio) as num_anime_as_main,
    min(a.season_year)::integer                            as first_year,
    max(a.season_year)::integer                            as last_year
from {{ ref('stg_mal__anime_studios') }} s
left join {{ ref('stg_mal__anime') }} a using (mal_id)
group by s.studio_id
