-- Panorama por temporada (cour): volume, qualidade, destaque e perfil de origem.
with base as (
    select *
    from {{ ref('dim_anime') }}
    where season_key is not null
      and media_type in ('tv', 'ona')
)

select
    season_key,
    season_year,
    season_name,
    {{ season_number('season_name') }}                                         as season_number,
    count(*)                                                                    as num_titles,
    count(mean_score)                                                           as num_scored,
    round(avg(mean_score), 3)                                                   as avg_score,
    round(median(mean_score), 3)                                                as median_score,
    arg_max(title, {'s': weighted_score, 't': title})                         as top_title,
    max(mean_score)                                                             as top_score,
    arg_max(title, num_list_users)                                              as most_popular_title,
    sum(num_list_users)                                                         as total_members,
    round(avg(case when is_sequel then 1.0 else 0.0 end), 3)                    as share_sequels,
    round(avg(case when source_material = 'original' then 1.0 else 0.0 end), 3) as share_original,
    round(avg(case when source_material in ('manga', 'web_manga') then 1.0 else 0.0 end), 3) as share_manga,
    round(avg(case when source_material = 'light_novel' then 1.0 else 0.0 end), 3) as share_light_novel
from base
group by all
