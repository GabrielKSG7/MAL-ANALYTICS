{{
  config(
    materialized='incremental',
    unique_key=['mal_id', 'snapshot_date'],
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns'
  )
}}
{#
  Série temporal de métricas: uma linha por anime por dia de extração.
  Incremental: a cada execução só processa extrações a partir do último dia já carregado
  (reprocessando esse dia, caso tenha havido nova extração nele).
#}
with extractions as (
    select *
    from {{ ref('stg_mal__anime_extractions') }}
    {% if is_incremental() %}
    where snapshot_date >= (select coalesce(max(snapshot_date), date '1900-01-01') from {{ this }})
    {% endif %}
    qualify row_number() over (partition by mal_id, snapshot_date order by extracted_at desc) = 1
)

select
    mal_id,
    snapshot_date,
    mean_score,
    score_rank,
    popularity_rank,
    num_list_users,
    num_scoring_users,
    status_watching,
    status_completed,
    status_on_hold,
    status_dropped,
    status_plan_to_watch,
    extracted_at
from extractions
