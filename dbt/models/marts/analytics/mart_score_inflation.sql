{#
  As notas estão subindo com o tempo? Compara a distribuição de notas por ano de estreia.
  Atenção ao viés de sobrevivência: títulos antigos que ainda recebem votos tendem a ser
  os clássicos — por isso trazemos também a mediana e o volume de votos.
#}
select
    season_year,
    count(*)                                         as num_titles,
    round(avg(mean_score), 3)                        as avg_score,
    round(median(mean_score), 3)                     as median_score,
    round(quantile_cont(mean_score, 0.10), 3)        as p10_score,
    round(quantile_cont(mean_score, 0.90), 3)        as p90_score,
    round(avg(weighted_score), 3)                    as avg_weighted_score,
    round(avg(score_stddev), 3)                      as avg_within_title_stddev,
    sum(num_scoring_users)                           as total_votes,
    round(avg(mean_score) - avg(avg(mean_score)) over (), 3) as diff_vs_overall_avg
from {{ ref('dim_anime') }}
where mean_score is not null
  and season_year is not null
  and media_type in ('tv', 'movie', 'ona')
group by season_year
