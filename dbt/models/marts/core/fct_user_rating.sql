{#
  Fato de interações usuário × anime (Kaggle). Grão: user_key × mal_id.
  Inclui todos os status (inclusive plan_to_watch e dropped, que são sinal implícito),
  e a nota normalizada quando existe.
#}
select
    k.user_key,
    k.mal_id,
    k.list_status,
    k.user_score,
    k.episodes_watched,
    n.score_centered,
    n.score_z,
    k.list_status = 'dropped'   as is_dropped,
    k.list_status = 'completed' as is_completed
from {{ ref('stg_kaggle__animelist') }} k
left join {{ ref('int_users__ratings_normalized') }} n using (user_key, mal_id)
