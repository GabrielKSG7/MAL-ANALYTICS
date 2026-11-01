-- Estado atual de cada anime: a extração mais recente.
select
    * exclude (_payload)
from {{ ref('stg_mal__anime_extractions') }}
{{ latest_by('mal_id') }}
