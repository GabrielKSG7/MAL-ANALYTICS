-- A soma dos status não pode passar muito do total de membros (tolerância de 2% para
-- diferenças de cache entre os contadores do MAL).
{{ config(severity='warn') }}

select mal_id, num_list_users,
       status_watching + status_completed + status_on_hold + status_dropped + status_plan_to_watch as status_sum
from {{ ref('stg_mal__anime') }}
where num_list_users > 0
  and (status_watching + status_completed + status_on_hold + status_dropped + status_plan_to_watch)
      > num_list_users * 1.02
