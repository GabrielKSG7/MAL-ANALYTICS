{#
  Interações usuário × anime (Kaggle hernan4444, 2020).
  - user_key: hash do user_id original → pseudonimização (não expomos o ID do dataset nas marts).
  - score 0 no MAL significa "sem nota" → NULL.
#}
select
    md5('kaggle:' || cast(user_id as varchar))  as user_key,
    anime_id                                    as mal_id,
    nullif(score, 0)                            as user_score,
    watching_status                             as status_code,
    case watching_status
        when 1 then 'watching'
        when 2 then 'completed'
        when 3 then 'on_hold'
        when 4 then 'dropped'
        when 6 then 'plan_to_watch'
        else 'unknown'
    end                                         as list_status,
    watched_episodes                            as episodes_watched,
    source_file
from {{ source('bronze', 'kaggle_animelist') }}
where user_id is not null and anime_id is not null
