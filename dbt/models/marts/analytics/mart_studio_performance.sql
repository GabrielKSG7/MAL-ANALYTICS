{#
  Ranking de estúdios: qualidade (nota bayesiana ponderada por votos), consistência
  (desvio-padrão entre títulos), alcance (membros) e o melhor título de cada um.
  Considera apenas o estúdio principal de cada anime e TV/filme/ONA (exclui PVs, CMs etc.).
#}
with base as (
    select *
    from {{ ref('dim_anime') }}
    where main_studio_id is not null
      and mean_score is not null
      and media_type in ('tv', 'movie', 'ona', 'ova', 'special', 'tv_special')
),

agg as (
    select
        main_studio_id                                                        as studio_id,
        any_value(main_studio_name)                                           as studio_name,
        count(*)                                                              as num_titles,
        min(season_year)                                                      as first_year,
        max(season_year)                                                      as last_year,
        sum(weighted_score * num_scoring_users) / sum(num_scoring_users)      as vote_weighted_score,
        avg(weighted_score)                                                   as avg_weighted_score,
        median(mean_score)                                                    as median_score,
        stddev_samp(mean_score)                                               as score_stddev,
        avg(case when mean_score >= 8 then 1.0 else 0.0 end)                  as share_titles_8_plus,
        sum(num_list_users)                                                   as total_members,
        arg_max(title, {'s': weighted_score, 't': title})                   as best_title,
        max(weighted_score)                                                   as best_weighted_score,
        arg_min(title, weighted_score)                                        as worst_title,
        avg(case when is_sequel then 1.0 else 0.0 end)                        as share_sequels,
        mode(source_material)                                                 as most_common_source
    from base
    group by main_studio_id
    having count(*) >= {{ var('studio_min_titles') }}
)

select
    *,
    rank() over (order by vote_weighted_score desc)  as quality_rank,
    rank() over (order by score_stddev asc)          as consistency_rank,
    rank() over (order by total_members desc)        as reach_rank
from agg
