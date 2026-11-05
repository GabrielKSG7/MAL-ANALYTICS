-- Mangá × anime (adaptações e demais ligações, MAL + AniList), só para animes conhecidos.
select l.manga_id, l.mal_id, l.relation_type, l.link_sources
from {{ ref('int_manga__anime_links') }} l
join {{ ref('dim_anime') }} using (mal_id)
