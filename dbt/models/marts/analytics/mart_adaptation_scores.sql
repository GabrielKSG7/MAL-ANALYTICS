-- Obra original × adaptação: a nota do anime fica acima ou abaixo da do mangá/LN?
select
    m.manga_id,
    m.title                                   as manga_title,
    m.media_type                              as source_type,
    m.mean_score                              as manga_score,
    a.mal_id,
    a.title                                   as anime_title,
    a.media_type                              as anime_media_type,
    a.mean_score                              as anime_score,
    round(a.mean_score - m.mean_score, 2)     as anime_minus_manga,
    a.main_studio_name,
    a.season_year,
    date_diff('year', m.start_date, a.start_date) as years_after_original
from {{ ref('bridge_manga_anime') }} b
join {{ ref('dim_manga') }} m using (manga_id)
join {{ ref('dim_anime') }} a using (mal_id)
where b.relation_type = 'adaptation'
  and m.mean_score is not null and a.mean_score is not null
  and a.media_type in ('tv', 'movie', 'ona')
