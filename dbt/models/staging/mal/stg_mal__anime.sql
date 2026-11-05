-- Estado atual de cada anime: a extração mais recente.
select
    * exclude (_genres, _studios, _related_anime)
from {{ ref('stg_mal__anime_extractions') }}
{{ latest_by('mal_id') }}
