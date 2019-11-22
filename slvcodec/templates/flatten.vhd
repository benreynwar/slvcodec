library ieee;
use ieee.std_logic_1164.all;
use work.slvcodec.all;
{{use_clauses}}

entity {{wrapper_name}} is
  generic (
    TEST_PARAMS_FILENAME: string := ""
    );
  port ({% for port in wrapper_ports %}
    {{port.name}}: {{port.direction}} {% if port.typ.__str__() == "std_logic" %}std_logic{% else %}std_logic_vector({{port.width}}-1 downto 0){% endif %}{% if not loop.last %};{% endif %}{% endfor %}
  );
end entity;
 
architecture arch of {{wrapper_name}} is
  {% for generic in generics %}
  constant {{generic.name}}: {{generic.typ}} := {{generic.value}};{% endfor %}
  {{ for_arch_header }}
  {% for port in wrapped_ports %}signal {{port.name}}_typed: {{port.typ}};
  {% endfor %}
begin

  {% for port in wrapper_ports %}
    {% if port.direction == "in" %}
      {{port.parent_name}}_typed{{port.suffix}} <=
      {% if port.typ.__str__() == "std_logic"%}
        {{port.name}};
      {% else %}
        from_slvcodec({{port.name}});
      {% endif %}
    {% else %}
      {{port.name}} <=
      {% if port.typ.__str__() == "std_logic"%}
        {{port.parent_name}}_typed{{port.suffix}};
      {% else %}
        to_slvcodec({{port.parent_name}}_typed{{port.suffix}});
      {% endif %}
    {% endif %}
  {% endfor %}

  wrapped: entity work.{{wrapped_name}}
    {% if generics %}generic map({% for generic in generics %}
      {{generic.name}} => {{generic.name}}{% if not loop.last %},{% endif %}{% endfor %}
      ){% endif %}
    port map({% for port in wrapped_ports%}
      {{port.name}} => {{port.name}}_typed{% if not loop.last %},{% endif %}{% endfor %}
      );
 
end architecture;
