-- A sua lista no MAL cruzada com a visão da comunidade.
select
    l.username,
    l.mal_id,
    coalesce(a.title, l.title)                                       as title,
    l.list_status,
    l.user_score,
    a.mean_score                                                     as mal_mean_score,
    round(l.user_score - a.mean_score, 2)                            as score_delta,
    l.episodes_watched,
    round(l.episodes_watched * a.episode_duration_min / 60.0, 1)     as hours_watched,
    l.is_rewatching,
    l.times_rewatched,
    l.started_on,
    l.finished_on,
    year(l.finished_on)                                              as finished_year,
    a.media_type,
    a.season_year,
    a.main_studio_name,
    a.genres,
    a.num_list_users                                                 as mal_members,
    l.list_updated_at
from {{ ref('stg_mal__user_animelist') }} l
left join {{ ref('dim_anime') }} a using (mal_id)
