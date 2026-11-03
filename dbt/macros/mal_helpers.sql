{#
  O MAL devolve datas parciais: "2015-04-06", "2015-04" ou só "2015".
  parse_mal_date normaliza para DATE (primeiro dia do período) e
  mal_date_precision diz qual era a precisão original.
#}
{% macro parse_mal_date(col) -%}
    case
        when {{ col }} is null or {{ col }} = '' then null
        when length({{ col }}) = 10 then try_cast({{ col }} as date)
        when length({{ col }}) = 7 then try_cast({{ col }} || '-01' as date)
        when length({{ col }}) = 4 then try_cast({{ col }} || '-01-01' as date)
    end
{%- endmacro %}

{% macro mal_date_precision(col) -%}
    case length({{ col }}) when 10 then 'day' when 7 then 'month' when 4 then 'year' end
{%- endmacro %}

{# Ordem da temporada no ano: winter=1 ... fall=4 #}
{% macro season_number(col) -%}
    case lower({{ col }}) when 'winter' then 1 when 'spring' then 2 when 'summer' then 3 when 'fall' then 4 end
{%- endmacro %}

{# Chave ordenável e legível de temporada: 2024-Q4-fall #}
{% macro season_key(year_col, season_col) -%}
    case when {{ year_col }} is not null and {{ season_col }} is not null
        then cast({{ year_col }} as varchar) || '-Q' || cast({{ season_number(season_col) }} as varchar)
             || '-' || lower({{ season_col }})
    end
{%- endmacro %}

{# Mantém só a extração mais recente de cada chave (bronze é append-only). #}
{% macro latest_by(partition_col, order_col='extracted_at') -%}
    qualify row_number() over (partition by {{ partition_col }} order by {{ order_col }} desc) = 1
{%- endmacro %}

{# Converte o contador de status (que a API manda como string) para inteiro. #}
{% macro status_count(path) -%}
    try_cast(payload->>'$.statistics.status.{{ path }}' as bigint)
{%- endmacro %}

{# Tipo JSON de uma pessoa (Staff) da AniList, reaproveitado em dubladores e staff. #}
{% macro anilist_person_type() -%}
{"id": "INTEGER", "name": {"full": "VARCHAR", "native": "VARCHAR"}, "languageV2": "VARCHAR", "gender": "VARCHAR", "favourites": "INTEGER", "primaryOccupations": ["VARCHAR"], "homeTown": "VARCHAR", "yearsActive": ["INTEGER"], "dateOfBirth": {"year": "INTEGER", "month": "INTEGER", "day": "INTEGER"}, "dateOfDeath": {"year": "INTEGER", "month": "INTEGER", "day": "INTEGER"}, "image": {"medium": "VARCHAR"}, "siteUrl": "VARCHAR"}
{%- endmacro %}

{# Data "fuzzy" da AniList ({year, month, day} com partes nulas) → DATE quando houver ano. #}
{% macro fuzzy_date(col) -%}
    case when {{ col }}.year is not null
         then make_date({{ col }}.year, coalesce({{ col }}.month, 1), coalesce({{ col }}.day, 1)) end
{%- endmacro %}

{# Normaliza o papel de staff ("Episode Director (eps 1, 5)") num grupo analítico. #}
{% macro staff_role_group(role) -%}
    case
        when {{ role }} ilike 'Original Creator%' or {{ role }} ilike 'Original Story%' then 'Criação original'
        when regexp_matches({{ role }}, '^(Chief |Series |General )?Director( \(.*\))?$') then 'Direção'
        when {{ role }} ilike 'Assistant Director%' then 'Direção assistente'
        when {{ role }} ilike 'Episode Director%' then 'Direção de episódio'
        when {{ role }} ilike 'Series Composition%' or {{ role }} ilike 'Script%'
          or {{ role }} ilike 'Screenplay%' then 'Roteiro'
        when {{ role }} ilike 'Storyboard%' then 'Storyboard'
        when {{ role }} ilike '%Character Design%' then 'Character design'
        when {{ role }} ilike 'Music%' or {{ role }} ilike 'Theme Song Composition%' then 'Música'
        when {{ role }} ilike 'Sound Director%' then 'Direção de som'
        when {{ role }} ilike 'Art Director%' then 'Direção de arte'
        when {{ role }} ilike '%Animation Director%' or {{ role }} ilike 'Key Animation%' then 'Animação'
        when {{ role }} ilike 'Producer%' or {{ role }} ilike 'Executive Producer%' then 'Produção'
        else 'Outros'
    end
{%- endmacro %}

{#
  Linhas da extração mais recente (com sucesso) de cada ID — versão econômica em memória do
  `latest_by`. Em vez de uma janela que precisa segurar todos os payloads JSON (centenas de MB),
  agrega só (id, max(extracted_at)) e filtra o bronze por junção. Uso:
      from {{ latest_success(source('bronze', 'mal_manga')) }} as src
#}
{% macro latest_success(relation, key='mal_id') -%}
(
    select s.*
    from {{ relation }} s
    join (
        select {{ key }}, max(extracted_at) as _latest_at
        from {{ relation }}
        where http_status = 200 and payload is not null
        group by {{ key }}
    ) l on l.{{ key }} = s.{{ key }} and l._latest_at = s.extracted_at
    where s.http_status = 200 and s.payload is not null
)
{%- endmacro %}

{# Tipo do payload da AniList, lido de uma vez só em stg_anilist__media. #}
{% macro anilist_media_type() -%}
{
    "id": "INTEGER",
    "title": {"romaji": "VARCHAR", "english": "VARCHAR", "native": "VARCHAR"},
    "favourites": "INTEGER", "averageScore": "INTEGER", "popularity": "INTEGER",
    "countryOfOrigin": "VARCHAR", "truncated": "BOOLEAN",
    "characters": [{
        "role": "VARCHAR",
        "node": {"id": "INTEGER", "name": {"full": "VARCHAR", "native": "VARCHAR"}, "gender": "VARCHAR",
                 "age": "VARCHAR", "favourites": "INTEGER", "image": {"medium": "VARCHAR"}, "siteUrl": "VARCHAR"},
        "voiceActorRoles": [{"roleNotes": "VARCHAR", "dubGroup": "VARCHAR", "voiceActor": {{ anilist_person_type() }}}]
    }],
    "staff": [{"role": "VARCHAR", "node": {{ anilist_person_type() }}}],
    "studios": {"edges": [{"isMain": "BOOLEAN", "node": {"id": "INTEGER", "name": "VARCHAR",
                           "isAnimationStudio": "BOOLEAN", "favourites": "INTEGER", "siteUrl": "VARCHAR"}}]},
    "tags": [{"name": "VARCHAR", "rank": "INTEGER", "category": "VARCHAR", "isMediaSpoiler": "BOOLEAN"}]
}
{%- endmacro %}
