{#
  Joias escondidas: nota bayesiana no quartil superior, mas poucos membros
  (abaixo do percentil `hidden_gem_max_members_pct`). A nota bayesiana evita que
  títulos com 30 votos e média 9 dominem a lista.
#}
with ranked as (
    select
        *,
        percent_rank() over (order by num_list_users)  as members_pct,
        percent_rank() over (order by weighted_score)  as quality_pct
    from {{ ref('dim_anime') }}
    where weighted_score is not null
      and media_type in ('tv', 'movie', 'ona', 'ova')
)

select
    mal_id,
    title,
    media_type,
    season_year,
    main_studio_name,
    genres_label,
    mean_score,
    weighted_score,
    num_list_users,
    round(members_pct, 3)   as members_percentile,
    round(quality_pct, 3)   as quality_percentile,
    round(quality_pct - members_pct, 3) as gem_score,
    mal_url
from ranked
where quality_pct >= 0.75
  and members_pct <= {{ var('hidden_gem_max_members_pct') }}
