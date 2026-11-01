{#
  Quem está subindo? Compara a extração mais recente com a anterior de cada anime
  (o bronze guarda histórico, então isso sai de graça a cada execução semanal).
#}
with series as (
    select
        *,
        lag(snapshot_date)     over w as prev_snapshot_date,
        lag(mean_score)        over w as prev_mean_score,
        lag(num_list_users)    over w as prev_members,
        lag(score_rank)        over w as prev_score_rank,
        row_number()           over (partition by mal_id order by snapshot_date desc) as recency
    from {{ ref('fct_anime_metrics_snapshot') }}
    window w as (partition by mal_id order by snapshot_date)
)

select
    s.mal_id,
    a.title,
    a.airing_status,
    s.snapshot_date,
    s.prev_snapshot_date,
    date_diff('day', s.prev_snapshot_date, s.snapshot_date)                 as days_between,
    s.mean_score,
    round(s.mean_score - s.prev_mean_score, 3)                             as score_change,
    s.num_list_users                                                        as members,
    s.num_list_users - s.prev_members                                       as members_gained,
    round((s.num_list_users - s.prev_members)::double / nullif(s.prev_members, 0), 5) as members_growth_rate,
    s.prev_score_rank - s.score_rank                                        as rank_positions_gained
from series s
join {{ ref('dim_anime') }} a using (mal_id)
where s.recency = 1
  and s.prev_snapshot_date is not null
