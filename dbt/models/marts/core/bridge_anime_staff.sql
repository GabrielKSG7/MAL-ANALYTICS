-- Créditos de staff: anime × pessoa × papel (com o grupo normalizado do papel).
select mal_id, person_id, role, role_base, role_group
from {{ ref('stg_anilist__staff_roles') }}
