-- Uma linha por mangá/light novel/manhwa do MAL, com autores, revista e se virou anime.
with genres as (
    select manga_id, list(genre_name order by genre_name) as genres,
           string_agg(genre_name, ', ' order by genre_name) as genres_label
    from {{ ref('stg_mal__manga_genres') }} group by manga_id
),
authors as (
    select manga_id, string_agg(author_name || coalesce(' (' || author_role || ')', ''), '; ') as authors_label
    from {{ ref('stg_mal__manga_authors') }} group by manga_id
),
magazines as (
    select manga_id, string_agg(magazine_name, '; ') as magazines_label
    from {{ ref('stg_mal__manga_serialization') }} group by manga_id
),
adaptations as (
    select l.manga_id,
           count(distinct l.mal_id)                                  as num_anime_adaptations,
           arg_max(a.title, coalesce(a.num_list_users, 0))           as main_adaptation_title,
           arg_max(a.mean_score, coalesce(a.num_list_users, 0))      as main_adaptation_score,
           min(a.start_date)                                         as first_adaptation_date
    from {{ ref('int_manga__anime_links') }} l
    join {{ ref('dim_anime') }} a using (mal_id)
    where l.relation_type in ('adaptation', 'alternative_version', 'full_story', 'parent_story')
    group by l.manga_id
)

select
    m.manga_id,
    m.title,
    m.title_english,
    'https://myanimelist.net/manga/' || m.manga_id          as mal_url,
    m.picture_url,
    m.media_type,
    m.publishing_status,
    m.start_date,
    m.end_date,
    year(m.start_date)                                      as start_year,
    m.num_volumes,
    m.num_chapters,
    m.mean_score,
    m.score_rank,
    m.popularity_rank,
    m.num_list_users,
    m.num_scoring_users,
    g.genres,
    g.genres_label,
    au.authors_label,
    mg.magazines_label,
    coalesce(ad.num_anime_adaptations, 0) > 0               as has_anime_adaptation,
    coalesce(ad.num_anime_adaptations, 0)                   as num_anime_adaptations,
    ad.main_adaptation_title,
    ad.main_adaptation_score,
    date_diff('year', m.start_date, ad.first_adaptation_date) as years_until_adaptation
from {{ ref('stg_mal__manga') }} m
left join genres g using (manga_id)
left join authors au using (manga_id)
left join magazines mg using (manga_id)
left join adaptations ad using (manga_id)
