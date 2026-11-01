{#
  Usa o nome do schema customizado "puro" (staging, core, analytics...)
  em vez do padrão do dbt (<target_schema>_<custom>), que deixa o banco poluído.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
