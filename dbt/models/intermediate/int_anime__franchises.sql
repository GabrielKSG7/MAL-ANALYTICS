{{ config(materialized='table') }}
{#
  Franquia = componente conexo do grafo de relações do MAL, considerando só relações
  "fortes" (var franchise_relation_types). Relações como `character` e `other` ficam de fora
  porque ligam obras sem relação narrativa e acabariam juntando franquias inteiras.

  Implementação: alcançabilidade via CTE recursiva. Cada nó "propaga" seu próprio ID; o
  franchise_id de um anime é o menor ID que o alcança — determinístico e estável.
  UNION (e não UNION ALL) elimina duplicatas a cada iteração e garante a parada em ciclos.
#}
with recursive

nodes as (
    select mal_id from {{ ref('stg_mal__anime') }}
),

directed as (
    select r.mal_id as src, r.related_mal_id as dst
    from {{ ref('stg_mal__anime_relations') }} r
    where r.relation_type in (
        {%- for t in var('franchise_relation_types') %}'{{ t }}'{{ ',' if not loop.last }}{% endfor -%}
    )
),

edges as (
    -- o grafo é tratado como não-direcionado e restrito a animes que conhecemos
    select src, dst from directed
    union
    select dst, src from directed
),

known_edges as (
    select e.src, e.dst
    from edges e
    join nodes a on a.mal_id = e.src
    join nodes b on b.mal_id = e.dst
),

reach(root, node) as (
    select mal_id, mal_id from nodes
    union
    select reach.root, known_edges.dst
    from reach
    join known_edges on known_edges.src = reach.node
),

components as (
    select node as mal_id, min(root) as franchise_id
    from reach
    group by node
)

select
    mal_id,
    franchise_id,
    count(*) over (partition by franchise_id) as franchise_size
from components
