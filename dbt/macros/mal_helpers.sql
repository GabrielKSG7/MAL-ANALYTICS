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
