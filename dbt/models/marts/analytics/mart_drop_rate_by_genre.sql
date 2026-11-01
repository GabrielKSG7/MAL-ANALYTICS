{#
  Comportamento real dos usuários (Kaggle): que gêneros as pessoas mais abandonam?
  drop_rate = dropped / (completed + dropped), contando cada interação uma vez por gênero.
#}
with interactions as (
    select r.mal_id, r.list_status, r.user_score
    from {{ ref('fct_user_rating') }} r
    where r.list_status in ('completed', 'dropped')
)

select
    g.genre_id,
    dg.genre_name,
    count(*)                                                       as num_interactions,
    count(*) filter (where i.list_status = 'dropped')              as num_dropped,
    round(avg(case when i.list_status = 'dropped' then 1.0 else 0.0 end), 4) as drop_rate,
    round(avg(i.user_score) filter (where i.list_status = 'completed'), 3)  as avg_score_when_completed,
    round(avg(i.user_score) filter (where i.list_status = 'dropped'), 3)    as avg_score_when_dropped
from interactions i
join {{ ref('bridge_anime_genre') }} g using (mal_id)
join {{ ref('dim_genre') }} dg using (genre_id)
group by g.genre_id, dg.genre_name
