{#
  Diretores (papel "Director", "Chief Director" ou "Series Director"): quantidade de obras,
  qualidade típica (mediana), consistência e a melhor obra. Exige ao menos 3 obras com nota.
#}
with works as (
    select s.person_id, a.mal_id, a.title, a.mean_score, a.weighted_score, a.num_list_users, a.season_year,
           a.main_studio_name
    from {{ ref('bridge_anime_staff') }} s
    join {{ ref('dim_anime') }} a using (mal_id)
    where s.role_group = 'Direção' and a.mean_score is not null
      and a.media_type in ('tv', 'movie', 'ona', 'ova')
)

select
    w.person_id,
    p.person_name,
    p.person_name_native,
    count(distinct w.mal_id)                            as num_titles,
    round(median(w.mean_score), 3)                      as median_score,
    round(avg(w.mean_score), 3)                         as avg_score,
    round(stddev_samp(w.mean_score), 3)                 as score_stddev,
    round(sum(w.weighted_score * w.num_list_users) / nullif(sum(w.num_list_users), 0), 3) as members_weighted_score,
    sum(w.num_list_users)                               as total_members,
    arg_max(w.title, {'s': w.weighted_score, 't': w.title}) as best_title,
    arg_max(w.mean_score, {'s': w.weighted_score, 't': w.title}) as best_score,  -- nota da melhor obra
    mode(w.main_studio_name)                            as usual_studio,
    min(w.season_year)                                  as first_year,
    max(w.season_year)                                  as last_year,
    p.favourites                                        as person_favourites
from works w
join {{ ref('dim_person') }} p using (person_id)
group by w.person_id, p.person_name, p.person_name_native, p.favourites
having count(distinct w.mal_id) >= 3
