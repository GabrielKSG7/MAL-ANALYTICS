-- Gênero × ano: participação no catálogo, qualidade média e audiência.
with base as (
    select a.mal_id, a.season_year, a.mean_score, a.num_list_users, g.genre_id, g.allocation_weight
    from {{ ref('dim_anime') }} a
    join {{ ref('bridge_anime_genre') }} g using (mal_id)
    where a.season_year is not null and a.media_type in ('tv', 'ona', 'movie')
),

year_totals as (
    select season_year, count(distinct mal_id) as titles_in_year
    from base
    group by season_year
)

select
    b.season_year,
    b.genre_id,
    dg.genre_name,
    count(distinct b.mal_id)                                         as num_titles,
    round(count(distinct b.mal_id)::double / yt.titles_in_year, 4)   as share_of_year,
    round(avg(b.mean_score), 3)                                      as avg_score,
    sum(b.num_list_users)                                            as total_members,
    round(sum(b.num_list_users * b.allocation_weight))::bigint       as allocated_members
from base b
join year_totals yt using (season_year)
join {{ ref('dim_genre') }} dg using (genre_id)
group by b.season_year, b.genre_id, dg.genre_name, yt.titles_in_year
