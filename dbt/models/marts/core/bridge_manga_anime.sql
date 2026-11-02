-- Mangá × anime (adaptações e demais ligações declaradas no MAL), só para animes conhecidos.
select l.manga_id, l.mal_id, l.relation_type
from {{ ref('stg_mal__manga_anime_links') }} l
join {{ ref('dim_anime') }} using (mal_id)
