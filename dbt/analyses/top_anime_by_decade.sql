-- Exemplo de consulta ad-hoc (dbt compile → target/compiled/.../analyses):
-- top 5 por década usando a nota bayesiana.
select decade, title, mean_score, weighted_score, num_list_users
from {{ ref('dim_anime') }}
where media_type in ('tv', 'movie') and weighted_score is not null
qualify row_number() over (partition by decade order by weighted_score desc) <= 5
order by decade desc, weighted_score desc
