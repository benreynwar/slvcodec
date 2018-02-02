library ieee;
use ieee.std_logic_1164.all;
use work.slvcodec.all;
{{use_clauses}}

entity {{entity_name}}_toslvcodec is{% if entity_generics %}
  generic (
    {{entity_generics}}
  );{% endif %}
  port ({% for port in ports %}
    {{port.name}}: {{port.direction}} {{port.typ}}{% if not loop.last%};{% endif %}{% endfor %}
  );
end entity;
 
architecture arch of {{entity_name}}_toslvcodec is
  {% for port in ports %}signal {{port.name}}_untyped: {% if port.typ.__str__() == "std_logic" %}std_logic{% else %}std_logic_vector({{port.width_as_str()}}-1 downto 0){% endif %};
  {% endfor %}
begin

  {% for port in ports %}{% if port.direction == "in" %}{{port.name}}_untyped <= {% if port.typ.__str__() == "std_logic"%}{{port.name}}{% else %}to_slvcodec({{port.name}}){% endif %}{% else %}{{port.name}} <= {% if port.typ.__str__() == "std_logic" %}{{port.name}}_untyped{% else %}from_slvcodec({{port.name}}_untyped){% endif %}{% endif %};
  {% endfor %}

  wrapped: entity work.{{wrapped_name}}
    port map({% for port in ports%}
      {{port.name}} => {{port.name}}_untyped{% if not loop.last %},{% endif %}{% endfor %}
      );
 
end architecture;
