{#
  Normaliza a nota de cada usuário (z-score): um 7 de alguém que dá 9 pra tudo vale
  menos que um 7 de alguém exigente. Base para análises de "gosto" sem viés de escala
  e para o recomendador.
#}
with rated as (
    select user_key, mal_id, user_score, list_status
    from {{ ref('stg_kaggle__animelist') }}
    where user_score is not null
),

user_stats as (
    select
        user_key,
        count(*)                as n_ratings,
        avg(user_score)         as user_mean,
        stddev_pop(user_score)  as user_stddev
    from rated
    group by user_key
    having count(*) >= {{ var('user_min_ratings') }}
)

select
    r.user_key,
    r.mal_id,
    r.user_score,
    r.list_status,
    s.n_ratings,
    s.user_mean,
    s.user_stddev,
    r.user_score - s.user_mean                                   as score_centered,
    (r.user_score - s.user_mean) / nullif(s.user_stddev, 0)      as score_z
from rated r
join user_stats s using (user_key)
