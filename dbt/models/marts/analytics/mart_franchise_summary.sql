{#
  Uma linha por franquia (2+ entradas).

  - Nome: o título mais popular da franquia. (Usar o mais antigo trazia pilotos e OVAs
    obscuros, ex.: "Lupin III: Pilot Film" em vez de "Lupin III".)
  - Evolução da nota: compara a PRIMEIRA e a ÚLTIMA entrada de TV com nota. Especiais,
    recaps e curtas distorciam a comparação.
#}
with entries as (
    select *
    from {{ ref('dim_anime') }}
    where franchise_size >= 2
),

tv as (
    select franchise_id, start_date, mean_score, title
    from entries
    where media_type = 'tv' and mean_score is not null and start_date is not null
)

select
    e.franchise_id,
    arg_max(e.title, coalesce(e.num_list_users, 0))                         as franchise_name,
    count(*)                                                                as num_entries,
    count(*) filter (where e.media_type = 'tv')                             as num_tv_entries,
    sum(e.num_episodes)                                                     as total_episodes,
    round(sum(e.total_runtime_hours), 1)                                    as total_runtime_hours,
    min(e.season_year)                                                      as first_year,
    max(e.season_year)                                                      as last_year,
    round(avg(e.mean_score), 3)                                             as avg_score,
    max(e.mean_score)                                                       as best_score,
    arg_max(e.title, {'s': e.mean_score, 'm': e.num_list_users, 't': e.title}) as best_entry,
    any_value(t.first_tv_title)                                             as first_tv_entry,
    any_value(t.first_tv_score)                                             as first_entry_score,
    any_value(t.latest_tv_title)                                            as latest_tv_entry,
    any_value(t.latest_tv_score)                                            as latest_entry_score,
    round(any_value(t.latest_tv_score) - any_value(t.first_tv_score), 3)    as score_change_first_to_latest,
    max(e.num_list_users)                                                   as peak_members,
    sum(e.num_list_users)                                                   as total_members
from entries e
left join (
    select
        franchise_id,
        arg_min(title, start_date)      as first_tv_title,
        arg_min(mean_score, start_date) as first_tv_score,
        arg_max(title, start_date)      as latest_tv_title,
        arg_max(mean_score, start_date) as latest_tv_score,
        count(*)                        as n_tv
    from tv
    group by franchise_id
    having count(*) >= 2
) t using (franchise_id)
group by e.franchise_id
