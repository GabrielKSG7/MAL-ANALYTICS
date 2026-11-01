{#
  Dimensão central: um anime por linha, com tudo o que as análises costumam precisar
  já resolvido (estúdio principal, gêneros, franquia, nota bayesiana, polarização,
  taxas de conclusão/abandono e IDs cruzados com outros sites).
#}
with anime as (
    select * from {{ ref('stg_mal__anime') }}
),

genres as (
    select
        mal_id,
        list(genre_name order by genre_name)                 as genres,
        string_agg(genre_name, ', ' order by genre_name)     as genres_label
    from {{ ref('stg_mal__anime_genres') }}
    group by mal_id
),

main_studio as (
    select mal_id, studio_id, studio_name
    from {{ ref('stg_mal__anime_studios') }}
    where is_main_studio
),

relations as (
    select
        mal_id,
        bool_or(relation_type = 'prequel')  as has_prequel,
        bool_or(relation_type = 'sequel')   as has_sequel
    from {{ ref('stg_mal__anime_relations') }}
    group by mal_id
),

manami as (
    select mal_id, anilist_id, kitsu_id, anidb_id, tags, cross_site_score_median
    from {{ ref('stg_manami__anime') }}
)

select
    a.mal_id,
    a.title,
    a.title_english,
    a.title_japanese,
    'https://myanimelist.net/anime/' || a.mal_id                      as mal_url,
    a.picture_url,
    a.synopsis,

    -- formato e produção
    a.media_type,
    a.airing_status,
    a.num_episodes,
    round(a.episode_duration_sec / 60.0, 1)                           as episode_duration_min,
    round(a.num_episodes * a.episode_duration_sec / 3600.0, 1)        as total_runtime_hours,
    a.source_material,
    a.age_rating,
    ms.studio_id                                                      as main_studio_id,
    ms.studio_name                                                    as main_studio_name,
    g.genres,
    g.genres_label,
    m.tags,

    -- tempo
    a.start_date,
    a.end_date,
    a.start_date_precision,
    coalesce(a.season_year, year(a.start_date))                       as season_year,
    a.season_name,
    {{ season_key('a.season_year', 'a.season_name') }}                as season_key,
    (coalesce(a.season_year, year(a.start_date)) // 10) * 10           as decade,

    -- franquia
    f.franchise_id,
    f.franchise_size,
    coalesce(r.has_prequel, false)                                    as is_sequel,
    coalesce(r.has_sequel, false)                                     as has_sequel,

    -- recepção
    a.mean_score,
    round(w.weighted_score, 3)                                        as weighted_score,
    a.score_rank,
    a.popularity_rank,
    a.num_list_users,
    a.num_scoring_users,
    case
        when a.mean_score >= 8.5 then '8.5+ excelente'
        when a.mean_score >= 8.0 then '8.0–8.49 ótimo'
        when a.mean_score >= 7.0 then '7.0–7.99 bom'
        when a.mean_score >= 6.0 then '6.0–6.99 mediano'
        when a.mean_score is not null then '< 6.0 fraco'
        else 'sem nota'
    end                                                               as score_band,
    a.status_completed::double
        / nullif(a.status_completed + a.status_dropped, 0)            as completion_rate,
    a.status_dropped::double / nullif(a.num_list_users, 0)            as drop_rate,
    a.status_plan_to_watch::double / nullif(a.num_list_users, 0)      as plan_to_watch_share,
    d.score_stddev,
    d.polarization_index,
    d.normalized_entropy,
    d.share_10,

    -- ponte com outros sites
    m.anilist_id,
    m.kitsu_id,
    m.anidb_id,
    m.cross_site_score_median,

    a.extracted_at                                                    as last_extracted_at
from anime a
left join genres g                                  using (mal_id)
left join main_studio ms                            using (mal_id)
left join relations r                               using (mal_id)
left join manami m                                  using (mal_id)
left join {{ ref('int_anime__franchises') }} f      using (mal_id)
left join {{ ref('int_anime__weighted_score') }} w  using (mal_id)
left join {{ ref('int_anime__score_dispersion') }} d using (mal_id)
