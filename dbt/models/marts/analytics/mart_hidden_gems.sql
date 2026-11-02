{#
  Joias escondidas: nota alta, mas pouca gente viu.

  A nota bayesiana NÃO serve aqui: por construção ela puxa títulos pouco votados para a
  média global — exatamente os que queremos achar. (Na primeira carga real isso deixou a
  mart vazia.) Em vez dela:
  - exigimos um mínimo de votos (`hidden_gem_min_votes`) para a média já ser confiável;
  - qualidade = percentil da nota média ENTRE esses títulos;
  - popularidade = percentil de membros entre esses mesmos títulos.
#}
with eligible as (
    select *
    from {{ ref('dim_anime') }}
    where mean_score is not null
      and num_scoring_users >= {{ var('hidden_gem_min_votes') }}
      and media_type in ('tv', 'movie', 'ona', 'ova')
),

ranked as (
    select
        *,
        percent_rank() over (order by num_list_users) as members_pct,
        percent_rank() over (order by mean_score)     as quality_pct
    from eligible
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
    num_scoring_users,
    num_list_users,
    round(members_pct, 3)                as members_percentile,
    round(quality_pct, 3)                as quality_percentile,
    round(quality_pct - members_pct, 3)  as gem_score,
    mal_url
from ranked
where quality_pct >= {{ var('hidden_gem_min_quality_pct') }}
  and members_pct <= {{ var('hidden_gem_max_members_pct') }}
