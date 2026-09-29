{#
  By default dbt prefixes custom schemas with the target schema ("analytics_staging").
  Override that so models land in plain "staging" and "marts" schemas.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name | trim if custom_schema_name else target.schema }}
{%- endmacro %}
