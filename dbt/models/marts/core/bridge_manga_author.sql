select manga_id, author_id, author_name, author_role
from {{ ref('stg_mal__manga_authors') }}
