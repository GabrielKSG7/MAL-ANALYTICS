{#
  "Por que isso ainda não virou anime?" — obras populares e bem avaliadas sem adaptação.
  Considera mangá, light novel, manhwa, manhua e novel com volume mínimo de votos.
#}
select
    manga_id,
    title,
    media_type,
    publishing_status,
    start_year,
    authors_label,
    magazines_label,
    genres_label,
    mean_score,
    num_list_users,
    num_scoring_users,
    num_volumes,
    num_chapters,
    rank() over (order by num_list_users desc) as popularity_rank_unadapted,
    mal_url
from {{ ref('dim_manga') }}
where not has_anime_adaptation
  and mean_score >= 7.5
  and num_scoring_users >= 1000
  and media_type in ('manga', 'light_novel', 'manhwa', 'manhua', 'novel')
