{#
  Arestas do grafo de dubladores: dois seiyuus ligados quando trabalharam no mesmo anime.
  Pronto para exportar para Gephi/NetworkX ou carregar num banco de grafos.
  Considera apenas papéis principais para manter o grafo legível.
#}
with main_roles as (
    select distinct mal_id, person_id
    from {{ ref('bridge_anime_cast') }}
    where person_id is not null
      and character_role = 'Main'
      and coalesce(voice_language, 'Japanese') = 'Japanese'
)

select
    a.person_id                         as person_a,
    b.person_id                         as person_b,
    pa.person_name                      as person_a_name,
    pb.person_name                      as person_b_name,
    count(distinct a.mal_id)            as shared_anime,
    list(distinct da.title)             as shared_titles
from main_roles a
join main_roles b
  on a.mal_id = b.mal_id and a.person_id < b.person_id
join {{ ref('dim_person') }} pa on pa.person_id = a.person_id
join {{ ref('dim_person') }} pb on pb.person_id = b.person_id
join {{ ref('dim_anime') }} da on da.mal_id = a.mal_id
group by all
