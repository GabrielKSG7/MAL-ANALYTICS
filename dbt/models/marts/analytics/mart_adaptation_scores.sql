-- Obra original × adaptação: a nota do anime fica acima ou abaixo da do mangá/LN?
-- Um anime pode ter várias obras de origem na AniList (One Piece → o mangá e one-shots como *Wanted!*);
-- a comparação usa só a principal: a mais popular entre elas.
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
    date_diff('year', m.start_date, a.start_date) as years_after_original,
    -- quantas obras de origem o anime tem (1 = comparação sem ambiguidade; é o recorte usado nos achados)
    count(*) over (partition by a.mal_id)          as num_source_works
from {{ ref('bridge_manga_anime') }} b
join {{ ref('dim_manga') }} m using (manga_id)
join {{ ref('dim_anime') }} a using (mal_id)
where b.relation_type = 'adaptation'
  and m.mean_score is not null and a.mean_score is not null
  and a.media_type in ('tv', 'movie', 'ona')
qualify row_number() over (partition by a.mal_id order by m.num_list_users desc nulls last, m.manga_id) = 1
