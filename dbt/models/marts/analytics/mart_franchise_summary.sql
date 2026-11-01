{#
  Uma linha por franquia (2+ entradas): tamanho, duração total, evolução da nota da
  primeira para a última entrada e audiência somada.
#}
with entries as (
    select *
    from {{ ref('dim_anime') }}
    where franchise_size >= 2
)

select
    franchise_id,
    arg_min(title, coalesce(start_date, date '2999-01-01'))                as franchise_name,
    count(*)                                                                as num_entries,
    count(*) filter (where media_type = 'tv')                               as num_tv_entries,
    sum(num_episodes)                                                       as total_episodes,
    round(sum(total_runtime_hours), 1)                                      as total_runtime_hours,
    min(season_year)                                                        as first_year,
    max(season_year)                                                        as last_year,
    round(avg(mean_score), 3)                                               as avg_score,
    max(mean_score)                                                         as best_score,
    arg_max(title, mean_score)                                              as best_entry,
    arg_min(mean_score, coalesce(start_date, date '2999-01-01'))            as first_entry_score,
    arg_max(mean_score, coalesce(start_date, date '1900-01-01'))            as latest_entry_score,
    round(
        arg_max(mean_score, coalesce(start_date, date '1900-01-01'))
        - arg_min(mean_score, coalesce(start_date, date '2999-01-01')), 3)  as score_change_first_to_latest,
    max(num_list_users)                                                     as peak_members,
    sum(num_list_users)                                                     as total_members
from entries
group by franchise_id
