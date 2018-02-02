library ieee;
use ieee.std_logic_1164.all;
use work.slvcodec.all;
{{use_clauses}}

entity {{entity_name}}_fromslvcodec is{% if entity_generics %}
  generic (
    {{entity_generics_with_defaults}}
  );{% endif %}
  port ({% for port in ports %}
    {{port.name}}: {{port.direction}} {% if port.typ.__str__() == "std_logic" %}std_logic{% else %}std_logic_vector({{port.width_as_str()}}-1 downto 0){% endif %}{% if not loop.last%};{% endif %}{% endfor %}
  );
end entity;
 
architecture arch of {{entity_name}}_fromslvcodec is
  {% for port in ports %}signal {{port.name}}_typed: {{port.typ}};
  {% endfor %}
begin

  {% for port in ports %}{% if port.direction == "in" %}{{port.name}}_typed <= {% if port.typ.__str__() == "std_logic"%}{{port.name}}{% else %}from_slvcodec({{port.name}}){% endif %}{% else %}{{port.name}} <= {% if port.typ.__str__() == "std_logic" %}{{port.name}}_typed{% else %}to_slvcodec({{port.name}}_typed){% endif %}{% endif %};
  {% endfor %}

  wrapped: entity work.{{wrapped_name}}{% if wrapped_generics %}
    generic map(
      {{wrapped_generics}}
      ){% endif %}
    port map({% for port in ports%}
      {{port.name}} => {{port.name}}_typed{% if not loop.last %},{% endif %}{% endfor %}
      );
 
end architecture;
