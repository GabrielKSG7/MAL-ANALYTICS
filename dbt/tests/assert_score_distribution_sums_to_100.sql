-- O Jikan arredonda os percentuais por nota; a soma deve ficar perto de 100.
-- Desvios grandes indicam parsing errado ou payload truncado.
{{ config(severity='warn') }}

select mal_id, sum(percentage) as total_pct
from {{ ref('stg_jikan__score_distribution') }}
group by mal_id
having abs(sum(percentage) - 100) > 2
