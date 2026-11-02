-- Dubladores: volume de trabalho, protagonismo, qualidade média dos animes e o papel mais famoso.
with roles as (
    select c.person_id, c.mal_id, c.character_id, c.character_role, c.voice_language,
           a.mean_score, a.num_list_users, ch.character_name, ch.favourites as character_favourites, a.title
    from {{ ref('bridge_anime_cast') }} c
    join {{ ref('dim_anime') }} a using (mal_id)
    join {{ ref('dim_character') }} ch using (character_id)
    where c.person_id is not null
)

select
    r.person_id,
    p.person_name,
    p.person_name_native,
    any_value(r.voice_language)                                       as voice_language,
    p.gender,
    p.birth_date,
    p.favourites                                                      as person_favourites,
    count(distinct r.mal_id)                                          as num_anime,
    count(distinct r.character_id)                                    as num_characters,
    count(distinct r.character_id) filter (where r.character_role = 'Main') as num_main_roles,
    round(avg(r.mean_score), 3)                                       as avg_anime_score,
    sum(r.num_list_users)                                             as total_members_reached,
    arg_max(r.character_name, r.character_favourites)                 as most_famous_character,
    arg_max(r.title, r.character_favourites)                          as most_famous_character_anime,
    min(a2.season_year)                                               as first_year,
    max(a2.season_year)                                               as last_year,
    rank() over (partition by any_value(r.voice_language) order by count(distinct r.mal_id) desc) as rank_by_volume
from roles r
join {{ ref('dim_person') }} p using (person_id)
join {{ ref('dim_anime') }} a2 on a2.mal_id = r.mal_id
group by r.person_id, p.person_name, p.person_name_native, p.gender, p.birth_date, p.favourites
