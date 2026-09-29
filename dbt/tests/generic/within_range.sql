{#
  Generic test: fails for rows where the column falls outside [min_value, max_value].
  Nulls are ignored (use not_null for those).
#}
{% test within_range(model, column_name, min_value, max_value) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }}
{% endtest %}
