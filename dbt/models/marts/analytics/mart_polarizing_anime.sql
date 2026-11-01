-- "Ame ou odeie": animes com distribuição de notas mais dividida (exige volume mínimo de votos).
select
    a.mal_id,
    a.title,
    a.media_type,
    a.season_year,
    a.main_studio_name,
    a.genres_label,
    a.mean_score,
    d.total_votes,
    round(d.score_stddev, 3)         as score_stddev,
    round(d.polarization_index, 4)   as polarization_index,
    round(d.normalized_entropy, 4)   as normalized_entropy,
    round(d.share_9_10, 4)           as share_9_10,
    round(d.share_1_4, 4)            as share_1_4,
    d.mode_score,
    rank() over (order by d.polarization_index desc) as polarization_rank
from {{ ref('dim_anime') }} a
join {{ ref('int_anime__score_dispersion') }} d using (mal_id)
where d.total_votes >= {{ var('polarization_min_votes') }}
