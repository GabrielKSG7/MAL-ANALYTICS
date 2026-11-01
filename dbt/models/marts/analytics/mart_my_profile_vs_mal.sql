{#
  "Meu perfil vs MAL": onde a sua nota diverge da comunidade, recortado por várias dimensões.
  Formato longo (dimension, value) para alimentar um único gráfico no dashboard.
  delta_avg > 0 → você avalia acima da média do MAL naquele recorte.
#}
with scored as (
    select *
    from {{ ref('fct_my_list') }}
    where user_score is not null and mal_mean_score is not null
),

by_genre as (
    select username, 'genre' as dimension, unnest(genres) as value, user_score, mal_mean_score, score_delta
    from scored
),

by_studio as (
    select username, 'studio', main_studio_name, user_score, mal_mean_score, score_delta
    from scored where main_studio_name is not null
),

by_media as (
    select username, 'media_type', media_type, user_score, mal_mean_score, score_delta
    from scored
),

by_decade as (
    select username, 'decade', cast((season_year // 10) * 10 as varchar) || 's', user_score, mal_mean_score, score_delta
    from scored where season_year is not null
),

overall as (
    select username, 'overall', 'all', user_score, mal_mean_score, score_delta
    from scored
),

unioned as (
    select * from by_genre
    union all select * from by_studio
    union all select * from by_media
    union all select * from by_decade
    union all select * from overall
)

select
    username,
    dimension,
    value,
    count(*)                          as num_titles,
    round(avg(user_score), 3)         as my_avg_score,
    round(avg(mal_mean_score), 3)     as mal_avg_score,
    round(avg(score_delta), 3)        as delta_avg,
    round(corr(user_score, mal_mean_score), 3) as correlation_with_mal
from unioned
group by username, dimension, value
