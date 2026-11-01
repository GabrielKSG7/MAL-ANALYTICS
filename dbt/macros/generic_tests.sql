{# Testes genéricos próprios (sem depender de pacotes externos). #}

{% test value_between(model, column_name, min_value=none, max_value=none) %}
    select {{ column_name }}
    from {{ model }}
    where {{ column_name }} is not null
      and (
        {% if min_value is not none %} {{ column_name }} < {{ min_value }} {% else %} false {% endif %}
        or
        {% if max_value is not none %} {{ column_name }} > {{ max_value }} {% else %} false {% endif %}
      )
{% endtest %}

{% test row_count_at_least(model, min_rows) %}
    select count(*) as n from {{ model }} having count(*) < {{ min_rows }}
{% endtest %}

{# Unicidade de uma combinação de colunas. #}
{% test unique_combination(model, columns) %}
    select {{ columns | join(', ') }}, count(*) as n
    from {{ model }}
    group by {{ columns | join(', ') }}
    having count(*) > 1
{% endtest %}

{# Proporção máxima de nulos tolerada numa coluna (ex.: 0.2 = até 20%). #}
{% test null_ratio_below(model, column_name, max_ratio) %}
    select avg(case when {{ column_name }} is null then 1.0 else 0.0 end) as null_ratio
    from {{ model }}
    having avg(case when {{ column_name }} is null then 1.0 else 0.0 end) > {{ max_ratio }}
{% endtest %}
