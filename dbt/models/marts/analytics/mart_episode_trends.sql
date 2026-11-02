-- Episódios exibidos por ano: volume, duração média e quantos animes estavam no ar.
select
    e.aired_year,
    count(*)                                           as episodes_aired,
    count(distinct e.mal_id)                           as anime_airing,
    round(avg(e.length_min), 1)                        as avg_length_min,
    round(sum(e.length_min) / 60.0)                    as total_hours,
    round(avg(case when a.media_type = 'ona' then 1.0 else 0.0 end), 3) as share_web_episodes
from {{ ref('fct_episode') }} e
join {{ ref('dim_anime') }} a using (mal_id)
where e.aired_year between 1960 and year(current_date)
group by e.aired_year
