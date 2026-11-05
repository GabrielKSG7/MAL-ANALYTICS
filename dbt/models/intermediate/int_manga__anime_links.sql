{#
  Ligações mangá × anime de duas fontes, no vocabulário do MAL:
  - MAL: `related_anime` do mangá (na prática quase sempre vazio na API);
  - AniList: relações do anime. `SOURCE` = o mangá é a obra de origem → 'adaptation'.
    `ADAPTATION` aponta o contrário (mangá derivado do anime) e vira 'derived_work'.
  `link_sources` mostra quem confirmou cada ligação.
#}
with mal as (
    select manga_id, mal_id, relation_type, 'mal' as link_source
    from {{ ref('stg_mal__manga_anime_links') }}
),

anilist as (
    select
        related_mal_id as manga_id,
        mal_id,
        case relation_type
            when 'SOURCE'      then 'adaptation'
            when 'ADAPTATION'  then 'derived_work'
            when 'ALTERNATIVE' then 'alternative_version'
            when 'PARENT'      then 'parent_story'
            when 'SIDE_STORY'  then 'side_story'
            when 'SPIN_OFF'    then 'spin_off'
            when 'SUMMARY'     then 'summary'
            else lower(relation_type)
        end as relation_type,
        'anilist' as link_source
    from {{ ref('stg_anilist__relations') }}
    where related_type = 'MANGA' and related_mal_id is not null
)

select manga_id, mal_id, relation_type, string_agg(distinct link_source, '+' order by link_source) as link_sources
from (select * from mal union all select * from anilist)
group by all
