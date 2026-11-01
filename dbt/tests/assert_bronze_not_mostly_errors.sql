-- Observabilidade da ingestão: se mais de 20% das extrações da última execução falharam
-- (fora 404, que é esperado no crawl por ID), algo está errado — rate limit, token, API fora.
{{ config(severity='warn') }}

with last_run as (
    select run_id from {{ source('bronze', 'mal_anime') }}
    order by extracted_at desc limit 1
)
select
    count(*)                                                            as attempts,
    count(*) filter (where http_status not in (200, 404))               as failures
from {{ source('bronze', 'mal_anime') }}
where run_id = (select run_id from last_run)
having count(*) filter (where http_status not in (200, 404)) > 0.2 * count(*)
