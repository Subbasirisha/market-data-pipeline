{#
  Generic test: fails for every row where the column is zero or negative.
  dbt tests are queries that return the *bad* rows; zero rows returned = pass.
#}
{% test positive(model, column_name) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} <= 0
{% endtest %}
