{#
  Generic test: fails if any combination of the given columns appears more than once.
  (The built-in `unique` test only checks a single column.)
#}
{% test unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as occurrences
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
