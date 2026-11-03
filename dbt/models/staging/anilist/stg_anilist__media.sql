{{ config(materialized='table') }}
-- Anime na AniList (extração mais recente por ID do MAL).
-- O JSON (que traz elenco e staff, dezenas de KB por anime) é lido UMA vez aqui, com o tipo de todos os
-- campos usados; personagens, staff, estúdios e tags saem como listas tipadas para os modelos filhos.
-- Reabrir o JSON em cada modelo filho não escala para ~30 mil animes (mesma lição do mangá).
with parsed as (
    select mal_id, extracted_at, from_json(payload, '{{ anilist_media_type() }}') as j
    from {{ latest_success(source('bronze', 'anilist_media')) }} as src
)

select
    mal_id,
    j.id                                   as anilist_id,
    j.title.romaji                         as title_romaji,
    j.title.english                        as title_english,
    j.title.native                         as title_native,
    j.favourites                           as anilist_favourites,
    j.averageScore                         as anilist_average_score,
    j.popularity                           as anilist_popularity,
    j.countryOfOrigin                      as country_of_origin,
    coalesce(j.truncated, false)           as cast_truncated,
    extracted_at,
    j.characters                           as _characters,
    j.staff                                as _staff,
    j.studios.edges                        as _studios,
    j.tags                                 as _tags
from parsed
